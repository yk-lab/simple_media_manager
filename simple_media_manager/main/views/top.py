from typing import Any, Dict

from django.views.generic.base import TemplateView

from ..models import Album


class TopView(TemplateView):
    template_name = 'top.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return dict(
            **super().get_context_data(**kwargs),
            albums=Album.objects.all(),
        )
