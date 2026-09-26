const buttons=[...document.querySelectorAll(".nav-item")];
const screens=[...document.querySelectorAll(".screen")];

function showScreen(key){
  buttons.forEach(b=>b.classList.toggle("active",b.dataset.screen===key));
  screens.forEach(s=>s.classList.toggle("active",s.id===`screen-${key}`));
  localStorage.setItem("mcpd-prototype-screen",key);
  window.scrollTo({top:0,behavior:"smooth"});
}

buttons.forEach(button=>button.addEventListener("click",()=>showScreen(button.dataset.screen)));

document.querySelectorAll(".ratings button").forEach(button=>{
  button.addEventListener("click",()=>{
    const row=button.closest(".ratings");
    row.querySelectorAll("button").forEach(b=>b.classList.remove("selected"));
    button.classList.add("selected");
  });
});

const portalFilter=document.querySelector("#portal-filter");
const portalGroup=document.querySelector("#portal-group");
const portalRole=document.querySelector("#portal-role");
const portalCards=[...document.querySelectorAll("#portal-grid .module-card")];
const portalDetail=document.querySelector("#portal-detail");
function filterPortal(){
  const query=(portalFilter?.value||"").toLowerCase();
  const group=portalGroup?.value||"all";
  const role=portalRole?.value||"all";
  portalCards.forEach(card=>{
    const visible=(!query||card.textContent.toLowerCase().includes(query))&&(group==="all"||card.dataset.group===group)&&(role==="all"||card.dataset.role.split(" ").includes(role));
    card.style.display=visible?"block":"none";
  });
}
[portalFilter,portalGroup,portalRole].forEach(control=>control?.addEventListener("input",filterPortal));
[portalGroup,portalRole].forEach(control=>control?.addEventListener("change",filterPortal));
portalCards.forEach(card=>card.addEventListener("click",()=>{
  portalCards.forEach(item=>item.classList.remove("selected"));
  card.classList.add("selected");
  portalDetail.innerHTML=`<h2>${card.querySelector("b").textContent}</h2><p>${card.querySelector("span").textContent}</p><div class="two-col"><div><h3>Preview workflow</h3><div class="task"><span>Open module workspace</span><b class="green">READY</b></div><div class="task"><span>Use synthetic records</span><b class="green">ENABLED</b></div><div class="task"><span>Connect Dataverse / flows</span><b class="orange">TENANT BUILD</b></div></div><div><h3>Access boundary</h3><p class="muted">Role-aware access follows the source-controlled table policies. Production records, credentials and evidence remain disabled in this preview.</p></div></div>`;
}));

const saved=localStorage.getItem("mcpd-prototype-screen");
if(saved && document.getElementById(`screen-${saved}`)) showScreen(saved);
