from rest_framework import status
from rest_framework.response import Response


class RelationHandlerMixin:
    """
    Миксин для обработки добавления и удаления объектов отношений
    (например, избранное или список покупок).
    """
    def handle_relation(self, request, model, relation_name, serializer_class):
        recipe = self.get_object()
        relation_qs = model.objects.filter(user=request.user, recipe=recipe)

        if request.method == 'POST':
            data = {'user': request.user.id, 'recipe': recipe.id}
            serializer = serializer_class(
                data=data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        deleted_count, _ = relation_qs.delete()
        if deleted_count:
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'error': f'Не найдено в {relation_name}'},
            status=status.HTTP_400_BAD_REQUEST
        )
