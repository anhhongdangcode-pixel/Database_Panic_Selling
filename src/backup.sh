#!/bin/bash

# =========================================================
# SYSTEM BACKUP SCRIPT
# Recommended to run via Cron Job daily at 00:00 (Midnight)
# Example Cron: 0 0 * * * /path/to/backup.sh
# =========================================================

# Thư mục lưu backup
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

# Tạo tên file theo ngày giờ
FILE_NAME="backup_panic_selling_$(date +%Y%m%d_%H%M%S).sql"

echo "Bắt đầu backup database 'panic_selling_project'..."

# Thực hiện lệnh mysqldump
mysqldump -u root -p panic_selling_project > "$BACKUP_DIR/$FILE_NAME"

echo "✅ Backup thành công! Đã lưu tại: $BACKUP_DIR/$FILE_NAME"