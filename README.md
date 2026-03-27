# KabuSys

日本株向け自動売買・データプラットフォームライブラリです。ETL（J-Quants 連携）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（取引トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価日足・財務データ・上場銘柄情報・JPX カレンダーを差分取得／保存
  - DuckDB に対する冪等保存（ON CONFLICT）をサポート
  - 日次 ETL パイプライン（run_daily_etl）による一括処理
- ニュース収集・NLP
  - RSS フィードからのニュース収集（SSRF・サイズ制限・トラッキング除去対応）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント付与（score_news）
  - マクロニュース + ETF MA200 乖離を合成した市場レジーム判定（score_regime）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー等
  - クロスセクション Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出（quality モジュール）
  - 全チェックの集約（run_all_checks）
- 監査ログ・トレーサビリティ
  - シグナル → 発注 → 約定までの監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数／.env ファイルの自動読み込み（プロジェクトルートを基準）
  - settings オブジェクト経由で設定値を取得

---

## 必要条件（推奨）

- Python 3.10+
- 依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 開発中に editable install を使う場合:
     ```
     pip install -e .
     ```
   - 最低限の手動インストール:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし OS の環境変数が優先されます）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
   - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN — Slack 通知ボット（必要に応じて）
   - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
   - OPENAI_API_KEY — OpenAI API を使う処理（score_news / score_regime）では必要
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_ENV — one of: development / paper_trading / live
   - LOG_LEVEL — one of: DEBUG / INFO / WARNING / ERROR / CRITICAL

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要 API と利用例）

注意: 多くの関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- settings を参照する
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live, settings.log_level)
  ```

- DuckDB 接続を作る
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付与（OpenAI API キー必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print("scored stocks:", n_written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- RSS 取得（ニュースコレクタの単体利用）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査ログ用 DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 以後 audit_conn を使用して監査テーブルへ挿入・参照できます
  ```

- 便利な設計上の注意
  - OpenAI を利用する関数は api_key 引数から優先的にキーを受け取り、None の場合は環境変数 `OPENAI_API_KEY` を参照します。
  - ETL / ニュース処理はルックアヘッドバイアスを避けるよう設計されています（内部で date.today() を不用意に参照しない等）。
  - J-Quants API にはレートリミットとリトライ処理が組み込まれていますが、ID トークンの設定（JQUANTS_REFRESH_TOKEN）を忘れないでください。

---

## .env の自動読み込み挙動

- 自動読み込みはデフォルトで有効です（パッケージがロードされた際にプロジェクトルートを探索して `.env` / `.env.local` を読み込みます）。
- 優先順位（高→低）:
  1. OS 環境変数（既にプロセスに設定されているもの）
  2. .env.local（プロジェクトルート、.env の上書き）
  3. .env（プロジェクトルート）
- 自動読み込みを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する

.env の行パースはシェル風の様々な書き方（`export KEY=val`、クォート、コメント等）に対応しています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: pipeline 等を参照)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py
- (将来的に strategy / execution / monitoring パッケージが含まれます)

（上記は主要モジュールの一覧であり、細かいモジュールや補助ユーティリティはソースツリーを参照してください）

---

## 開発・運用時の注意

- OpenAI や J-Quants の API キーは機密情報です。リポジトリにコミットしないでください。
- DuckDB のファイルパスは settings.duckdb_path で管理されます。共有環境ではファイルの排他アクセスに注意してください（複数プロセスの同時書き込みなど）。
- news_collector は外部 RSS を取得します。SSRF 対策・サイズ制限が組み込まれていますが、運用時は信頼できるソースのみ登録してください。
- ETL 実行はログ（LOG_LEVEL）を適宜設定してモニタリングしてください。

---

もし README に追加したい例（cron ジョブの設定、具体的な .env.example、Docker 化手順、CI 設定など）があれば教えてください。必要に応じて追記します。