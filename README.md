# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などの機能を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に永続化する ETL パイプライン
- RSS ベースのニュース収集・前処理・LLM によるセンチメント解析（ai.news_nlp）
- マクロセンチメントと ETF の移動平均乖離を組み合わせた市場レジーム判定（ai.regime_detector）
- 研究用途のファクター計算・統計ユーティリティ（research）
- 発注フローの監査ログ（audit テーブル群）初期化ユーティリティ
- データ品質チェック（quality）やカレンダー管理などの補助機能

このリポジトリの設計方針には「ルックアヘッドバイアスを生まない」「DBへの冪等書き込み」「外部 API の堅牢なリトライ」などが反映されています。

---

## 主な機能一覧

- ETL（data.pipeline）
  - run_daily_etl: 市場カレンダー、株価、財務データの差分取得・保存・品質チェック
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（data.jquants_client）
  - fetch / save 関数（ページネーション・レート制御・トークンリフレッシュ対応）
- ニュース NLP（ai.news_nlp）
  - calc_news_window / score_news：ニュースを銘柄別に集約し OpenAI でスコア化
- 市場レジーム判定（ai.regime_detector）
  - score_regime：ETF(1321)のMA乖離とマクロニュースセンチメントを合成してレジームを決定
- 研究用（research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank など
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（data.audit）
  - init_audit_db / init_audit_schema：監査用テーブル群を初期化

---

## 要件 / 依存パッケージ（代表）

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
  - （標準ライブラリ以外は requirements.txt にまとめてください）

※実行環境に応じて追加パッケージが必要になる可能性があります（urllib/ssl等の基本は標準で提供されます）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存モジュールをインストール
   - 簡易例（必要パッケージを列挙している場合）
     ```
     pip install -e .
     pip install duckdb openai defusedxml
     ```
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれに従う

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を使って設定します（自動ロード機能あり）。
   - 重要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=CXXXXXXX
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     KABUSYS_ENV=development  # development|paper_trading|live
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効化したい場合：
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - Settings API を使うコード例:
     ```py
     from kabusys.config import settings
     print(settings.jquants_refresh_token)
     ```

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は最小限のサンプルコード例です。Python スクリプトや REPL から実行できます。

- DuckDB 接続と日次 ETL 実行
  ```py
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 監査 DB 初期化（監査専用 DB）
  ```py
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル群が作成されます
  ```

- ニュースのスコアリング（OpenAI API キー required）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote ai_scores for {n_written} codes")
  ```

- 市場レジーム判定（OpenAI API キー required）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```py
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  ```

- RSS フィード取得（ニュース収集の一部）
  ```py
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点：
- OpenAI 呼び出しや J-Quants API 呼び出しにはそれぞれの API キーが必要です。
- LLM の呼び出しはコストが発生するため、テスト時はモック化（unittest.mock.patch）して実行することを推奨します（コードにもテスト差し替えを想定した設計箇所があります）。

---

## 主要設定項目（環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI APIキー（score_news / score_regime など）
- KABU_API_PASSWORD: kabu API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack 設定
- DUCKDB_PATH: メイン DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（環境モード）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

設定は .env / .env.local に記述しておくと自動的に読み込まれます（プロジェクトルートを .git または pyproject.toml から検出）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内 src/kabusys 以下の代表的な構成）
```
src/kabusys/
├── __init__.py
├── config.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── data/
│   ├── __init__.py
│   ├── audit.py
│   ├── calendar_management.py
│   ├── etl.py
│   ├── jquants_client.py
│   ├── news_collector.py
│   ├── pipeline.py
│   ├── quality.py
│   └── stats.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
└── research/（その他研究用ユーティリティ）
```

各モジュールは概ね以下の責務を持ちます：
- config.py: 環境変数の読み込み・検証
- data/jquants_client.py: J-Quants API 呼び出しと DuckDB への保存
- data/pipeline.py: ETL の上位制御（run_daily_etl 等）
- ai/news_nlp.py / ai/regime_detector.py: LLM を用いたセンチメント / レジーム判定
- research/*: ファクター計算・特徴量探索
- data/audit.py: 監査ログテーブル定義と初期化

---

## 開発・テストのヒント

- LLM / HTTP 外部 API 呼び出しはユニットテストでモック化してください。コード内に差し替えを想定したポイント（_call_openai_api など）が用意されています。
- 自動環境変数読み込みはテストで望ましくない場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- DuckDB に対するテストは ":memory:" を使うと高速です（init_audit_db(":memory:") 等）。

---

## ライセンス / 貢献

（ここにライセンスやコントリビューションポリシーを追記してください）

---

README の補足やサンプル・CI 設定、requirements.txt を追加したい場合は要望を教えてください。README の内容をプロジェクトの実運用手順（デプロイ、cron / systemd でのジョブ実行、自動監視）に合わせて拡張できます。