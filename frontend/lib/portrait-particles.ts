type SceneOptions = {
  canvas: HTMLCanvasElement
  image: HTMLImageElement
  initialProgress: number
  onContextLost: () => void
}
export type PortraitScene = {
  setProgress: (progress:number) => void
  prepareHeadline: (element:HTMLElement|null) => void
  setExit: (progress:number) => void
  destroy: () => void
}

// Original RGB texture fragments assemble the artwork. During departure, only
// cyan eye-light fragments survive: their new destinations sample the real h1.
const vertexSource=`
precision highp float;
attribute vec2 aTarget;
attribute vec2 aOrigin;
attribute vec3 aTiming;
attribute vec2 aHeadline;
attribute float aExtra;
uniform vec2 uResolution;
uniform vec4 uPortrait;
uniform float uProgress;
uniform float uSize;
uniform float uDpr;
uniform float uExit;
varying vec2 vUv;
varying float vAlpha;
varying float vBlue;
void main(){
  float t=smoothstep(aTiming.x,aTiming.x+0.38+aTiming.y*0.18,uProgress);
  vec2 end=uPortrait.xy+aTarget*uPortrait.zw;
  vec2 start=aOrigin*uResolution;
  vec2 normal=normalize(vec2(-(end-start).y,(end-start).x)+0.001);
  vec2 position=mix(start,end,t)+normal*sin(t*3.14159)*(1.0-t)*(aTiming.y-0.5)*260.0;
  float dissolve=smoothstep(0.0,0.76,uExit);
  float morph=smoothstep(0.08,0.9,uExit);
  vec2 departure=start+vec2(-uResolution.x*0.75,(aTiming.y-0.5)*uResolution.y);
  vec2 headline=aHeadline*uResolution;
  vec2 letter=mix(end,headline,morph);
  letter.y+=sin(morph*3.14159)*(aTiming.y-0.5)*80.0;
  position=mix(mix(position,departure,dissolve),letter,aTiming.z);
  // Preserve the exact incoming portrait; headline-only copies appear on exit.
  if(uExit<=0.0) position=mix(start,end,t)+normal*sin(t*3.14159)*(1.0-t)*(aTiming.y-0.5)*260.0;
  vec2 clip=position/uResolution*2.0-1.0;
  gl_Position=vec4(clip.x,-clip.y,0.0,1.0);
  gl_PointSize=mix(uSize,1.8*uDpr,morph*aTiming.z);
  vUv=aTarget;
  vBlue=aTiming.z*smoothstep(0.05,0.5,uExit);
  vAlpha=smoothstep(0.0,0.08,t)*mix(1.0-smoothstep(0.26,0.74,uExit),1.0-smoothstep(0.9,1.0,uExit),aTiming.z);
  vAlpha*=mix(1.0,smoothstep(0.02,0.18,uExit),aExtra);
}`
const fragmentSource=`
precision mediump float;
uniform sampler2D uImage;
uniform vec2 uTile;
varying vec2 vUv;
varying float vAlpha;
varying float vBlue;
void main(){
  vec4 ink=texture2D(uImage,vUv+(gl_PointCoord-0.5)*uTile);
  gl_FragColor=vec4(mix(ink.rgb,vec3(0.4196,0.7451,0.8235),vBlue),ink.a*vAlpha);
}`
function random(seed:number){return()=>{seed=(Math.imul(seed,1664525)+1013904223)|0;return(seed>>>0)/4294967296}}
function shader(gl:WebGLRenderingContext,type:number,source:string){
  const result=gl.createShader(type)!
  gl.shaderSource(result,source);gl.compileShader(result)
  if(!gl.getShaderParameter(result,gl.COMPILE_STATUS)){const error=gl.getShaderInfoLog(result);gl.deleteShader(result);throw new Error(error||'Portrait shader failed')}
  return result
}

