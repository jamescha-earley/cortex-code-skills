#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const SKILLS_DIR = path.join(os.homedir(), ".snowflake", "cortex", "skills");
const PKG_ROOT = path.resolve(__dirname, "..");

function getAvailableSkills() {
  return fs
    .readdirSync(PKG_ROOT)
    .filter((name) => {
      if (name.startsWith(".") || name === "bin" || name === "node_modules" || name === "skills") return false;
      const dir = path.join(PKG_ROOT, name);
      if (!fs.statSync(dir).isDirectory()) return false;
      return fs.existsSync(path.join(dir, "SKILL.md"));
    });
}

function ensureSkillsDir() {
  fs.mkdirSync(SKILLS_DIR, { recursive: true });
}

function installSkill(name) {
  const src = path.join(PKG_ROOT, name);
  if (!fs.existsSync(src) || !fs.existsSync(path.join(src, "SKILL.md"))) {
    console.error(`Error: "${name}" is not a valid skill in this package.`);
    console.error(`Run "cortex-code-skills list" to see available skills.`);
    process.exit(1);
  }

  ensureSkillsDir();
  const dest = path.join(SKILLS_DIR, name);

  fs.cpSync(src, dest, { recursive: true });
  console.log(`Installed "${name}" -> ${dest}`);
}

function list() {
  const skills = getAvailableSkills();
  console.log("Available skills:\n");
  for (const name of skills) {
    const installed = fs.existsSync(path.join(SKILLS_DIR, name, "SKILL.md"));
    const marker = installed ? " (installed)" : "";
    console.log(`  ${name}${marker}`);
  }
  console.log(`\nInstall with: npx cortex-code-skills install <name>`);
}

function install(args) {
  if (args.includes("--all")) {
    const skills = getAvailableSkills();
    ensureSkillsDir();
    for (const name of skills) {
      installSkill(name);
    }
    console.log(`\nInstalled ${skills.length} skills.`);
    return;
  }

  if (args.length === 0) {
    console.error("Usage: cortex-code-skills install <skill-name> [--all]");
    process.exit(1);
  }

  for (const name of args) {
    installSkill(name);
  }
}

function usage() {
  console.log(`cortex-code-skills — Install custom skills for Cortex Code

Usage:
  cortex-code-skills list                  List available skills
  cortex-code-skills install <name> ...    Install one or more skills
  cortex-code-skills install --all         Install all skills

Skills are installed to ~/.snowflake/cortex/skills/`);
}

const [cmd, ...args] = process.argv.slice(2);

switch (cmd) {
  case "list":
    list();
    break;
  case "install":
    install(args);
    break;
  case "help":
  case "--help":
  case "-h":
    usage();
    break;
  default:
    usage();
    process.exit(cmd ? 1 : 0);
}
