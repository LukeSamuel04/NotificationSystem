// frontend/verify-env.js
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const colors = {
  reset: "\x1b[0m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m"
};

console.log(`${colors.cyan}🚀 开始执行 AI Priority Inbox 环境自动化测试...${colors.reset}\n`);

const checks = [
  {
    name: "依赖包完整性 (node_modules)",
    check: () => fs.existsSync(path.join(__dirname, 'node_modules')),
    fix: "运行 npm install"
  },
  {
    name: "Tailwind 配置文件 (tailwind.config.js)",
    check: () => {
      const p = path.join(__dirname, 'tailwind.config.js');
      if (!fs.existsSync(p)) return false;
      const content = fs.readFileSync(p, 'utf8');
      return content.includes('content') && content.includes('./src');
    },
    fix: "手动创建 tailwind.config.js 并配置 content 路径"
  },
  {
    name: "PostCSS 配置文件 (postcss.config.js)",
    check: () => fs.existsSync(path.join(__dirname, 'postcss.config.js')),
    fix: "手动创建 postcss.config.js"
  },
  {
    name: "CSS 指令检查 (src/index.css)",
    check: () => {
      const p = path.join(__dirname, 'src/index.css');
      if (!fs.existsSync(p)) return false;
      const content = fs.readFileSync(p, 'utf8');
      return content.includes('@tailwind base');
    },
    fix: "在 index.css 顶部添加 @tailwind 指令"
  },
  {
    name: "Vite 路径别名配置 (vite.config.ts)",
    check: () => {
      const p = path.join(__dirname, 'vite.config.ts');
      if (!fs.existsSync(p)) return false;
      const content = fs.readFileSync(p, 'utf8');
      return content.includes('alias') && content.includes('@');
    },
    fix: "在 vite.config.ts 中配置 resolve.alias"
  }
];

let allPassed = true;

checks.forEach(item => {
  try {
    if (item.check()) {
      console.log(`${colors.green} [PASS] ${colors.reset} ${item.name}`);
    } else {
      console.log(`${colors.red} [FAIL] ${colors.reset} ${item.name}`);
      console.log(`       👉 修复建议: ${item.fix}`);
      allPassed = false;
    }
  } catch (e) {
    console.log(`${colors.red} [ERR ] ${colors.reset} ${item.name} (发生错误: ${e.message})`);
    allPassed = false;
  }
});

console.log("\n" + "─".repeat(50));
if (allPassed) {
  console.log(`\n${colors.green}✨ 恭喜！你的前端开发环境已完美就绪。${colors.reset}`);
  console.log(`${colors.yellow}现在你可以运行 'npm run dev' 开启你的 AccountDashboard 之旅了！${colors.reset}\n`);
} else {
  console.log(`\n${colors.red}❌ 环境仍存在异常，请根据上方的修复建议进行处理。${colors.reset}\n`);
}