from io import BytesIO
from xhtml2pdf import pisa


def generate_shopping_cart_pdf(ingredients_by_recipe, combined_ingredients):
    html = '''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Список покупок</title>
        <style>
            @page {
                size: A4;
                margin: 20mm;
            }
            @font-face {
                font-family: "DejaVu";
                src: url("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
                    format("truetype");
            }
            body {
                font-family: "DejaVu", sans-serif;
                font-size: 14px;
            }
            h1 {
                text-align: center;
            }
            ul {
                list-style-type: none;
                padding: 0;
            }
            li {
                margin-bottom: 5px;
            }
        </style>
    </head>
    <body>
        <h1>Список покупок</h1>
    '''

    for recipe, items in ingredients_by_recipe.items():
        html += f'<h2>{recipe}</h2><ul>'
        for ingredient in items:
            html += f'<li>{ingredient}</li>'
        html += '</ul>'

    html += '<h2>Общие ингредиенты:</h2><ul>'
    for name, data in sorted(combined_ingredients.items()):
        html += f'<li>{name} ({data["unit"]}) - {data["amount"]}</li>'
    html += '</ul></body></html>'

    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)

    if pisa_status.err:
        return None

    return pdf_buffer
