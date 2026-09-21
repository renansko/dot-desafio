from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="BookRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("author", models.CharField(max_length=200)),
                ("publication_date", models.DateField()),
                ("summary", models.TextField(max_length=5000)),
            ],
            options={"ordering": ["id"]},
        )
    ]
