# FoodGo — Лабораторийн ажил №5

Өмнөх `food-order-starter` төслөөс өргөтгөсөн Flask + SQLite + Bootstrap хоол захиалгын сургалтын веб.

## Mac / VS Code

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Chrome: http://127.0.0.1:5000

Эхлээд **Бүртгүүлэх**, дараа нь **Нэвтрэх**, хоолны тоо ширхэг сонгож **Сагсанд нэмэх**, **Захиалга баталгаажуулах**. Хэрэглэгч зөвхөн өөрийн захиалгыг үзнэ.

## Тест

Сервер ажиллаж буй терминалыг хаахгүйгээр шинэ Terminal дээр:

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

TC01–TC06 нь лабораторийн шаардлагын дагуу, нэмэлт 2 тест нь захиалга хадгалалт/хувийн мэдээллийн эрх ба CSRF шалгана.

## GitHub

```bash
git init
git add .
git commit -m "Implement Lab 5 login cart validation and tests"
```

GitHub дээр хоосон repository үүсгээд:

```bash
git branch -M main
git remote add origin https://github.com/USERNAME/food-order-starter.git
git push -u origin main
```

## Анхаарах зүйл

- `food.db` нь локал SQLite сан бөгөөд `.gitignore`-д орсон.
- Хуучин `food.db`-г шинэ төсөлд **хуулж болохгүй**: хуучин хүснэгтийн бүтэц өөр. Шинэ хавтсаас эхлүүл.
- Нууц үг хэшлэгдэнэ, SQL параметртэй, Jinja автоматаар HTML escape хийнэ, POST хүсэлт CSRF token шалгана.
- `SECRET_KEY`-г бодит орчинд заавал environment variable-аар тохируулна. `debug=True` зөвхөн локал сургалтад.
- Энэ нь сургалтын demo; бодит төлбөр болон хүргэлтийн API байхгүй.
