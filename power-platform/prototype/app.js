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

const saved=localStorage.getItem("mcpd-prototype-screen");
if(saved && document.getElementById(`screen-${saved}`)) showScreen(saved);
