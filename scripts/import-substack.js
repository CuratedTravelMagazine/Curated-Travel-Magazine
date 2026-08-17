const Parser = require("rss-parser");
const TurndownService = require("turndown");
const fs = require("fs");
const path = require("path");

const FEED_URL = "https://curatedtravelmagazine.substack.com/feed";
const POSTS_DIR = path.join(__dirname, "..", "_posts");

async function run() {
  const parser = new Parser();
  const feed = await parser.parseURL(FEED_URL);
  const turndown = new TurndownService();

  for (const entry of feed.items) {
    const date = new Date(entry.pubDate);
    const slug = entry.title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");

    const filename = `${date.getFullYear()}-${String(
      date.getMonth() + 1
    ).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}-${slug}.md`;

    const filepath = path.join(POSTS_DIR, filename);

    if (fs.existsSync(filepath)) {
      console.log("Already exists:", filename);
      continue;
    }

    const markdown = turndown.turndown(entry["content:encoded"] || entry.content);

    const frontMatter = `---
layout: post
title: "${entry.title.replace(/"/g, '\\"')}"
date: ${date.toISOString()}
source: "Substack"
original_url: "${entry.link}"
---

`;

    fs.writeFileSync(filepath, frontMatter + markdown);
    console.log("Created:", filename);
  }
}

run();
