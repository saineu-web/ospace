from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"

    def items(self):
        return ["web:home", "web:drivers", "web:how_it_works", "web:app", "web:families", "web:about", "web:media", "web:faq", "web:contact", "web:privacy"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return {"web:home": 1.0, "web:drivers": 0.9, "web:families": 0.8}.get(item, 0.6)
