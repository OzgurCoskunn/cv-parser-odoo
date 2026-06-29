# Porting Log - barcode_wms

Bu dosya, Odoo 19'a geçiş (porting) sürecinde yapılan değişiklikleri takip etmek için oluşturulmuştur.

## [2026-01-20] - InventoryAdjustments Scan Error FIX
- **Dosya:** `static/src/component/Components/Components.js`
- **Hata:** `TypeError: text.split is not a function`. `scan` metoduna string yerine event objesi gidiyordu.
- **Çözüm:** `onScan` metodunda gelen parametrenin (event veya string) kontrolü yapıldı ve `scan` metoduna her zaman string gönderilmesi sağlandı.
