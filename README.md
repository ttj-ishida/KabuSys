# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）によるセンチメント算出、研究用ファクター計算、監査ログ（発注 → 約定トレーサビリティ）などを提供します。

## 主な特徴
- J-Quants API 経由の差分取得（株価・財務・市場カレンダー）と DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と OpenAI による銘柄毎センチメント算出（news_nlp）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログスキーマ（signal_events / order_requests / executions）および初期化ユーティリティ
- 環境変数ベースの設定管理（自動 .env 読み込み / 保護）

---

## 機能一覧（モジュール別）
- kabusys.config
  - Settings: 環境変数から設定値を取得（自動 .env 読み込み）
- kabusys.data
  - jquants_client: J-Quants API ラッパー（取得・保存・認証・レート制御・リトライ）
  - pipeline: run_daily_etl 等の ETL 実行と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集と前処理（SSRF対策・サイズ制限）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログスキーマ生成・監査DB初期化
  - stats: z-score 正規化などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（OpenAI）
  - regime_detector.score_regime: 市場レジーム判定（MA + マクロセンチメント）
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 前提 / 必要環境
- Python 3.9+
- 主要依存:
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
- ネットワークアクセス（J-Quants API・RSS フィード・OpenAI API）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを取得）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発用）pip install -e . などプロジェクトのパッケージ化に応じて
4. 環境変数を設定
   - プロジェクトルートに .env ファイルを置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みは無効化されます）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime でも利用）
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env の例:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=CXXXXXXX

---

## 使い方（基本例）

以下は Python スクリプトやデバッガから呼び出す最小例です。共通して DuckDB の接続を渡します（settings.duckdb_path にデフォルトパスあり）。

- 初期準備（設定読み込み・接続）

    from datetime import date
    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行

    from kabusys.data.pipeline import run_daily_etl

    # target_date を省略すると今日を基準に処理します
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントを評価して ai_scores に書き込む

    from kabusys.ai.news_nlp import score_news
    from datetime import date

    # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {n_written}")

- 市場レジーム判定（regime を market_regime テーブルへ保存）

    from kabusys.ai.regime_detector import score_regime
    from datetime import date

    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ（監査DBの初期化）

    from kabusys.data.audit import init_audit_db

    audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリ自動作成
    # 監査テーブルが作成され、UTC 設定が適用されます

- 研究用ファクター計算の呼び出し例

    from kabusys.research.factor_research import calc_momentum
    from datetime import date

    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    # 結果は list[dict]（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）

注意点:
- OpenAI 呼び出し回数・レートに注意してください（API 利用に伴うコスト・制限があります）。
- ETL / API 呼び出しはネットワーク・外部APIに依存するため、エラーハンドリングが必要です（run_daily_etl は部分失敗時でも可能な処理を続けます）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト時など自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よく使う API / 関数一覧（参考）
- kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.duckdb_path
  - settings.env / settings.is_live / settings.is_paper / settings.is_dev
- kabusys.data.jquants_client
  - fetch_daily_quotes, save_daily_quotes
  - fetch_financial_statements, save_financial_statements
  - fetch_market_calendar, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.news_collector
  - fetch_rss(url, source)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_db(path)
  - init_audit_schema(conn, transactional=False)

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/  (監視用コード・DBアクセスなどが想定される場所)
- execution/   (発注/ブローカー連携用コードを配置する想定)
- strategy/    (戦略実装を置く想定)

---

## 開発上の注意 / 設計方針のポイント
- ルックアヘッドバイアス防止: 各モジュールは明示的な target_date を受け取り、date.today()/datetime.today() を直接参照しない実装方針が取られています（バックテストや再現性に重要）。
- 冪等性: ETL の保存処理は ON CONFLICT / DO UPDATE による冪等設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）の失敗時は部分的にフォールバック（スコア 0 化など）して処理を継続する設計が多く採用されています。
- セキュリティ考慮: RSS 収集では SSRF 対策、defusedxml の利用、受信サイズ制限などを実装。

---

## ライセンス / 貢献
（ここにライセンス情報・貢献方法を追記してください）

---

README はプロジェクトの導入・参照に必要な最低限の情報をまとめています。運用やデプロイ、テスト方法、より詳細な設計ドキュメント（StrategyModel.md / DataPlatform.md 等）が別途ある場合はそちらも参照してください。