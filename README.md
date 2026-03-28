# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買基盤のためのライブラリ群です。J-Quants や各種 RSS / OpenAI を利用してデータ収集・ETL・品質チェック・AI ベースのニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ管理などを行えるよう設計されています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API からの株価・財務・市場カレンダーの差分取得（ETL）と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理、ニュース→銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄別 / マクロ）評価
- ETF を使った市場レジーム判定（MA200 とマクロセンチメントの合成）
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ初期化ユーティリティ
- 環境変数管理と自動 .env ロード（プロジェクトルートの検出に基づく）

設計上の方針として、バックテストでのルックアヘッドバイアスを避けるために date/datetime の参照を明示的に受け渡す実装になっています。また外部 API 呼び出しにはリトライやフェイルセーフが組み込まれています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config.Settings）
  - J-Quants トークン / kabu API / Slack / DB パス / 環境モード等の取得
  - .env / .env.local の自動読み込み（無効化可）
- Data モジュール
  - jquants_client: J-Quants API 呼び出し（取得・保存・認証・レート制御・リトライ）
  - pipeline / etl: 日次 ETL パイプライン（市場カレンダー、株価、財務、品質チェック）
  - news_collector: RSS 取得・前処理・raw_news への保存支援（SSRF対策・size制限）
  - calendar_management: 営業日判定、next/prev 営業日取得、カレンダー更新ジョブ
  - quality: 欠損/重複/スパイク/日付不整合チェック
  - audit: 監査テーブル初期化（signal_events, order_requests, executions）
  - stats: z-score 正規化ユーティリティ
- AI モジュール（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して ai_scores テーブルに保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
  - 両者とも OpenAI（gpt-4o-mini）を利用（JSON Mode を期待）
- Research モジュール（kabusys.research）
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（推奨）

- Python 3.10 以上（型ヒントで | を利用）
- 主要依存パッケージ:
  - duckdb
  - openai
  - defusedxml

環境によっては以下も必要になる場合があります:
- requests 等（本コード内では標準 urllib を利用）
- 他の運用ツール（例: kabu API と連携する実装がある場合）

---

## セットアップ手順

1. 仮想環境作成（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - 必須（実行する機能に応じて）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY
   - 任意 / デフォルト:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト "development"
     - KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"
     - LOG_LEVEL — デフォルト "INFO"

   .env を使用する場合はプロジェクトルートに `.env` / `.env.local` を配置（自動読み込み）。自動読み込みを無効にするには：
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. データディレクトリの作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトや対話実行での使用例。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメント（AI）スコアリング
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定済みなら api_key は省略可
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} ai_scores")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（監査専用）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)     # Path オブジェクト
  print(settings.env)             # 'development' 等
  ```

---

## 注意事項 / 運用上のポイント

- ルックアヘッドバイアス防止: ほとんどの関数は内部で date.today() を使わず、target_date を引数で受け取ります。バックテスト時は適切な target_date を渡してください。
- OpenAI 呼び出し:
  - レスポンスは厳密な JSON を期待していますが、パース失敗時はフォールバック（0.0やスキップ）する設計です。
  - API キーは引数で明示的に渡す事もできます（テスト容易化）。
- J-Quants クライアント:
  - レートリミット（120 req/min）を守る実装になっています。
  - 401 を受けた場合は自動でリフレッシュして再試行します。
- news_collector は RSS → raw_news の保存を行います。外部からの RSS を取得するため SSRF 対策やサイズ上限、gzip 解凍制限などの安全対策が組み込まれています。
- DuckDB の executemany は空リスト渡しが問題となるバージョンがあるため、各所で空チェックを行っています。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルの一覧（src/kabusys 配下）。実際はさらにファイルやテストがあるかもしれませんが、本リポジトリ内の主要モジュールは次の通りです。

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
      - jquants_client.py
      - pipeline.py
      - etl.py
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py (再エクスポート)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - (その他: strategy, execution, monitoring パッケージが __all__ に含まれていますが、ここに示したコードベースでは未掲示)

各モジュールの役割は前節の「主な機能一覧」を参照してください。

---

## よく使う環境変数（名前と説明）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

---

## 貢献 / 開発上のヒント

- テスト時は環境変数自動ロードを無効化するか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して下さい。
- OpenAI 呼び出しやネットワーク I/O はテストでモックしやすいように内部関数を分離しています（例: _call_openai_api, _urlopen）。
- DuckDB を使ったクエリは生 SQL を用いる設計です。スキーマ変更時は保存関数（save_*）や ETL の挙動を確認してください。

---

この README はリポジトリのコード内容（config / data / ai / research 等）に基づき作成しています。追加の実行例や運用手順（cron ジョブ、監視、Slack 通知など）のドキュメントが必要であれば、用途に応じて別途追記します。