# KabuSys

日本株向けの自動売買 / データパイプラインライブラリです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（オーダー → 約定トレース）などを含むモジュール群を提供します。

以下はコードベース（src/kabusys）に基づく README です。

## プロジェクト概要
KabuSys は次の用途を想定しています。
- J-Quants API からの差分 ETL（株価日足 / 財務 / JPX カレンダー）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- ETF（1321）200日移動平均乖離とマクロセンチメントの合成による日次市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ用の DuckDB スキーマ（signal_events / order_requests / executions）初期化ユーティリティ

設計方針の要点：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を不用意に参照しない）
- 冪等性（DB 保存は ON CONFLICT / UPSERT）を重視
- 外部 API 呼び出しにはリトライ・バックオフ・レート制御を実装
- テスト容易性のため API キーを引数注入できる箇所あり

## 主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、get_id_token）
  - market calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector（RSS 取得、前処理、ID 正規化、SSRF 対策）
  - quality（欠損・重複・スパイク・日付不整合チェック）
  - audit（監査テーブル初期化 / init_audit_db）
  - stats（zscore 正規化）
- ai/
  - news_nlp.score_news：銘柄単位のニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime：ETF 1321 の MA200 とマクロセンチメントを合成して market_regime テーブルへ書き込む
- research/
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
- config.Settings：環境変数ベースの設定管理（自動で .env / .env.local をロード、必要項目を検証）

## セットアップ手順（ローカル開発向け）
1. Python 環境を用意（推奨: 3.10+）
   - 仮想環境の作成例：
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使用してください（このリポジトリ断片にない場合は主要依存のみ列挙します）：
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （必要に応じて logging / urllib 等は標準ライブラリ）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注周りを使う場合）
     - SLACK_BOT_TOKEN — Slack 通知に使用する場合
     - SLACK_CHANNEL_ID — 同上
     - OPENAI_API_KEY — OpenAI を利用する AI 機能で必要
   - 任意・デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — monitoring 用 SQLite（デフォルト data/monitoring.db）
   - サンプル `.env`（プロジェクトに追加してください）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB 初期スキーマ（必要に応じて）
   - audit 用 DB を初期化する例：
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - その他テーブル（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime など）は ETL / 初期化スクリプトで作成することを想定しています（この断片では schema 初期化全面の記述は含まれていません）。

## 使い方（主要なユースケース例）
- ETL（デイリーパイプライン）実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（ai_scores への保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```
  - OPENAI_API_KEY が環境変数で設定されていれば api_key 引数は不要です。gpt-4o-mini（JSON mode）を使用します。API 呼び出しはバッチ（最大 20 銘柄/回）で行い、429・ネットワーク断・5xx は指数バックオフでリトライします。失敗した銘柄はスキップして継続します。

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```
  - ETF 1321 の直近 200 日 MA 乖離（重み 70%）とマクロ記事の LLM センチメント（重み 30%）を合成し、market_regime テーブルに書き込みます。OpenAI キーは引数または環境変数 OPENAI_API_KEY で渡します。API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックします。

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- データ品質チェック
  ```python
  import duckdb
  from kabusys.data.quality import run_all_checks
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

- 監査テーブル初期化（既存 DB に追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants のリフレッシュトークン）
- OPENAI_API_KEY — 必須（AI 機能を使う場合）
- KABU_API_PASSWORD — 必須（kabuステーション API を使う場合）
- KABU_API_BASE_URL — 任意（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — 必須（Slack 通知を使う場合）
- SLACK_CHANNEL_ID — 必須（Slack 通知を使う場合）
- DUCKDB_PATH — 任意（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 任意（デフォルト data/monitoring.db）
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

## ディレクトリ構成（主要ファイル）
（ルートの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limiting）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）および ETLResult
    - etl.py — ETL の公開インターフェース（ETLResult の再エクスポート）
    - news_collector.py — RSS 収集・前処理（SSRF 対策、ID 正規化）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマの初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

## 注意事項 / 実運用に関する補足
- AI（OpenAI）呼び出しは API レート・コストに依存します。必ず適切な API キーとモニタリングを行ってください。
- J-Quants API にはレート制限（120 req/min）があります。jquants_client 内で固定間隔スロットリングを実装していますが、運用環境ではさらに考慮してください。
- DuckDB のバージョン互換性に注意（executemany の空リスト挙動など、コード内で対応を入れています）。
- 本リポジトリ断片はフルパッケージの一部です。実行前にスキーマ初期化・必要テーブル作成、または ETL による初回データロードが必要になることがあります。
- production / live 環境では KABUSYS_ENV を `live` に設定し、発注まわりの設定（kabu API）や監査ログを必ず確実に運用してください。

---

不明点や README に追記して欲しいコマンド・サンプルがあれば教えてください。例えば「初期スキーマ作成スクリプト例」や「デイリーバッチの systemd / cron 例」などを追加できます。