# KabuSys

バージョン: 0.1.0

日本株自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログの土台を提供します。

---

## 概要

KabuSys は日本株の自動売買システム構築に必要なデータ基盤と運用ユーティリティを含む Python パッケージです。主に以下を担います。

- J-Quants API を用いた時系列データ・財務情報・マーケットカレンダーの取得
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS からのニュース収集と銘柄抽出（SSRF や XML 攻撃対策を考慮）
- マーケットカレンダーの管理（営業日の判定、next/prev 等ユーティリティ）
- 監査（監査テーブル群）でシグナル→発注→約定のトレーサビリティ確保

設計上、レート制限やリトライ、冪等性（ON CONFLICT 等）やセキュリティ対策（SSRF、XML防御）に配慮しています。

---

## 主な機能一覧

- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、トレーディングカレンダーの取得
  - レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存用ユーティリティ（save_*）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、品質チェック連携
  - run_daily_etl：カレンダー取得 → 株価取得 → 財務取得 → 品質チェック

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理（URL除去・空白正規化）、記事ID生成（正規化URL の SHA-256 部分）
  - SSRF/リダイレクト検査、gzip サイズチェック、defusedxml による安全解析
  - raw_news / news_symbols への冪等保存

- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブル定義と初期化（Raw / Processed / Feature / Execution）
  - インデックス定義や init_schema / get_connection

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内営業日取得、カレンダー夜間更新ジョブ

- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue を返し、ETL 判定の補助に利用

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査向けテーブル群の初期化
  - UTCタイムスタンプ設定、冪等キーによる発注重複防止

---

## セットアップ手順

前提
- Python 3.10 以上（型注記や | ユニオンを使用）
- Git（パッケージのルート検出に使用）

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <リポジトリ>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール（最低限）
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）
   pip install -e .

4. 環境変数の設定
   - プロジェクトルートの `.env`、その上書き用に `.env.local` を配置可能
   - 自動読み込みはデフォルト有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV: 開発環境。'development'（デフォルト）、'paper_trading'、'live'
   - LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト 'INFO'）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合に '1' を設定
   - KABUSYS_API_BASE_URL: kabu API のベース URL（必要に応じて）

   データベースパス:
   - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH: 監視用 SQLite のパス（`data/monitoring.db`）

   サンプル .env（プロジェクトルートに配置）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易ガイド）

以下は Python のインタラクティブ / スクリプト例です。

- DuckDB スキーマ初期化

```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリは自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

- 監査スキーマ初期化（既存接続に追加）

```python
from kabusys.data import audit
# conn は schema.init_schema の戻り値
audit.init_audit_schema(conn)
```

- 日次 ETL の実行（J-Quants トークンは settings 経由で自動利用）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブの実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 事前用意した有効コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- J-Quants トークン取得 / API 呼び出し例

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

ログは標準的な logging モジュールを利用します。LOG_LEVEL 環境変数で制御してください。

---

## 注意点 / 運用メモ

- 自動環境変数読み込み:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` を読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - テストやカスタム初期化時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

- API レート制限:
  - J-Quants は 120 req/min を想定。内部で固定間隔の RateLimiter によるスロットリングがあります。

- 冪等性:
  - raw テーブルへの保存は ON CONFLICT DO UPDATE / DO NOTHING が活用され、再実行に耐える設計です。

- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）、XML の安全パーサ（defusedxml）を使用します。

- 品質チェック:
  - ETL 後の品質チェックは Fail-Fast ではなく問題の収集に留めます。呼び出し元が severity に応じて処理可否を決める設計です。

---

## ディレクトリ構成

概観（主要ファイル）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（自動 .env ロード、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
    - news_collector.py       — RSS ニュース収集・前処理・保存
    - schema.py               — DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - pipeline.py             — ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py  — マーケットカレンダー管理ユーティリティ / 夜間ジョブ
    - audit.py                — 監査ログ用テーブルの初期化
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py             — 戦略層（拡張ポイント）
  - execution/
    - __init__.py             — 発注・broker 接続等（拡張ポイント）
  - monitoring/
    - __init__.py             — 監視・メトリクス（拡張ポイント）

---

## 開発・拡張ポイント

- strategy / execution / monitoring パッケージはプレースホルダ（拡張想定）。シグナル生成、ポートフォリオ管理、発注ブローカー連携、監視アラートなどをここに実装します。
- DuckDB スキーマは DataPlatform.md を想定した階層構造。必要なカラムやインデックスは schema.py で定義されています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を set して環境を制御し、DuckDB の ":memory:" を使うと容易にテスト可能です。

---

## ライセンス / コントリビューション

（この README にはライセンス情報・コントリビュート手順を明記していません。実際のリポジトリに合わせて LICENSE や CONTRIBUTING を追加してください。）

---

不明点や README に追記して欲しい項目があれば教えてください。README にサンプル .env.example や CI / テスト手順のテンプレを追加できます。