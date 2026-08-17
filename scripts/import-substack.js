const Parser = require("rss-parser");
const TurndownService = require("turndown");
const fs = require("fs");
const path = require("path");

const FEED_URL = "https://curatedtravelmagazine.substack.com/feed";
const POSTS_DIR = path.join(__dirname, "..", "_posts");

// Make sure the folder exists
if (!fs.existsSync(POSTS_DIR)) {
  fs.mkdirSync(POSTS_DIR, { recursive: true });
}

async function run() {
  const parser = new Parser({
    customFields: {
      item: ["content:encoded"],
    },
  });

  const feed = await parser.parseURL(FEED_URL);
  const turndown = new TurndownService({
    headingStyle: "atx",
    codeBlockStyle: "fenced",
  });

  let created = 0;

  for (const entry of feed.items) {
    const date = new Date(entry.pubDate || entry.isoDate);
    if (isNaN(date)) {
      console.warn("Skipping item with bad date:", entry.title);
      continue;
    }

    const slug = (entry.title || "untitled")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80); // keep filename reasonable

    const filename = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}-${slug}.md`;
    const filepath = path.join(POSTS_DIR, filename);

    if (fs.existsSync(filepath)) {
      console.log("Already exists:", filename);
      continue;
    }

    // Prefer full content
    const html = entry["content:encoded"] || entry.content || entry.contentSnippet || "";
    const markdown = turndown.turndown(html);

    const title = (entry.title || "Untitled").replace(/"/g, '\\"');

    const frontMatter = `---
layout: post
title: "${title}"
date: ${date.toISOString()}
source: "Substack"
original_url: "${entry.link || ""}"
---

`;

    fs.writeFileSync(filepath, frontMatter + markdown, "utf8");
    console.log("Created:", filename);
    created++;
  }

  console.log(`Done. Created ${created} new post(s).`);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
