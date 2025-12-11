---
layout: default
title: Blog
---
<section class="blog-preview">
  <h2>Latest Posts</h2>
  <div class="blog-grid">
    {% for post in site.posts %}
      <a href="{{ post.url }}" class="post-card">
        <div class="post-img-wrapper">
          {% if post.image %}
            <img src="{{ post.image }}" alt="{{ post.title }}">
          {% endif %}
        </div>
        <div class="post-info">
          <p class="post-date">{{ post.date | date: "%B %d, %Y" }}</p>
          <h3 class="post-title">{{ post.title }}</h3>
          <p class="post-excerpt">{{ post.excerpt | strip_html | truncatewords: 30 }}</p>
          <span class="read-more">Read More →</span>
        </div>
      </a>
    {% endfor %}
  </div>
</section>
