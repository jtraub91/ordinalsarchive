from django.shortcuts import render


def index(request):
    results = []
    query = request.GET.get("q")
    if query:
        results.append(f"no results found for {query}")
    return render(request, "base.html", context={"results": results})
