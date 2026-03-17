# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants API や RSS フィードからデータを取得して DuckDB に格納する ETL、マーケットカレンダー管理、ニュース収集、品質チェック、監査ログなど、アルゴリズムトレーディング基盤に必要な機能を提供します。

主な設計方針：
- API レート制限遵守・リトライ・トークン自動リフレッシュ
- DuckDB への冪等（ON CONFLICT）保存
- ニュース収集での SSRF / XML 攻撃保護、メモリ DoS 対策
- 品質チェック（欠損・重複・スパイク・日付不整合）
- シグナル→発注→約定の監査トレースを強く意識した設計

---

## 機能一覧

- 環境変数/設定管理（.env 自動読み込み対応）
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、マーケットカレンダー取得
  - レートリミット、指数バックオフ、401 時のトークンリフレッシュ対応
  - ページネーション対応
- DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定 / next/prev / 期間内営業日取得）
- ニュース収集モジュール（RSS → raw_news、ID生成、記事内の銘柄抽出）
  - defusedxml、SSRF 防止、受信サイズ制限、トラッキングパラメータ除去
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal / order_request / executions 用テーブル）
- execution/strategy/monitoring 用のパッケージ構成（拡張用プレースホルダ）

---

## 必要条件（Prerequisites）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を使用しているため requests は必須ではありませんが、運用上のツールは任意で追加してください。

例（仮の requirements.txt を用いる場合）:
```
duckdb
defusedxml
```

インストール例:
```
python -m pip install duckdb defusedxml
```

---

## 環境変数

アプリ設定は環境変数から読み込みます（プロジェクトルートに .env / .env.local があれば自動読み込み）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token() により idToken を取得します。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、デフォルト: development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (任意、デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

注意: .env のパースは一般的な shell 形式をサポートし、クォート・エスケープ・コメントの扱いに配慮しています。

---

## セットアップ手順

1. リポジトリをチェックアウト
2. Python 環境を準備（推奨: 仮想環境）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```
4. 環境変数を設定（.env をプロジェクトルートに作成）
   - 必須変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - .env.example がある想定で、そこを参考に作成してください（config._require は未設定時に .env.example を参照するよう促します）。
5. DuckDB スキーマ初期化
   Python インタラクティブまたはスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
6. 監査ログスキーマ（別途必要な場合）
   ```python
   from kabusys.data import audit
   # 既に init_schema で接続した conn を渡して監査テーブルを追加
   audit.init_audit_schema(conn, transactional=True)
   ```
7. （任意）監視やその他 DB 初期化

---

## 使い方（簡易ガイド）

※ 以下は一例です。実運用ではログ設定や例外処理などを追加してください。

- J-Quants の id token を取得する:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
```

- DuckDB スキーマ初期化（再掲）:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を与えれば特定日で実行可能
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- ニュース収集ジョブ（既知銘柄リストを渡して銘柄紐付けも実行）:
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "6501"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- データ品質チェックを単独で実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- audit スキーマの初期化（監査 DB を別ファイルで管理する場合）:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 重要な実装ノート（運用時の注意点）

- J-Quants API はレートリミット（120 req/min）を遵守するため、クライアントは内部でスロットリングを実施します。大量取得時は時間を要します。
- HTTP エラー（408/429/5xx）に対する指数バックオフのリトライを行います。401 はトークン自動リフレッシュを試みて1回だけ再試行します。
- DuckDB への挿入は基本的に ON CONFLICT DO UPDATE / DO NOTHING により冪等性を確保しています。
- news_collector は SSRF 対策、XML パースの安全化（defusedxml）、受信サイズ制限（デフォルト 10MB）など安全対策が組み込まれています。
- calendar_management は market_calendar が存在しない場合は曜日ベースのフォールバック（平日を営業日扱い）を使用します。
- audit.init_audit_schema() はタイムゾーンを UTC に固定します（SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース収集・記事保存・銘柄抽出
    - schema.py               -- DuckDB スキーマ定義と初期化
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  -- マーケットカレンダー管理・ジョブ
    - audit.py                -- 監査ログ（signal/order_request/executions）
    - quality.py              -- データ品質チェック
  - strategy/
    - __init__.py  -- 戦略層の拡張ポイント（実装はプロジェクトで追加）
  - execution/
    - __init__.py  -- 発注周りの拡張ポイント（実装はプロジェクトで追加）
  - monitoring/
    - __init__.py  -- 監視機能の拡張ポイント（実装はプロジェクトで追加）

---

## 開発・拡張のヒント

- strategy/ と execution/ はプレースホルダです。独自戦略やブローカー連携はここに実装してください。
- ETL やニュース収集はテストしやすいように id_token 注入や _urlopen のモック差し替えが考慮されています。ユニットテストは外部コールをモックして実行してください。
- DuckDB を使っているため、ローカル実行・検証が高速に行えます。運用時はバックアップ戦略を検討してください。

---

必要であれば、README に含めるサンプル .env.example や systemd/cron のジョブ例、運用チェックリスト（監視項目）等も作成します。どの項目を追加しますか？