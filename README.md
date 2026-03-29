# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）。  
ETL、ニュース収集・NLPスコアリング、マーケットカレンダー管理、ファクター計算、監査ログ等を含むモジュール群を提供します。

主な用途:
- J-Quants からの株価・財務・カレンダーの差分ETL
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメントスコア生成
- ETF を用いた市場レジーム判定（LLM とテクニカル指標の合成）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order → execution トレーサビリティ）
- データ品質チェック（欠損、重複、スパイク、日付不整合）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、トークン自動リフレッシュ・レート制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 収集、安全対策（SSRF / gzip / XML 防御））
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ初期化・操作（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: OpenAI を用いた銘柄別センチメント）
  - レジーム検出（score_regime: ETF MA + マクロニュースで市場レジーム判定）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）算出、統計サマリー
- config
  - 環境変数管理（.env 自動ロード、必須チェック、設定アクセス用 Settings オブジェクト）

---

## 前提条件 / 推奨環境

- Python 3.10 以降（型ヒントで `X | Y` を使用）
- 必要な Python パッケージ（少なくとも以下）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI 等）

（プロジェクト固有の依存は requirements.txt を用意していればそちらに従ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最小例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を推奨）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（少なくともこれらを設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで使用）
   - 任意・デフォルト値:
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
     - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH — SQLite 用パス（デフォルト `data/monitoring.db`）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-xxxx...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

5. データベース初期化（監査ログ用の DuckDB を作る例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit_duckdb.duckdb")
   # 返された conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（主要な API サンプル）

以下は Python スクリプトや REPL での利用例です。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査スキーマの初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ETL の個別実行（株価のみ）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
  ```

- 市場カレンダーの判定ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

注意点:
- score_news / score_regime は外部 API（OpenAI）を呼び出します。API キーを渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- ETL は J-Quants API を呼びます。`JQUANTS_REFRESH_TOKEN` を `.env` 等で設定してください。
- 日付の扱いはルックアヘッドバイアス回避のために設計されています（内部で date.today() を使わない処理設計など）。

---

## 環境変数 / 設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用リフレッシュトークン）
- KABU_API_PASSWORD — 必須（kabu API を使う場合）
- OPENAI_API_KEY — 必須（AI スコアリングに必要）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 必須（Slack 通知を行う場合）
- DUCKDB_PATH — DuckDB データファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite データファイル（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル（"DEBUG" など）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

config モジュール経由で Settings オブジェクト（kabusys.config.settings）からアクセス可能です。

---

## ディレクトリ構成

（実際のリポジトリは src/ 配下にパッケージ `kabusys` を配置しています。主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - pipeline.py
      - etl.py
      - jquants_client.py
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py (ETLResult re-export)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/factor_research.py
    - research/feature_exploration.py

（各モジュールは DuckDB 接続を受け取って動作する設計が基本です。）

---

## 運用上の注意 / ベストプラクティス

- API キー／トークンは安全に管理してください（.env は .gitignore に追加）。
- 実運用（live）では KABUSYS_ENV=live に設定し、発注ロジックの安全チェックと監査ログを有効にしてください。
- OpenAI 呼び出しはコストが発生するためバッチサイズやリトライ設定を調整してください（news_nlp/regime_detector 内の定数を参照）。
- DuckDB への大量書き込みや executemany の挙動に注意（モジュール内で注意喚起あり）。
- ETL は差分更新方式を採るため過去データの再取得（backfill_days）設定で API 後出し修正を吸収する運用を推奨。

---

## 参考（開発者向け）

- 主要公開関数:
  - kabusys.data.pipeline.run_daily_etl
  - kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.ai.news_nlp.score_news
  - kabusys.ai.regime_detector.score_regime
  - kabusys.data.audit.init_audit_db / init_audit_schema
  - kabusys.data.calendar_management.{is_trading_day, next_trading_day, prev_trading_day, get_trading_days}
  - kabusys.research.* のファクター計算関数

- 設計上の留意点は各モジュールの docstring に詳細に記載してあります。実装詳細やパラメータはソースコードを参照してください。

---

ご要望があれば、README に以下を追加できます:
- requirements.txt の候補リスト
- 実行例の CLI ラッパー（もし存在すれば）や systemd / cron ジョブ設定例
- .env.example の具体的なテンプレート

必要があれば作成します。