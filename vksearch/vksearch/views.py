from django.shortcuts import render, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models import Community
from .forms import CommunitiesFilterForm


COMMUNITIES_PER_PAGE = 50
COMMUNITIES_LIMIT = 5 * COMMUNITIES_PER_PAGE


@csrf_exempt
@require_GET
@login_required(login_url='/user/login', redirect_field_name=None)
def communities_view(req):
    form = CommunitiesFilterForm(req.GET)
    if form.is_valid():
        communities = Community.objects.select(
            form.cleaned_data['ordering'], form.cleaned_data["inverted"],
            form.cleaned_data['min_members'], form.cleaned_data['max_members'],
            form.cleaned_data['min_audience'], form.cleaned_data['max_audience'],
            form.cleaned_data['min_audience_perc'], form.cleaned_data['max_audience_perc'],
            form.cleaned_data['sex'], form.cleaned_data['age_ranges'],
            form.cleaned_data['countries'], form.cleaned_data['apps']
        )[:COMMUNITIES_LIMIT]
        paginator = Paginator(communities, COMMUNITIES_PER_PAGE)
        page_num = req.GET.get('page', 1)
        try:
            communities = paginator.page(page_num)
        except (PageNotAnInteger, EmptyPage):
            raise Http404()
    else:
        communities = []
    return render(req, 'communities.html', {
        'communities': communities,
        'form': form
    })
