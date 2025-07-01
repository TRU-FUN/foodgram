from rest_framework import status
from rest_framework.response import Response


class RelationHandlerMixin:
    """
    Миксин для обработки добавления и удаления объектов отношений
    (например, избранное или список покупок).
    """
    def handle_relation(self, request, pk, model, relation_name):
        recipe = self.get_object()
        relation = model.objects.filter(user=request.user, recipe=recipe)

        if request.method == 'POST':
            if relation.exists():
                return Response(
                    {'error': f'Уже добавлено в {relation_name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=request.user, recipe=recipe)
            return Response(
                {'success': f'Добавлено в {relation_name}'},
                status=status.HTTP_201_CREATED
            )

        if relation.exists():
            relation.delete()
            return Response(
                {'success': f'Удалено из {relation_name}'},
                status=status.HTTP_204_NO_CONTENT
            )

        return Response(
            {'error': f'Не найдено в {relation_name}'},
            status=status.HTTP_400_BAD_REQUEST
        )
