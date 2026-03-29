KabuSys — 日本株自動売買 / データプラットフォーム
================================

概要
---
KabuSys は日本株の自動売買・データプラットフォーム向けの Python ライブラリ群です。  
主に以下の機能群を備え、データ取得（J-Quants）、ETL、ニュース NLP（LLM）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（取引フローのトレーサビリティ）をサポートします。

主な特徴
---
- J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御、リトライ）
- DuckDB を想定した ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ベースのニュース収集（SSRF 対策、トラッキング除去、前処理）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析（news_nlp）と市場レジーム判定（regime_detector）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
- 環境変数/設定の集中管理（.env 自動読み込み、プロジェクトルート検出）

機能一覧（モジュール概観）
---
- kabusys.config
  - 環境変数読み込み（.env/.env.local をプロジェクトルートから自動読み込み）
  - settings オブジェクト経由で設定を取得（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD
- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch / save / auth / rate limiter）
  - pipeline: run_daily_etl、個別の ETL ジョブ（prices / financials / calendar）
  - news_collector: RSS 取得＋raw_news への保存ロジック（SSRF 対策・トラッキング削除）
  - calendar_management: 市場カレンダー（is_trading_day / next_trading_day / calendar_update_job）
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出・ai_scores 書き込み
  - regime_detector.score_regime: ETF と LLM を組み合わせた市場レジーム判定・market_regime 書き込み
- kabusys.research
  - calc_momentum / calc_value / calc_volatility（ファクター群）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索・統計）

前提・依存関係
---
- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- （任意）ネットワークアクセス: J-Quants API、RSS フィード、OpenAI API

セットアップ手順
---
1. リポジトリをチェックアウト / コピー
   - 例: git clone <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .            # パッケージセットアップ済みの setup.cfg/pyproject がある前提
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を作成すると自動読み込みされます。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - OPENAI_API_KEY=sk-xxxx
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C012345...
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - テスト等で自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB（監査DB等）の準備
   - 監査用 DB を初期化するには:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - その他のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）は ETL 実行前に作成されている必要があります（schema 初期化スクリプトを用意してください）。audit モジュールのみ init 関数を提供しています。

使い方（基本例）
---
- DuckDB 接続を作成して ETL を実行する
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    res = run_daily_etl(conn, target_date=date(2026,3,20))
    print(res.to_dict())

- ニュースセンチメントのスコア取得（ai.news_nlp.score_news）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"scored {n} codes")

  - 備考: api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照します。記事がない場合は LLM 呼び出しを行わず 0 を返します。テスト時は内部の _call_openai_api をモック可能です。

- 市場レジーム評価（ai.regime_detector.score_regime）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成

- 研究用関数の例（モメンタム計算）
  - from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    recs = calc_momentum(conn, target_date=date(2026,3,20))

設定の注意点
---
- settings（kabusys.config.settings）は必須設定を _require で検証します。必要な環境変数が欠けていると ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN）。
- KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。
- 自動 .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。テスト時に自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

テストとモック
---
- OpenAI 呼び出しは各モジュール内の _call_openai_api を経由しており、ユニットテストでは unittest.mock.patch によって差し替え可能です（kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api など）。
- news_collector._urlopen もモック可能で、ネットワーク I/O を差し替えられます。

ディレクトリ構成
---
(主要ファイルのみ抜粋)
- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュースセンチメント / ai_scores 書き込み
    - regime_detector.py         -- 市場レジーム判定（ETF + LLM）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（fetch/save）
    - pipeline.py                -- ETL パイプライン（run_daily_etl など）
    - etl.py                     -- ETLResult の再エクスポート
    - news_collector.py          -- RSS 収集・前処理
    - calendar_management.py     -- 市場カレンダー管理
    - quality.py                 -- データ品質チェック
    - stats.py                   -- zscore_normalize 等
    - audit.py                   -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         -- Momentum / Value / Volatility 等
    - feature_exploration.py     -- forward returns, IC, summary
  - research/...                  -- 研究用ユーティリティ
  - その他（strategy, execution, monitoring 等のエントリは __all__ で公開想定）

運用上の注意
---
- Look-ahead bias（未来情報の参照）を避けるため、本ライブラリは target_date を明示的に受け取り、datetime.today() 等を内部ロジックで参照しない方針を採っています。バックテスト実行時は過去時点で利用可能なデータのみを用いるようにしてください。
- J-Quants のレート制限（120 req/min）を守る実装になっていますが、複数プロセスで同一 API を叩く運用時は追加の調整が必要です。
- OpenAI 呼び出しや外部 API は失敗耐性（フェイルセーフ）を設計に入れていますが、異常時のログ監視を必ず行ってください。

今後の拡張（例）
---
- raw_*/schema 初期化スクリプトの追加（ETL 実行前にテーブル作成できるように）
- CLI / サービス化（cron/jupyter 以外での運用向け）
- モニタリング・アラート連携（Slack / Prometheus）

ライセンス / コントリビュート
---
（該当リポジトリのライセンス方針に従ってください）

---

この README はコードベースの主要な機能と利用方法をまとめた簡易ドキュメントです。詳細な API 仕様やスキーマ定義・運用手順は別途ドキュメント（Design docs / DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README を拡張して CLI コマンド例や schema SQL を付加できます。