# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、データ品質チェック、DuckDBスキーマ、監査ログ用スキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API からの市場データ（株価日足・財務データ・マーケットカレンダー）の取得と DuckDB への保存
- RSS を用いたニュース収集と記事の前処理、銘柄コード抽出・紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

設計上の特徴：
- API レート制御、リトライ、トークン自動更新、冪等保存（ON CONFLICT）を考慮
- Look-ahead bias を防ぐため取得時刻（UTC）を記録
- SSRF・XML Bomb 等への対策（ニュース収集）

---

## 主な機能一覧

- kabusys.config
  - .env / 環境変数の自動ロード／管理、必須変数チェック
- kabusys.data.jquants_client
  - J-Quants API クライアント（id_token 取得、日足／財務／カレンダーの取得、DuckDB への保存）
- kabusys.data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- kabusys.data.pipeline
  - 差分 ETL（calendar / prices / financials）と総合日次 ETL 実行、品質チェック連携
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news 保存、銘柄抽出・紐付け
- kabusys.data.calendar_management
  - カレンダー更新ジョブ、営業日判定・next/prev_trading_day、期間内営業日取得
- kabusys.data.quality
  - 欠損・重複・スパイク・日付不整合チェック
- kabusys.data.audit
  - 監査ログ用テーブル定義と初期化（signal / order_request / executions）
- kabusys.execution / kabusys.strategy / kabusys.monitoring
  - 各レイヤーの拡張ポイント（現状パッケージ初期化のみ）

---

## セットアップ手順

前提：
- Python 3.10 以上（ソース内で `X | Y` 型注釈を使用）
- Git（リポジトリからクローンする場合）

1. リポジトリをクローン（任意）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存ライブラリをインストール
   - 必要な主要パッケージ:
     - duckdb
     - defusedxml
   - インストール例:
     ```
     pip install duckdb defusedxml
     ```
   - プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください:
     ```
     pip install -r requirements.txt
     # または
     pip install -e .
     ```

4. 環境変数（.env）の準備  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。  
   必須の環境変数例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL は任意（デフォルト: http://localhost:18080/kabusapi）
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack 通知（必要な場合）
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境設定
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトから直接呼ぶ簡単な例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル DB を作成してスキーマを作る
```

- 監査ログスキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema などで得た接続
```

- J-Quants から日足を取得して保存（手動呼び出し例）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
# id_token は自動的に settings.jquants_refresh_token から取得される
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

- 日次 ETL を実行する（カレンダー先読み・バックフィル含む）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date 省略で today
print(result.to_dict())
```

- RSS ニュース収集と DB 保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄リストの set（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

補足：
- jquants_client の _request はレートリミット・リトライ・トークンリフレッシュを管理します。通常は id_token を明示せずに組み込みのキャッシュを使ってください。
- news_collector.fetch_rss は SSRF/サイズ/圧縮/XML 安全性を考慮しています。テスト時は _urlopen をモックできます。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須/オプション) — Slack 通知トークン
- SLACK_CHANNEL_ID (必須/オプション) — Slack チャンネルID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視系の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（1 を設定）

設定は .env / .env.local に置けます（.env.local は .env の上書き）。パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を基準）から自動ロードされます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義（バージョン: 0.1.0）
- config.py — 環境変数・設定管理（.env 読み込み、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、取得＆保存ロジック
  - news_collector.py — RSS 収集・前処理・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック統合）
  - calendar_management.py — マーケットカレンダー管理・ジョブ
  - audit.py — 監査ログ用スキーマ初期化（signal / order_request / executions）
  - quality.py — データ品質チェック（QualityIssue, 各種チェック）
- strategy/
  - __init__.py — 戦略層拡張ポイント（将来的に戦略実装を追加）
- execution/
  - __init__.py — 発注・約定関連の拡張ポイント
- monitoring/
  - __init__.py — 監視関連の拡張ポイント

主要ファイルの役割:
- data/schema.py: 全レイヤー（Raw/Processed/Feature/Execution）およびインデックス定義を持つ。init_schema で DB を初期化。
- data/jquants_client.py: API 呼び出しのレート制御、リトライ、ページネーション、DuckDB への冪等保存関数を実装。
- data/news_collector.py: RSS の安全な取得、テキスト前処理、記事ID生成（URL 正規化＋SHA256）、DuckDB への保存（チャンク／トランザクション）を実装。
- data/pipeline.py: ETL の差分ロジック、バックフィル、品質チェック統合を提供する高レベル API（run_daily_etl 等）。

---

## ログ・デバッグ

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- モジュール毎に logger を取得しているため、アプリ側で logging.basicConfig 等を設定してください。

---

## テスト・開発時の注意点

- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にしてください（テストで環境汚染を避けたい場合など）。
- news_collector のネットワーク呼び出しは _urlopen をモックしてテストできます。
- jquants_client のリフレッシュ動作やページネーションは外部 API に依存するため、ユニットテストでは HTTP レスポンスをモックしてください。
- DuckDB はシングルファイル DB なので、テストでは ":memory:" を使うことでインメモリ DB を利用できます。

---

## 付記 / 今後の拡張

- strategy / execution / monitoring パッケージは拡張ポイントとして用意されています。戦略実装、リスク管理、実際の発注ロジック（証券会社 API 連携）を追加することでフルスタック運用が可能です。
- Slack 通知や監査ログのカスタム処理は各モジュールにフックする形で実装してください。

---

不明点や README に追加したい利用シナリオ（例: CIジョブ、Cron 実行例、Slack 通知の設定例など）があれば教えてください。必要に応じてサンプルスクリプトも作成します。