export function createPortraitScene({canvas,image,initialProgress,onContextLost}:SceneOptions):PortraitScene{
  const gl=canvas.getContext('webgl',{alpha:true,antialias:false,depth:false,powerPreference:'low-power'})
  if(!gl)throw new Error('WebGL unavailable')
  const program=gl.createProgram()!
  for(const[type,source]of[[gl.VERTEX_SHADER,vertexSource],[gl.FRAGMENT_SHADER,fragmentSource]]as const){const compiled=shader(gl,type,source);gl.attachShader(program,compiled);gl.deleteShader(compiled)}
  gl.linkProgram(program)
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('Portrait shader linking failed')
  gl.useProgram(program)
  const texture=gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D,texture)
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST)
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE)
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image)
  const cols=240,rows=Math.round(cols*image.naturalHeight/image.naturalWidth)
  const sample=document.createElement('canvas');sample.width=cols;sample.height=rows
  const ctx=sample.getContext('2d',{willReadFrequently:true})!
  ctx.drawImage(image,0,0,cols,rows)
  const pixels=ctx.getImageData(0,0,cols,rows).data
  const original:number[]=[],streakIndices:number[]=[]
  const next=random(8419)
  for(let y=0;y<rows;y++)for(let x=0;x<cols;x++){
    const i=(y*cols+x)*4
    if(Math.max(pixels[i],pixels[i+1],pixels[i+2])<9)continue
    const side=next(),distance=.05+next()*.6,along=next()
    const ox=side<.4?-distance:side<.8?1+distance:along
    const oy=side<.8?along:side<.9?-distance:1+distance
    const cyan=pixels[i+1]>pixels[i]*1.4&&pixels[i+2]>pixels[i]*1.4&&pixels[i+1]>70
    const streak=cyan&&y/rows>.29&&y/rows<.44&&x/cols>.26&&x/cols<.7?1:0
    if(streak)streakIndices.push(original.length)
    original.push((x+.5)/cols,(y+.5)/rows,ox,oy,.015+next()*.39,next(),streak,.5,.25,0)
  }
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer)
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(original),gl.DYNAMIC_DRAW)
  for(const[name,size,offset]of[['aTarget',2,0],['aOrigin',2,8],['aTiming',3,16],['aHeadline',2,28],['aExtra',1,36]]as const){const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,40,offset)}
  const uniform=(name:string)=>gl.getUniformLocation(program,name)
  const progressUniform=uniform('uProgress'),exitUniform=uniform('uExit')
  gl.uniform2f(uniform('uTile'),1/cols,1/rows)
  gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.clearColor(0,0,0,0)
  let progress=initialProgress,exit=0,frame=0,destroyed=false,count=original.length/10,headlineElement:HTMLElement|null=null
  function draw(){frame=0;if(destroyed)return;gl!.uniform1f(progressUniform,progress);gl!.uniform1f(exitUniform,exit);gl!.clear(gl!.COLOR_BUFFER_BIT);gl!.drawArrays(gl!.POINTS,0,count)}
  function schedule(){if(!frame&&!destroyed&&!document.hidden)frame=requestAnimationFrame(draw)}
  function prepareHeadline(element:HTMLElement|null){
    headlineElement=element
    if(!element||!streakIndices.length||destroyed)return
    const bounds=element.getBoundingClientRect(),view=canvas.getBoundingClientRect()
    if(!bounds.width||!bounds.height||!view.width||!view.height)return
    const style=getComputedStyle(element),size=parseFloat(style.fontSize)
    const mask=document.createElement('canvas');mask.width=Math.ceil(bounds.width);mask.height=Math.ceil(bounds.height)
    const ink=mask.getContext('2d',{willReadFrequently:true})!
    ink.font=`${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
    ink.letterSpacing=style.letterSpacing
    ink.fillStyle='#fff';ink.textAlign='center';ink.textBaseline='alphabetic'
    const text=element.textContent||'',metrics=ink.measureText(text)
    const ascent=metrics.fontBoundingBoxAscent||size*.8,descent=metrics.fontBoundingBoxDescent||size*.2
    ink.fillText(text,mask.width/2,(mask.height-ascent-descent)/2+ascent)
    const maskPixels=ink.getImageData(0,0,mask.width,mask.height).data
    const destinations:Array<[number,number]>=[]
    const step=view.width<600?2:3
    for(let y=0;y<mask.height;y+=step)for(let x=0;x<mask.width;x+=step){
      if(maskPixels[(y*mask.width+x)*4+3]>90)destinations.push([(bounds.left-view.left+x)/view.width,(bounds.top-view.top+y)/view.height])
    }
    if(!destinations.length)return
    // Shuffle every destination once so every letter is covered, for any point count.
    const shuffle=random(6103)
    for(let i=destinations.length-1;i>0;i--){const j=Math.floor(shuffle()*(i+1));[destinations[i],destinations[j]]=[destinations[j],destinations[i]]}
    const data=original.slice()
    const total=Math.max(streakIndices.length,destinations.length)
    for(let i=0;i<total;i++){
      const source=streakIndices[i%streakIndices.length]
      const destination=destinations[i%destinations.length]
      if(i<streakIndices.length){data[source+7]=destination[0];data[source+8]=destination[1]}
      else{const copy=original.slice(source,source+10);copy[7]=destination[0];copy[8]=destination[1];copy[9]=1;data.push(...copy)}
    }
    gl!.bindBuffer(gl!.ARRAY_BUFFER,buffer);gl!.bufferData(gl!.ARRAY_BUFFER,new Float32Array(data),gl!.DYNAMIC_DRAW)
    count=data.length/10;schedule()
  }
  function resize(){
    const{width,height}=canvas.getBoundingClientRect();if(!width||!height)return
    const dpr=Math.min(devicePixelRatio||1,2),pw=Math.max(width,height*image.naturalWidth/image.naturalHeight),ph=pw*image.naturalHeight/image.naturalWidth
    canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr)
    gl!.viewport(0,0,canvas.width,canvas.height);gl!.uniform2f(uniform('uResolution'),width,height)
    gl!.uniform4f(uniform('uPortrait'),(width-pw)/2,(height-ph)/2,pw,ph)
    gl!.uniform1f(uniform('uSize'),pw/cols*dpr+.25);gl!.uniform1f(uniform('uDpr'),dpr)
    if(headlineElement)prepareHeadline(headlineElement)
    schedule()
  }
  function lost(event:Event){event.preventDefault();onContextLost()}
  const observer=new ResizeObserver(resize);resize();observer.observe(canvas)
  canvas.addEventListener('webglcontextlost',lost);document.addEventListener('visibilitychange',schedule)
  return{
    setProgress(value){progress=value;cancelAnimationFrame(frame);draw()},prepareHeadline,
    setExit(value){exit=value;cancelAnimationFrame(frame);draw()},
    destroy(){destroyed=true;cancelAnimationFrame(frame);observer.disconnect();canvas.removeEventListener('webglcontextlost',lost);document.removeEventListener('visibilitychange',schedule);gl.deleteBuffer(buffer);gl.deleteTexture(texture);gl.deleteProgram(program)},
  }
}
