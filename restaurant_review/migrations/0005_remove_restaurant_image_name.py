# Generated by Django 4.0.4 on 2022-04-19 16:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant_review', '0004_alter_restaurant_image_name_alter_review_image_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='restaurant',
            name='image_name',
        ),
    ]
