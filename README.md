# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのライブラリ群です。データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、監査ログ、カレンダー管理などを備え、戦略実装や注文実行のための土台を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API を用いた株価（日足）・財務データ・マーケットカレンダーの取得と DuckDB への永続化（冪等性を考慮）
- RSS からのニュース収集と銘柄コード紐付け（SSRF・XML攻撃対策を考慮）
- ETL（差分取得、バックフィル、品質チェック）の統合パイプライン
- マーケットカレンダーによる営業日判定ユーティリティ
- 監査ログ用スキーマ（シグナル→発注→約定のトレース）
- 戦略（strategy）・発注実行（execution）・監視（monitoring）のためのパッケージ構造

設計面の特徴：
- API レート制限・リトライ・トークン自動更新対応
- DuckDB を用いた軽量かつ SQL ベースのデータ管理
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 冪等処理（ON CONFLICT を利用）により安全な再実行が可能

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須環境変数の取得）
  - 自動読み込みの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants クライアント（jquants_client）
  - 株価日足、財務データ、マーケットカレンダーの取得
  - レートリミッティング、リトライ、トークンリフレッシュ
  - DuckDB への保存関数（冪等）
- ニュース収集（news_collector）
  - RSS 取得、XML サニタイズ（defusedxml 使用）
  - URL 正規化（トラッキングパラメータ除去）、記事 ID の SHA-256 ハッシュ化
  - SSRF 対策（スキーム検証、ホストのプライベート判定、リダイレクト検査）
  - DuckDB への一括挿入（トランザクション、INSERT … RETURNING）
  - 銘柄コード抽出・紐付け
- スキーマ定義と初期化（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを定義
  - インデックス作成、init_schema / get_connection API
- ETL パイプライン（data.pipeline）
  - 日次 ETL（カレンダー→株価→財務→品質チェック）
  - 差分取得、バックフィル、品質チェックの統合
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ
- 監査ログスキーマ（data.audit）
  - signal_events / order_requests / executions を含む監査ログ初期化
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- パッケージ構成により strategy・execution・monitoring を実装可能（拡張ポイント）

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに Union | を使用）
- duckdb
- defusedxml
- その他標準ライブラリ（urllib, logging 等）

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数の準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local による上書き可）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD      （kabu API のパスワード）
   - SLACK_BOT_TOKEN        （Slack 通知用トークン）
   - SLACK_CHANNEL_ID       （Slack チャンネル ID）

   任意（デフォルトあり）:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) デフォルト development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト INFO

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB）
   - Python REPL かスクリプト内で:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

6. 監査 DB を別に作る場合:
   - from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡易例）

以下は主要な利用例です。実運用ではログ設定や例外処理、スケジューラ（cron / Airflow / Dagster 等）を組み合わせてください。

- スキーマ初期化
```
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集（RSS）と保存
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes を渡すことで記事→銘柄紐付けを行う
known_codes = {"7203", "6758", "9432"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- J-Quants の ID トークン取得（必要に応じて）
```
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

- 監査スキーマ初期化（既存の conn に追加）
```
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

補足:
- ETL やニュース収集は定期バッチで動かすことが想定されています（cron、ジョブランナー等）。
- run_daily_etl は品質チェックを行い、QualityIssue のリストを返します。重大な品質エラーがある場合は通知・手動確認を行ってください。

---

## ディレクトリ構成

プロジェクトの主要ファイル配置（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント（取得・保存）
    - news_collector.py           # RSS ニュース収集、前処理、DB 保存
    - schema.py                   # DuckDB スキーマ定義・初期化
    - pipeline.py                 # ETL パイプライン（日次 ETL 等）
    - calendar_management.py      # マーケットカレンダー管理
    - audit.py                    # 監査ログスキーマと初期化
    - quality.py                  # データ品質チェック
  - strategy/
    - __init__.py                 # 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                 # 発注 / ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                 # 監視・アラート（拡張ポイント）

ドキュメント / 設計参照:
- DataPlatform.md（設計に従った各モジュールの振る舞いを反映）
- README.md（本ファイル）

---

## 運用上の注意点

- 環境変数には機密情報が含まれるため .env ファイルはバージョン管理に入れないでください（.gitignore に追加）。
- J-Quants の API レート制限（120 req/min）を尊重しています。get_id_token や fetch 系は内部でレート制御とリトライを行います。
- ニュース収集は外部 URL を取り扱うため SSRF 対策（スキーム検証、プライベート IP 判定、リダイレクト検査）や XML パースに defusedxml を使用していますが、運用環境での追加監視も推奨します。
- DuckDB ファイルのバックアップや運用ポリシー（保存先、ローテーション）は運用チームで決めてください。デフォルトは data/kabusys.duckdb。
- ETL は再実行可能（冪等）設計ですが、外部からの手動 DB 更新等は想定外の挙動を招くことがあります。

---

もし README に追加したい具体的なセクション（例: CI/CD、テスト方法、より詳細な API 使用例）があれば教えてください。README をその内容に合わせて拡張します。