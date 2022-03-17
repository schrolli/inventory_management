from datetime import datetime
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView
from django.core.exceptions import ObjectDoesNotExist
import extra_views
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import UserPassesTestMixin


from . import forms
from . import models

# Create your views here.


def index(request):
    return render(request, "inventory/index.html")


class DetailLocationView(DetailView):
    model = models.Location
    # (request, pk, unique_identifier):
    # Prio 1
    # return HttpResponse("Here should be an overview of items stored at this location.")

    # TODO
    # * inform user, if redirect with changed unique_identifier occurred

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.unique_identifier != kwargs["unique_identifier"]:
            return redirect(self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


def update_location(request, pk, unique_identifier):
    pass


def view_item(request, pk):
    return redirect(reverse_lazy("update_item", args=[pk]))


class CreateItemView(UserPassesTestMixin, extra_views.CreateWithInlinesView):
    model = models.Item
    inlines = [forms.ItemImageInline, forms.ItemLocationInline]
    template_name = "inventory/item_formset.html"
    form_class = forms.CreateItemForm
    extra_context = {"title": _("Create Item")}

    def get_success_url(self):
        location = self._get_location()
        if location is not None \
                and self.request.POST and "save_and_mark" in self.request.POST:
            # redirect to location
            return reverse_lazy('view_location', args=[location.id, location.unique_identifier])
        # Preserve location_id
        url = reverse_lazy("create_item")
        if self.request.GET and "location_id" in self.request.GET and location:
            url += "?location_id=%s" % self._get_location().id
        return url
    
    def _get_location(self):
        if self.request.GET and "location_id" in self.request.GET:
            location_id = self.request.GET.get("location_id")
            try:
                location_id = int(location_id)
                return models.Location.objects.get(pk=location_id)
            except (ValueError, models.Location.DoesNotExist):
                pass
        return None

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        location = self._get_location()
        if location is not None:
            ctxt['location'] = location
        return ctxt

    def construct_inlines(self):
        location = self._get_location()
        if location is not None:
            self.kwargs["initial"] = [{"location": location}]
        return super().construct_inlines()
    
    def test_func(self):
        # Logged in or @ZAM
        return not self.request.user.is_anonymous or \
            self.request.session.get('is_zam_local')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.POST and 'save_and_mark' in self.request.POST:
            location = self._get_location()
            location.last_complete_inventory = datetime.now()
            location.save()
        return response


class UpdateItemView(UserPassesTestMixin, extra_views.UpdateWithInlinesView):
    model = models.Item
    inlines = [forms.ItemImageInline, forms.ItemLocationInline]
    template_name = "inventory/item_formset.html"
    form_class = forms.ItemForm
    extra_context = {"title": _("Update Item")}

    def get_success_url(self):
        return self.object.get_absolute_url()

    def test_func(self):
        # Logged in or @ZAM
        return not self.request.user.is_anonymous or \
            self.request.session.get('is_zam_local', False)


class SearchableItemListView(UserPassesTestMixin, extra_views.SearchableListMixin, ListView):
    # matching criteria can be defined along with fields
    search_fields = ["name", "category__name"]
    search_date_fields = []
    model = models.Item
    exact_query = False
    wrong_lookup = False

    # def get_search_query(self):
    #    # Overwrite query here
    #    return super().get_search_query()

    def test_func(self):
        # Logged in or @ZAM
        return not self.request.user.is_anonymous or \
            self.request.session.get('is_zam_local', False)
