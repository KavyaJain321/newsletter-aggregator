import { getAuthClient } from "./scripts/lib/auth";
import { google } from "googleapis";
import fs from "node:fs";
import path from "node:path";

const OUT = process.env.EXPORT_DIR || "C:/Users/anony/AppData/Local/Temp/claude/D--Work-Projects-newsletter-aggregator/6a149ca2-2e19-421c-a763-72970e46e4e2/scratchpad/export";
const EMLDIR = path.join(OUT, "eml");

const SEG: Record<string,string> = {techai:"1-TechAI",biz:"2-BizFinance",legal:"3-Legal",hr:"4-HR",github:"5-GitHub",indie:"6-IndieHacker",satire:"7-Absurdist",smallcap:"8-SmallCap",news:"9-News"};
const CONFIRM=/confirm|verify|welcome|complete your sign|one-time|added successfully|now signed up|now subscribed|thanks for signing|a few things|verification code|on the list/i;

function decodeRaw(b64url:string){return Buffer.from(b64url.replace(/-/g,"+").replace(/_/g,"/"),"base64").toString("utf8");}
function headerBlock(eml:string){const i=eml.search(/\r?\n\r?\n/);return (i<0?eml:eml.slice(0,i)).replace(/\r?\n[ \t]+/g," ");}
function getHeader(block:string,name:string){const re=new RegExp("^"+name+":\\s*(.*)$","im");const m=block.match(re);return m?m[1].trim():"";}
function segOf(to:string,from:string){const t=(to.match(/\+([a-z]+)@/)||[])[1];if(t&&SEG[t])return SEG[t];const f=from.toLowerCase();if(f.includes("hrbrew@morningbrew"))return SEG.hr;if(f.includes("morningbrew.com"))return SEG.biz;if(f.includes("findlaw.com"))return SEG.legal;if(f.includes("babylonbee.com"))return SEG.satire;return "unmatched";}
function csvCell(v:any){const s=String(v??"").replace(/"/g,'""').replace(/\r?\n/g," ");return `"${s}"`;}
function slug(s:string){return (s||"x").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/(^-|-$)/g,"").slice(0,28);}

(async()=>{
  fs.rmSync(OUT,{recursive:true,force:true});
  fs.mkdirSync(EMLDIR,{recursive:true});
  const auth=await getAuthClient();const gmail=google.gmail({version:"v1",auth});
  let ids:string[]=[];let page:string|undefined;
  do{const r=await gmail.users.messages.list({userId:"me",q:"in:anywhere newer_than:20d",maxResults:200,pageToken:page});(r.data.messages||[]).forEach(m=>ids.push(m.id!));page=r.data.nextPageToken||undefined;}while(page&&ids.length<600);

  const rows:any[]=[]; let saved=0;
  for(const id of ids){
    let raw:string;
    try{ const m:any=(await gmail.users.messages.get({userId:"me",id,format:"raw"})).data; raw=decodeRaw(m.raw); }catch{ continue; }
    const hb=headerBlock(raw);
    const from=getHeader(hb,"From");
    const to=getHeader(hb,"To")||getHeader(hb,"Delivered-To");
    const deliveredTo=getHeader(hb,"Delivered-To")||to;
    const subject=getHeader(hb,"Subject");
    const date=getHeader(hb,"Date");
    const fromEmail=(from.match(/<([^>]+)>/)||[,from])[1].toLowerCase();
    const fromName=(from.match(/^(.*?)</)||[])[1]?.replace(/"/g,"").trim()||from;
    // skip our own test mails / google account notices
    if(fromEmail.includes("notifyy1008@gmail.com")||fromEmail.includes("noreply-accounts@google.com"))continue;
    const seg=segOf(deliveredTo,fromEmail);
    const isIssue = (CONFIRM.test(subject)||!subject.trim())?0:1;
    // save eml
    const dir=path.join(EMLDIR,seg);fs.mkdirSync(dir,{recursive:true});
    const fname=`${slug(fromName)}__${id}.eml`;
    fs.writeFileSync(path.join(dir,fname),raw);
    saved++;
    rows.push({id,segment:seg,from_name:fromName,from_email:fromEmail,to:deliveredTo,date,subject,is_issue:isIssue,eml:`eml/${seg}/${fname}`});
  }

  // metadata CSV
  const header="segment,from_name,from_email,delivered_to,date,subject,is_issue,gmail_id,eml_path";
  const lines=rows.sort((a,b)=>a.segment.localeCompare(b.segment)).map(r=>[r.segment,r.from_name,r.from_email,r.to,r.date,r.subject,r.is_issue,r.id,r.eml].map(csvCell).join(","));
  fs.writeFileSync(path.join(OUT,"emails.csv"),[header,...lines].join("\n"),"utf8");
  fs.writeFileSync(path.join(OUT,"emails.json"),JSON.stringify(rows,null,2),"utf8");
  fs.writeFileSync(path.join(OUT,"README.txt"),
`Newsletter inbox export from notifyy1008@gmail.com
Generated: (see file mtimes)  Window: last 20 days  Messages: ${saved}

Files:
- emails.csv / emails.json : one row per email (segment, from, delivered_to, date, subject, is_issue)
- eml/<segment>/*.eml       : the raw original email of each message (lossless)

'segment' is derived from the +tag the mail was delivered to (or sender domain for the 4
plain-addressed ones: Morning Brew, HR Brew, FindLaw, Babylon Bee). 'unmatched' = not one of
our routed addresses. is_issue=1 means a real newsletter issue (0 = welcome/confirm/verify).
`,"utf8");

  console.log("SAVED", saved, "emails");
  console.log("segments:", JSON.stringify(rows.reduce((a:any,r)=>{a[r.segment]=(a[r.segment]||0)+1;return a;},{})));
  console.log("OUT:", OUT);
})();
