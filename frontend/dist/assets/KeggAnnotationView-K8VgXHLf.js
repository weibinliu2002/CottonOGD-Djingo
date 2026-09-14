import"./index-CDqonAEx.js";/* empty css                *//* empty css                     *//* empty css               *//* empty css                  *//* empty css                  *//* empty css                  *//* empty css                 */import{d as q,ax as C,p as L,c as v,a as d,U as r,u as t,F as o,G as a,aF as M,r as m,$ as U,S as K,M as A,a6 as N,aA as O,o as p,B as R}from"./vue-vendor-UPSzB6ZS.js";import{u as j}from"./useGenomeBrowser-DuRf3P1N.js";import{u as z}from"./enrichment-L-l0QGtZ.js";import{m as T,a as $,v as H,w as P,e as Q,f as W,d as X,o as g,n as Y}from"./element-plus-BVGCgPq7.js";import{_ as Z}from"./_plugin-vue_export-helper-DlAUqK2U.js";import"./utils-eXoYvUN4.js";import"./useAsyncTask-CMk2hupo.js";const ee={class:"container mt-4"},ie={class:"card-header"},te={class:"mt-2"},oe={class:"d-flex justify-content-end"},ae=q({__name:"KeggAnnotationView",setup(ne){const{t:e}=C(),s=m(""),u=m(!1),J=O(),f=M(),{genomeOptions:b,genomeLoading:h,ensureGenomesLoaded:y,pickDefaultGenome:E,allGenomes:x}=j(),c=m("");L(async()=>{await y();const i=typeof f.query.genome=="string"?f.query.genome:"",n=i&&x.value.includes(i)?i:E();n&&(c.value=n)});const V=()=>{const i=`Kirkii_Juiced.00g000010
Kirkii_Juiced.00g000020
Kirkii_Juiced.00g000030
Kirkii_Juiced.00g000040
Kirkii_Juiced.00g000050
Kirkii_Juiced.00g000060
Kirkii_Juiced.00g000070
Kirkii_Juiced.00g000080
Kirkii_Juiced.00g000090
Kirkii_Juiced.00g000100
Kirkii_Juiced.00g000110
Kirkii_Juiced.00g000120
Kirkii_Juiced.00g000130
Kirkii_Juiced.00g000140
Kirkii_Juiced.00g000150
Kirkii_Juiced.00g000160
Kirkii_Juiced.00g000170
Kirkii_Juiced.00g000180
Kirkii_Juiced.00g000190
Kirkii_Juiced.00g000200
Kirkii_Juiced.00g000210
Kirkii_Juiced.00g000220
Kirkii_Juiced.00g000230`;s.value=i},w=async()=>{if(!s.value.trim()){g.error(e("please_enter")+" gene IDs");return}if(!c.value){g.error(e("please_select_genome"));return}u.value=!0;try{const i=z();i.selectedGenome=c.value,J.push({path:"/tools/kegg-annotation/results",query:{gene_id:s.value}})}catch(i){console.error(e("error")+" submitting form:",i),g.error(e("error")+" submitting form: "+(i.message||"Unknown error"))}finally{u.value=!1}};return(i,n)=>{const G=Q,k=W,_=P,I=Y,B=X,S=H,D=T,F=$;return p(),v("div",ee,[d("h2",null,r(t(e)("kegg_annotation"))+" "+r(t(e)("search")),1),o(D,{class:"mb-4"},{header:a(()=>[d("div",ie,[d("span",null,r(t(e)("kegg_annotation"))+" "+r(t(e)("search")),1)])]),default:a(()=>[o(S,{onSubmit:U(w,["prevent"]),"label-width":"250px"},{default:a(()=>[o(_,{label:"Enter Gene IDs (one per line or space/comma separated)"},{default:a(()=>[o(G,{type:"textarea",rows:5,modelValue:s.value,"onUpdate:modelValue":n[0]||(n[0]=l=>s.value=l),placeholder:"please_enter gene IDs",disabled:u.value},null,8,["modelValue","disabled"]),d("div",te,[o(k,{type:"info",size:"small",onClick:V,disabled:u.value},{default:a(()=>[K(r(t(e)("load_example")),1)]),_:1},8,["disabled"])])]),_:1}),o(_,{label:t(e)("select_genome")},{default:a(()=>[o(B,{modelValue:c.value,"onUpdate:modelValue":n[1]||(n[1]=l=>c.value=l),placeholder:t(e)("select_genome"),style:{width:"100%"},loading:t(h),filterable:""},{default:a(()=>[(p(!0),v(A,null,N(t(b),l=>(p(),R(I,{key:l.value,label:l.label,value:l.value},null,8,["label","value"]))),128))]),_:1},8,["modelValue","placeholder","loading"])]),_:1},8,["label"]),o(_,null,{default:a(()=>[d("div",oe,[o(k,{type:"primary","native-type":"submit",loading:u.value},{default:a(()=>[K(r(t(e)("search")),1)]),_:1},8,["loading"])])]),_:1})]),_:1})]),_:1}),o(F,{right:40,bottom:40})])}}}),be=Z(ae,[["__scopeId","data-v-22997029"]]);export{be as default};
