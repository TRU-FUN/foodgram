from rest_framework.pagination import PageNumberPagination

DEFAULT_PAGE_SIZE = 6
MAX_PAGE_SIZE = 100


class SubscriptionPagination(PageNumberPagination):
    """Пагинация для списка подписок."""
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE
