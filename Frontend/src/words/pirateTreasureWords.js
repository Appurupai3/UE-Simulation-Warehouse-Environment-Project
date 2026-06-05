export const wordCategories = [
  {
    id: '1_Nature_Cosmos',
    title: '大自然與宇宙',
    wordCount: 102,
    treasurePack: '海盜寶藏 1',
    storyHint: '船長在暴風雨後登上孤島，沿著月光、星座、森林與山脈的線索尋找發光寶石；如果你聽見海風談到天空和大地，這箱寶藏就在提示自然與宇宙。'
  },
  {
    id: '2_Nautical_Pirate',
    title: '航海與海盜冒險',
    wordCount: 121,
    treasurePack: '海盜寶藏 1',
    storyHint: '黑帆升起，水手握著羅盤穿越暗礁，海盜用船錨、甲板與藏寶圖追逐金幣；這段冒險指向航海與海盜世界。'
  },
  {
    id: '3_Travel_Transport',
    title: '旅遊、交通與航空',
    wordCount: 105,
    treasurePack: '海盜寶藏 1',
    storyHint: '寶藏獵人先搭火車到港口，再換飛機越過雲層，最後乘巴士抵達遙遠城市；所有移動工具都在暗示旅遊、交通與航空。'
  },
  {
    id: '4_History_Fantasy',
    title: '歷史、奇幻與中世紀',
    wordCount: 106,
    treasurePack: '海盜寶藏 1',
    storyHint: '古老城堡裡，騎士守著王冠，巫師翻開羊皮卷，傳說中的巨龍在城牆外盤旋；故事把你帶到歷史、奇幻與中世紀。'
  },
  {
    id: '5_Flora_Fauna',
    title: '動植物與生物界',
    wordCount: 100,
    treasurePack: '海盜寶藏 1',
    storyHint: '鸚鵡帶路穿過藤蔓、花朵與蕨類，狐狸、蝴蝶和鯨魚留下生命的腳印；這些線索提示動植物與生物界。'
  },
  {
    id: '6_Science_Tech',
    title: '科學、科技與醫療',
    wordCount: 100,
    treasurePack: '海盜寶藏 2',
    storyHint: '船醫用顯微鏡研究神祕藥水，工程師啟動機器人與晶片解開密碼鎖；實驗與發明都在指向科學、科技與醫療。'
  },
  {
    id: '7_Business_Law',
    title: '商業、經濟與法律',
    wordCount: 100,
    treasurePack: '海盜寶藏 2',
    storyHint: '海港市集裡，商人談判價格，會計計算利潤，法官審查寶藏契約；這個碼頭故事提示商業、經濟與法律。'
  },
  {
    id: '8_Arts_Culture',
    title: '藝術、文學與休閒娛樂',
    wordCount: 101,
    treasurePack: '海盜寶藏 2',
    storyHint: '夜晚的甲板變成劇場，吟遊詩人朗讀小說，畫家描繪海圖，樂手奏起舞曲；這箱寶藏藏著藝術、文學與休閒娛樂。'
  },
  {
    id: '9_Psychology_Traits',
    title: '心理學與人格特質',
    wordCount: 100,
    treasurePack: '海盜寶藏 2',
    storyHint: '大副觀察船員的勇敢、焦慮、好奇與自信，靠理解每個人的性格解決叛變危機；故事提示心理學與人格特質。'
  },
  {
    id: '10_Abstract_Terms',
    title: '社會城市與進階抽象概念',
    wordCount: 102,
    treasurePack: '海盜寶藏 2',
    storyHint: '海盜來到未來城市，討論自由、秩序、正義、制度與社群合作，才找到最後一把鑰匙；這些概念暗示社會城市與進階抽象概念。'
  }
]

export const treasurePacks = [
  {
    id: 'pirate_treasure_1',
    name: '海盜寶藏 1',
    categoryIds: wordCategories.filter((category) => category.treasurePack === '海盜寶藏 1').map((category) => category.id)
  },
  {
    id: 'pirate_treasure_2',
    name: '海盜寶藏 2',
    categoryIds: wordCategories.filter((category) => category.treasurePack === '海盜寶藏 2').map((category) => category.id)
  }
]

export function getTreasureWordForBox(boxId) {
  const category = wordCategories[(boxId - 1) % wordCategories.length]

  return {
    productName: `${category.treasurePack}｜${category.id}`,
    wordCategory: category.title,
    wordCount: category.wordCount,
    storyHint: category.storyHint,
    treasurePack: category.treasurePack
  }
}
