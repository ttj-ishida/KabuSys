# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー追跡）などのユーティリティを提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants API）と DuckDB への冪等保存（ON CONFLICT）
- 日次 ETL パイプライン（差分取得／バックフィル／品質チェック）
- ニュース収集（RSS）と OpenAI による銘柄別センチメント付与（ai_scores）
- マクロ＋テクニカル（ETF 1321 の MA200 乖離）に基づく市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマの初期化・管理
- 設定は .env / 環境変数で管理（auto load 対応、配布後も動作する設計）

---

## 機能一覧（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数の取得
- kabusys.data
  - jquants_client: データ取得 / 保存（daily quotes, financials, market calendar）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector: RSS 取得・前処理・raw_news への保存
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログスキーマ作成・init_audit_db
  - stats: zscore 正規化
- kabusys.ai
  - news_nlp.score_news: OpenAI を用いた銘柄別センチメント付与（ai_scores へ書込）
  - regime_detector.score_regime: MA200 とマクロニュースを合成した日次市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 動作要件（例）

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- インターネット接続（J-Quants / OpenAI / RSS 取得用）

（実際の依存は pyproject.toml / requirements.txt を確認してください）

---

## セットアップ手順

1. リポジトリをクローンし、開発環境へインストール（src パッケージ構成）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"  # あるいは pip install -e .
   ```
   （プロジェクトに依存記述がない場合は必要なパッケージを手動で pip install してください: duckdb openai defusedxml）

2. 環境変数 / .env を用意する  
   ルートに `.env`（と必要なら `.env.local`）を置くと自動で読み込まれます（読み込みはプロジェクトルートの検出に依存）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（代表例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key

   任意（デフォルト値あり）:
   - KABUSYS_ENV=development | paper_trading | live  (default: development)
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動読み込みを無効にする場合

   .env の基本例（プロジェクトルートの `.env.example` を参照して作成してください）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. DuckDB データベース（初期化は必要に応じて）  
   デフォルトパスは `data/kabusys.duckdb`。初回はディレクトリを作成しておくか、関数側で自動作成されます（audit.init_audit_db は親ディレクトリを自動作成します）。

---

## 基本的な使い方（コード例）

以下は簡単な利用例です。プロジェクトをインストールした Python 環境で実行してください。

- 日次 ETL を実行（J-Quants からデータ取得して DuckDB に保存・品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付与（OpenAI を利用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {written} codes")
  ```

- 市場レジーム判定（MA200 とマクロニュースの合成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルへ操作可能
  ```

- ファクター計算（研究用途）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  mom = calc_momentum(conn, d)
  val = calc_value(conn, d)
  vol = calc_volatility(conn, d)
  ```

---

## よく使う設定 / 環境変数

- KABUSYS_ENV: development / paper_trading / live（安全のため本番は `live` を使用）
- OPENAI_API_KEY: OpenAI クライアントの API キー（news_nlp / regime_detector で使用）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（jquants_client が id_token を取得）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を指定すると .env の自動ロードを無効化

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py            - ニュースの OpenAI スコアリング（ai_scores 書込み）
    - regime_detector.py     - 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得・保存）
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - news_collector.py      - RSS 収集と raw_news 保存
    - calendar_management.py - 市場カレンダーの管理・営業日判定
    - quality.py             - データ品質チェック
    - stats.py               - zscore_normalize 等の統計ユーティリティ
    - audit.py               - 監査ログスキーマ定義・初期化
    - etl.py                 - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     - Momentum / Value / Volatility の計算
    - feature_exploration.py - forward returns, IC, summary, rank

---

## 注意事項 / ベストプラクティス

- OpenAI の API 呼び出しは外部ネットワーク・コストが発生します。テスト時はモックを利用してください（モジュール内の _call_openai_api はテスト置換を想定）。
- DuckDB に対する executemany の空リストは一部バージョンでエラーになるため、コード側で空チェックを行っています。スキーマや DuckDB のバージョン差に注意してください。
- ETL / スコアリング関数はルックアヘッドバイアス対策が施されています（date 引数を明確に渡す設計）。バックテストでは取得済みデータの整合性を確保してから利用してください。
- .env は秘密情報を含むためバージョン管理に含めないでください。`.env.example` を用意してテンプレートを管理するのが推奨です。
- 本番環境での発注（kabu 関連）やライブ取引を行う場合は十分なテスト・リスク管理を行ってください（このリポジトリはアルゴリズムのユーティリティ群を提供するもので、発注ロジックの最終責任は利用者にあります）。

---

必要に応じて README を拡張します（例: pyproject/Poetry セットアップ、CI、例 .env.example、具体的な SQL スキーマ定義、よくあるトラブルシュート）。どのセクションの詳細を追加しますか？