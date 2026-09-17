# Codeforces + GitHub Sync

هذا المشروع يربط بين Codeforces و GitHub بحيث كل مشكلة يتم حلها على Codeforces يتم إضافتها تلقائيًا إلى مستودع GitHub.

## الفكرة

- نقرأ قائمة المشاكل المحلولة من Codeforces API.
- نطابقها مع ملف cache محلي.
- إذا كانت هناك مشكلة جديدة، يتم إنشاء ملف Markdown داخل مجلد `codeforces/` في المستودع.
- ثم يتم رفع الملف إلى GitHub عبر GitHub API.

## التشغيل

1. أنشئ GitHub token مع صلاحية `repo`.
2. احفظه في متغير البيئة:

```bash
export GITHUB_TOKEN=your_token_here
```

3. شغّل السكربت:

```bash
python sync_cf_to_github.py \
  --handle your_cf_handle \
  --repo owner/repository \
  --branch main
```

4. لتجربة بدون رفع فعلي:

```bash
python sync_cf_to_github.py \
  --handle your_cf_handle \
  --repo owner/repository \
  --branch main \
  --dry-run
```

## مثال

```bash
python sync_cf_to_github.py \
  --handle ahmed_ali \
  --repo ECPC/competitive-programming \
  --branch main
```

## ملاحظات

- لا يوجد webhook مباشر رسمي لـ Codeforces إلى GitHub مباشرة.
- الحل العملي هو: تشغيل السكربت دورياً (مثلاً كل 30 دقيقة أو كل يوم) أو عبر GitHub Actions.
- إذا أردت، يمكنني تجهيز نسخة جاهزة تعمل في GitHub Actions وتُشغّل تلقائيًا كل ساعة.
