const rewards = [
  { day: 1, name: "萌星", kind: "signed" },
  { day: 2, name: "稀有房间礼物", image: "assets/rare-bottle.png", selected: true, special: "稀有" },
  { day: 3, name: "星座装扮奖励", image: "assets/constellation-ring.png" },
  { day: 4, name: "玩豆+100", image: "assets/bean.png" },
  { day: 5, name: "玩豆+120", image: "assets/bean.png" },
  { day: 6, name: "玩豆+140", image: "assets/bean.png" },
  { day: 7, name: "连续签到奖励", image: "assets/grand-prize.png", wide: true, special: "大奖" },
];

const rewardGrid = document.querySelector(".reward-grid");
const popupShell = document.querySelector(".popup-shell");
const closeButton = document.querySelector(".close-button");
const reminderToggle = document.querySelector(".reminder-toggle");

function updateStageScale() {
  if (document.body.classList.contains("audit-mode")) {
    document.documentElement.style.setProperty("--stage-scale", "1");
    return;
  }
  const scale = Math.min(window.innerWidth / 1179, window.innerHeight / 2556);
  document.documentElement.style.setProperty("--stage-scale", String(scale));
}

function createRewardCard(reward) {
  const card = document.createElement("article");
  card.className = [
    "reward-card",
    reward.selected ? "reward-card--selected" : "",
    reward.wide ? "reward-card--wide" : "",
  ].filter(Boolean).join(" ");
  card.dataset.day = String(reward.day);

  const dayBadge = document.createElement("span");
  dayBadge.className = reward.kind === "signed" ? "day-badge day-badge--stamp" : "day-badge";
  dayBadge.textContent = reward.kind === "signed" ? "已签" : `第${reward.day}天`;
  card.append(dayBadge);

  if (reward.special) {
    const special = document.createElement("span");
    special.className = reward.day === 7 ? "grand-badge" : "rare-badge";
    special.textContent = reward.special;
    card.append(special);
  }

  const art = document.createElement("div");
  art.className = "reward-art";
  art.setAttribute("aria-hidden", "true");
  if (reward.image) {
    const image = document.createElement("img");
    image.src = reward.image;
    image.alt = "";
    art.append(image);
  } else {
    const star = document.createElement("span");
    star.className = "signed-star";
    art.append(star);
  }
  card.append(art);

  const name = document.createElement("p");
  name.className = "reward-name";
  name.textContent = reward.name;
  card.append(name);
  return card;
}

for (const reward of rewards) rewardGrid.append(createRewardCard(reward));

function closePopup() {
  if (!popupShell.hidden) popupShell.hidden = true;
}

closeButton.addEventListener("click", closePopup);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closePopup();
});

reminderToggle.addEventListener("click", () => {
  const checked = reminderToggle.getAttribute("aria-checked") === "true";
  reminderToggle.setAttribute("aria-checked", String(!checked));
});

if (new URLSearchParams(window.location.search).has("audit")) {
  document.body.classList.add("audit-mode");
}

updateStageScale();
window.addEventListener("resize", updateStageScale);
