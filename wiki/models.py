from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class WikiPage(models.Model):
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="wiki_pages",
    )
    title = models.CharField("titre", max_length=255)
    slug = models.SlugField("slug", max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_wiki_pages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "page wiki"
        verbose_name_plural = "pages wiki"
        unique_together = [("project", "slug")]
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "projects:wiki_page",
            kwargs={"identifier": self.project.identifier, "slug": self.slug},
        )

    @property
    def current_revision(self):
        return self.revisions.order_by("-version").first()

    @property
    def content(self):
        rev = self.current_revision
        return rev.content if rev else ""

    @property
    def version(self):
        rev = self.current_revision
        return rev.version if rev else 0


class WikiPageRevision(models.Model):
    page = models.ForeignKey(
        WikiPage,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    version = models.PositiveIntegerField("version")
    content = models.TextField("contenu (Markdown)")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="wiki_revisions",
    )
    comment = models.CharField("commentaire d'édition", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "révision wiki"
        verbose_name_plural = "révisions wiki"
        unique_together = [("page", "version")]
        ordering = ["-version"]

    def __str__(self):
        return f"{self.page.title} v{self.version}"

    def get_absolute_url(self):
        return reverse(
            "projects:wiki_revision",
            kwargs={
                "identifier": self.page.project.identifier,
                "slug": self.page.slug,
                "version": self.version,
            },
        )
