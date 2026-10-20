'use strict';
/* Offline WebGL galaxy fallback that preserves camera flight when CDN is unavailable.
 * No third-party code, no assets or network requests. */
if (typeof window.ForceGraph3D !== 'function') {
  window.ForceGraph3D = function ForceGraph3DOffline() {
    return function mount(container) {
      const canvas=document.createElement('canvas');canvas.className='offline-webgl';
      canvas.setAttribute('aria-label','نمای سه‌بعدی WebGL یادداشت‌ها');container.append(canvas);
      const gl=canvas.getContext('webgl',{antialias:true,alpha:true,preserveDrawingBuffer:false});
      if(!gl) {canvas.remove();throw Error('WebGL disabled');}
      const V=`attribute vec3 position;attribute vec3 tint;attribute float size;varying vec3 vColor;uniform mat4 vp;uniform float pixelRatio;void main(){vec4 clip=vp*vec4(position,1.);gl_Position=clip;float z=max(1.,clip.w);gl_PointSize=clamp(size*pixelRatio*420./z,1.4,42.);vColor=tint;}`;
      const F=`precision mediump float;varying vec3 vColor;uniform float pointMode;void main(){vec3 col=vColor;if(pointMode>.5){vec2 p=gl_PointCoord*2.-1.;float r=length(p);if(r>1.)discard;float core=pow(max(0.,1.-r),2.2);float halo=pow(max(0.,1.-r),5.);float alpha=clamp(core*.4+halo*.85,0.,1.);gl_FragColor=vec4(col*(1.+halo*.65),alpha);}else{gl_FragColor=vec4(col,.26);}}`;
      const compile=(source,type)=>{const sh=gl.createShader(type);gl.shaderSource(sh,source);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(sh));return sh;};
      const prog=gl.createProgram();gl.attachShader(prog,compile(V,gl.VERTEX_SHADER));gl.attachShader(prog,compile(F,gl.FRAGMENT_SHADER));gl.linkProgram(prog);if(!gl.getProgramParameter(prog,gl.LINK_STATUS))throw Error('WebGL shader linker failed');
      const attr={pos:gl.getAttribLocation(prog,'position'),tint:gl.getAttribLocation(prog,'tint'),size:gl.getAttribLocation(prog,'size')};
      const uniforms={vp:gl.getUniformLocation(prog,'vp'),point:gl.getUniformLocation(prog,'pointMode'),ratio:gl.getUniformLocation(prog,'pixelRatio')};
      const buf=gl.createBuffer();let data={nodes:[],links:[]},nodeData=[],lines=[],nodeId='id',label=n=>n.title||'',nodeColor=()=>'#4ac9ff',nodeVal=4;
      let nodeClick=()=>{},nodeHover=()=>{},linkColor=()=>'#327ca7',linkOpacity=.35;
      let camera={yaw:.23,pitch:.1,dist:310,target:[0,0,0]}, to=null,turning=false,mouse={x:0,y:0},dragging=false,dragStart=null,lastHover=null,drawId=null;
      let width=container.clientWidth||500,height=container.clientHeight||500;
      const rgb=color=>{let hex=typeof color==='string'?color:'#71d8ff';if(/^#[\da-f]{3}$/i.test(hex))hex='#'+hex.slice(1).split('').map(x=>x+x).join('');const m=/^#([\da-f]{6})$/i.exec(hex);let v=m?parseInt(m[1],16):0x71d8ff;return [(v>>16&255)/255,(v>>8&255)/255,(v&255)/255];};
      const sub=(a,b)=>a.map((x,i)=>x-b[i]);
      const norm=a=>{const s=Math.hypot(...a)||1;return a.map(x=>x/s);};
      const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
      const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
      const m4=(...r)=>r.flat();
      const mul=(a,b)=>{const o=new Array(16).fill(0);for(let r=0;r<4;r++)for(let c=0;c<4;c++)for(let k=0;k<4;k++)o[r*4+c]+=a[r*4+k]*b[k*4+c];return o;};
      const matTranspose=m=>m4([m[0],m[4],m[8],m[12]],[m[1],m[5],m[9],m[13]],[m[2],m[6],m[10],m[14]],[m[3],m[7],m[11],m[15]]);
      const getProjection=()=>{
        const aspect=width/Math.max(height,1),near=1,far=2000,f=1/Math.tan(.78/2);
        const proj=m4([f/aspect,0,0,0],[0,f,0,0],[0,0,(far+near)/(near-far),2*far*near/(near-far)],[0,0,-1,0]);
        const eye=[camera.target[0]+Math.sin(camera.yaw)*Math.cos(camera.pitch)*camera.dist,camera.target[1]+Math.sin(camera.pitch)*camera.dist,camera.target[2]+Math.cos(camera.yaw)*Math.cos(camera.pitch)*camera.dist];
        const forward=norm(sub(camera.target,eye)),right=norm(cross(forward,[0,1,0])),up=cross(right,forward);
        const view=m4([right[0],right[1],right[2],-dot(right,eye)],[up[0],up[1],up[2],-dot(up,eye)],[-forward[0],-forward[1],-forward[2],dot(forward,eye)],[0,0,0,1]);
        return mul(proj,view);
      };
      function project(pos){const mat=getProjection(),p=[...pos,1],q=mat.map((_,r)=>dot(mat.slice(r*4,r*4+4),p));if(q[3]<=0)return null;return {x:(q[0]/q[3]*.5+.5)*width,y:(.5-q[1]/q[3]*.5)*height};}
      function populate(){
        const nodes=data.nodes;
        const cats=[...new Set(nodes.map(n=>n.category))];
        nodes.forEach((n,i)=>{
          const cat=Math.max(0,cats.indexOf(n.category));
          const angle=(i*2.399963+cat*2.1),rad=24+Math.sqrt(i+1)*14;
          n.x=Math.cos(angle)*rad;n.y=Math.sin(i*1.23)*19+(cat-cats.length/2)*5;n.z=Math.sin(angle)*rad;
        });
        const idMap=new Map(nodes.map(n=>[n[nodeId],n]));
        lines=data.links.map(l=>{
          const a=idMap.get(typeof l.source==='object'?l.source[nodeId]:l.source),b=idMap.get(typeof l.target==='object'?l.target[nodeId]:l.target);
          return a&&b?[a,b]:null;
        }).filter(Boolean);
      }
      function pack(vertices){let floats=new Float32Array(vertices.length*7);vertices.forEach((v,i)=>{floats.set([...v.pos,...v.color,v.size],i*7)});return floats;}
      function drawBuffer(vertices,mode,pointMode){if(!vertices.length)return;const floats=pack(vertices);gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,floats,gl.DYNAMIC_DRAW);
        gl.vertexAttribPointer(attr.pos,3,gl.FLOAT,false,28,0);gl.vertexAttribPointer(attr.tint,3,gl.FLOAT,false,28,12);gl.vertexAttribPointer(attr.size,1,gl.FLOAT,false,28,24);
        gl.enableVertexAttribArray(attr.pos);gl.enableVertexAttribArray(attr.tint);gl.enableVertexAttribArray(attr.size);
        gl.uniform1f(uniforms.point,pointMode);gl.drawArrays(mode,0,vertices.length);
      }
      const vertex=(n,size=4)=>({pos:[n.x,n.y,n.z],color:rgb(typeof nodeColor==='function'?nodeColor(n):nodeColor),size});
      let rafLast=0;
      function frame(t){drawId=requestAnimationFrame(frame);if(document.hidden)return;
        const now=performance.now();if(now-rafLast<29)return;rafLast=now;
        if(to){const p=Math.min(1,(now-to.start)/to.duration),e=1-Math.pow(1-p,3);camera.target=to.from.map((x,i)=>x*(1-e)+to.target[i]*e);camera.dist=to.d0*(1-e)+to.distance*e;if(p>=1)to=null;}
        if(!turning&&!to)camera.yaw+=.00028;
        const ratio=Math.min(2,window.devicePixelRatio||1),w=Math.max(1,Math.round(width*ratio)),h=Math.max(1,Math.round(height*ratio));
        if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;canvas.style.width=width+'px';canvas.style.height=height+'px';}
        gl.viewport(0,0,w,h);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
        gl.enable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
        gl.useProgram(prog);gl.uniformMatrix4fv(uniforms.vp,false,new Float32Array(matTranspose(getProjection())));gl.uniform1f(uniforms.ratio,ratio);
        drawBuffer(lines.flatMap(([a,b])=>[{pos:[a.x,a.y,a.z],color:rgb(linkColor()),size:1},{pos:[b.x,b.y,b.z],color:rgb(linkColor()),size:1}]),gl.LINES,0);
        drawBuffer(data.nodes.map(n=>vertex(n,Number(typeof nodeVal==='function'?nodeVal(n):nodeVal)||4)),gl.POINTS,1);
      }
      drawId=requestAnimationFrame(frame);
      function hover(e,click=false){const r=canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;let near=null,best=click?22:15;for(const n of data.nodes){const p=project([n.x,n.y,n.z]);if(!p)continue;const d=Math.hypot(p.x-x,p.y-y);if(d<best){best=d;near=n;}}if(click){if(near)nodeClick(near,e);return;}
        if(near!==lastHover){nodeHover(near,lastHover);lastHover=near;}}
      canvas.addEventListener('pointerdown',e=>{dragging=true;turning=true;dragStart={x:e.clientX,y:e.clientY};mouse={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);});
      canvas.addEventListener('pointermove',e=>{if(dragging){camera.yaw-=(e.clientX-mouse.x)*.006;camera.pitch=Math.max(-1.2,Math.min(1.2,camera.pitch+(e.clientY-mouse.y)*.006));mouse={x:e.clientX,y:e.clientY};}else hover(e);});
      canvas.addEventListener('pointerup',e=>{dragging=false;const move=Math.hypot(e.clientX-dragStart.x,e.clientY-dragStart.y);if(move<7)hover(e,true);setTimeout(()=>turning=false,2200);});
      canvas.addEventListener('wheel',e=>{e.preventDefault();turning=true;camera.dist=Math.min(920,Math.max(35,camera.dist*(e.deltaY>0?1.11:.89)));setTimeout(()=>turning=false,2400);},{passive:false});
      const api={};
      const methods=['backgroundColor','showNavInfo','nodeId','nodeLabel','nodeColor','nodeVal','nodeRelSize','linkColor','linkOpacity','linkWidth','enableNodeDrag','onNodeClick','onNodeHover','d3VelocityDecay'];
      for(const key of methods){api[key]=function(x){if(arguments.length){if(key==='nodeId')nodeId=x;if(key==='nodeLabel')label=x;if(key==='nodeColor')nodeColor=x;if(key==='nodeVal')nodeVal=x;if(key==='linkColor')linkColor=x;if(key==='linkOpacity')linkOpacity=x;if(key==='onNodeClick')nodeClick=x;if(key==='onNodeHover')nodeHover=x;return api;}return key==='nodeVal'?nodeVal:key==='nodeColor'?nodeColor:null;};}
      api.graphData=function(value){if(!arguments.length)return data;data=value||{nodes:[],links:[]};populate();return api;};
      api.cameraPosition=function(position,lookAt,duration=1000){const dest=lookAt?[lookAt.x||0,lookAt.y||0,lookAt.z||0]:[0,0,0];const d=position?Math.max(35,Math.hypot(position.x-dest[0],position.y-dest[1],position.z-dest[2])):240;to={from:[...camera.target],target:dest,d0:camera.dist,distance:d,start:performance.now(),duration:Math.max(50,duration)};return api;};
      api.zoomToFit=function(duration=900,padding=80,filter=null){const ns=data.nodes.filter(n=>!filter||filter(n));if(!ns.length)return api;const c=[0,1,2].map(i=>ns.reduce((s,n)=>s+[n.x,n.y,n.z][i],0)/ns.length);const bound=Math.max(35,...ns.map(n=>Math.hypot(n.x-c[0],n.y-c[1],n.z-c[2])));to={from:[...camera.target],target:c,d0:camera.dist,distance:Math.min(940,Math.max(100,bound*3.1+padding*.7)),start:performance.now(),duration:Math.max(50,duration)};return api;};
      api.width=function(v){if(!arguments.length)return width;width=Math.max(1,v);return api;};
      api.height=function(v){if(!arguments.length)return height;height=Math.max(1,v);return api;};
      api.destroy=function(){cancelAnimationFrame(drawId);canvas.remove();};
      return api;
    };
  };
  window.JARVIS_OFFLINE_WEBGL=true;
}
