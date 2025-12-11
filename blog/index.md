---
layout: default
title: Curated Travel
---



<!-- Latest Blog Posts -->
## Latest Posts
<div class="blog-grid">
  {% for post in site.posts %}
  <a href="{{ post.url }}" class="post-card">
    <div class="post-img-wrapper">
      {% if post.image %}
      <img src="{{ post.image }}" alt="{{ post.title }}">
      {% else %}
      <img src="/assets/images/blog/default-post.jpg" alt="{{ post.title }}">
      {% endif %}
    </div>
    <div class="post-info">
      <p class="post-date">{{ post.date | date: "%B %d, %Y" }}</p>
      <h3 class="post-title">{{ post.title }}</h3>
      <p class="post-excerpt">{{ post.excerpt | strip_html | truncate: 120 }}</p>
      <span class="read-more">Read More →</span>
    </div>
  </a>
  {% endfor %}
</div>
