type SceneOptions = {
  canvas: HTMLCanvasElement
  image: HTMLImageElement
  initialProgress: number
  onContextLost: () => void
}
export type PortraitScene = { setProgress: (progress: number) => void; destroy: () => void }

// Each flying tile carries the original artwork's texture, including its cyan
// light and ASCII gaps. No recoloring or photographic reconstruction occurs.
const vertexSource = `
precision highp float;
attribute vec2 aTarget;
attribute vec2 aOrigin;
attribute vec2 aTiming;
uniform vec2 uResolution;
uniform vec4 uPortrait;
uniform float uProgress;
uniform float uSize;
varying vec2 vUv;
varying float vAlpha;
void main() {
  float t = smoothstep(aTiming.x, aTiming.x + 0.38 + aTiming.y * 0.18, uProgress);
  vec2 end = uPortrait.xy + aTarget * uPortrait.zw;
  vec2 start = aOrigin * uResolution;
  vec2 normal = normalize(vec2(-(end-start).y, (end-start).x) + 0.001);
  vec2 position = mix(start, end, t) + normal * sin(t * 3.14159)
    * (1.0-t) * (aTiming.y-0.5) * 260.0;
  vec2 clip = position / uResolution * 2.0 - 1.0;
  gl_Position = vec4(clip.x, -clip.y, 0.0, 1.0);
  gl_PointSize = uSize;
  vUv = aTarget;
  vAlpha = smoothstep(0.0, 0.08, t);
}`
const fragmentSource = `
precision mediump float;
uniform sampler2D uImage;
uniform vec2 uTile;
varying vec2 vUv;
varying float vAlpha;
void main() {
  vec4 ink = texture2D(uImage, vUv + (gl_PointCoord - 0.5) * uTile);
  gl_FragColor = vec4(ink.rgb, ink.a * vAlpha);
}`
function random(seed: number) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) | 0
    return (seed >>> 0) / 4294967296
  }
}
function shader(gl: WebGLRenderingContext, type: number, source: string) {
  const result = gl.createShader(type)!
  gl.shaderSource(result, source)
  gl.compileShader(result)
  if (!gl.getShaderParameter(result, gl.COMPILE_STATUS)) {
    const error = gl.getShaderInfoLog(result)
    gl.deleteShader(result)
    throw new Error(error || 'Portrait shader failed')
  }
  return result
}
export function createPortraitScene({canvas, image, initialProgress, onContextLost}: SceneOptions): PortraitScene {
  const gl = canvas.getContext('webgl', {alpha:true, antialias:false, depth:false, powerPreference:'low-power'})
  if (!gl) throw new Error('WebGL unavailable')
  const program = gl.createProgram()!
  for (const [type, source] of [[gl.VERTEX_SHADER, vertexSource], [gl.FRAGMENT_SHADER, fragmentSource]] as const) {
    const compiled = shader(gl, type, source)
    gl.attachShader(program, compiled)
    gl.deleteShader(compiled)
  }
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error('Portrait shader linking failed')
  gl.useProgram(program)
  const texture = gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D, texture)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image)
  const cols = 240
  const rows = Math.round(cols * image.naturalHeight / image.naturalWidth)
  const sample = document.createElement('canvas')
  sample.width = cols; sample.height = rows
  const ctx = sample.getContext('2d', {willReadFrequently:true})!
  ctx.drawImage(image, 0, 0, cols, rows)
  const pixels = ctx.getImageData(0, 0, cols, rows).data
  const data: number[] = []
  const next = random(8419)
  for (let y=0; y<rows; y++) for (let x=0; x<cols; x++) {
    const i=(y*cols+x)*4
    if (Math.max(pixels[i],pixels[i+1],pixels[i+2]) < 9) continue
    const side=next(), distance=.05+next()*.6, along=next()
    const ox=side<.4 ? -distance : side<.8 ? 1+distance : along
    const oy=side<.8 ? along : side<.9 ? -distance : 1+distance
    data.push((x+.5)/cols, (y+.5)/rows, ox, oy, .015+next()*.39, next())
  }
  const buffer=gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.STATIC_DRAW)
  for (const [name, offset] of [['aTarget',0],['aOrigin',8],['aTiming',16]] as const) {
    const loc=gl.getAttribLocation(program,name)
    gl.enableVertexAttribArray(loc)
    gl.vertexAttribPointer(loc,2,gl.FLOAT,false,24,offset)
  }
  const uniform=(name:string)=>gl.getUniformLocation(program,name)
  const progressUniform=uniform('uProgress')
  gl.uniform2f(uniform('uTile'),1/cols,1/rows)
  gl.enable(gl.BLEND)
  gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA)
  gl.clearColor(0,0,0,0)
  let progress=initialProgress, frame=0, destroyed=false
  function draw() {
    frame=0
    if (destroyed) return
    gl!.uniform1f(progressUniform,progress)
    gl!.clear(gl!.COLOR_BUFFER_BIT)
    gl!.drawArrays(gl!.POINTS,0,data.length/6)
  }
  function schedule() { if (!frame && !destroyed && !document.hidden) frame=requestAnimationFrame(draw) }
  function resize() {
    const {width,height}=canvas.getBoundingClientRect()
    if (!width || !height) return
    const dpr=Math.min(devicePixelRatio || 1,2)
    const pw=Math.max(width,height*image.naturalWidth/image.naturalHeight)
    const ph=pw*image.naturalHeight/image.naturalWidth
    const px=(width-pw)/2, py=(height-ph)/2
    canvas.width=Math.round(width*dpr); canvas.height=Math.round(height*dpr)
    gl!.viewport(0,0,canvas.width,canvas.height)
    gl!.uniform2f(uniform('uResolution'),width,height)
    gl!.uniform4f(uniform('uPortrait'),px,py,pw,ph)
    gl!.uniform1f(uniform('uSize'),pw/cols*dpr+.25)
    schedule()
  }
  function lost(event:Event) { event.preventDefault(); onContextLost() }
  const observer=new ResizeObserver(resize)
  resize(); observer.observe(canvas)
  canvas.addEventListener('webglcontextlost',lost)
  document.addEventListener('visibilitychange',schedule)
  return {
    setProgress(value) { progress=value; schedule() },
    destroy() {
      destroyed=true; cancelAnimationFrame(frame); observer.disconnect()
      canvas.removeEventListener('webglcontextlost',lost)
      document.removeEventListener('visibilitychange',schedule)
      gl.deleteBuffer(buffer); gl.deleteTexture(texture); gl.deleteProgram(program)
    },
  }
}
