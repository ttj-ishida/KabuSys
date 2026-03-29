KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ群（データプラットフォーム・リサーチ・AI・監査ログ・ETL 等）です。  
このリポジトリは、J-Quants / kabuステーション / OpenAI 等と連携して、データ収集（ETL）→ 品質チェック → 特徴量計算 → AI によるニュース評価 → 市場レジーム判定 → 戦略/発注の監査ログまでをカバーするコンポーネント群を提供します。

概要
----
- 設計方針のキーポイント
  - ルックアヘッドバイアス対策：内部処理で date.today()/datetime.today() を不用意に参照しない設計
  - 冪等性：DuckDB への保存は ON CONFLICT（UPSERT）を多用し再実行耐性を確保
  - フェイルセーフ：外部API失敗時は例外で即中断せず、許容可能なフォールバック（例: LLM 失敗時 macro_sentiment=0）を採用
  - セキュリティ：RSS収集でのSSRF対策、defusedxml の利用等、安全性に配慮
  - レート制御：J-Quants API 用に固定間隔の RateLimiter を実装

主な機能一覧
-------------
- データ収集 / ETL
  - J-Quants から株価日足、財務、上場情報、JPXカレンダーを差分取得（jquants_client）
  - ETLパイプライン実装（pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（data.quality）：欠損、重複、スパイク、日付不整合を検出
- ニュース収集
  - RSS 取得・前処理・raw_news への冪等保存（news_collector）
  - URL 正規化、トラッキングパラメータ除去、SSRF対策、gzip サイズ検査 等
- AI（LLM）連携
  - ニュースセンチメントの銘柄別スコアリング（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA200乖離から市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI の JSON Mode を用いた堅牢なレスポンスバリデーション・リトライ戦略
- 研究用ユーティリティ
  - ファクター計算（research.factor_research: momentum / value / volatility）
  - 特徴量探索（research.feature_exploration: forward returns, IC, summary, rank）
  - 統計ユーティリティ（data.stats: zscore_normalize）
- 監査ログ（オーダー・シグナルのトレーサビリティ）
  - 監査テーブルのDDLと初期化ユーティリティ（data.audit.init_audit_schema / init_audit_db）
  - signal_events, order_requests, executions 等の構造設計（冪等キー・ステータス遷移）
- 設定管理
  - 環境変数 / .env 自動読み込み（config.Settings）および必須キーの検査

セットアップ手順
----------------
以下は一般的なセットアップ例です。環境や依存パッケージはプロジェクトごとに調整してください。

1. Python 環境
   - Python 3.10+ を推奨（typing の union 表記や型ヒントを多用）
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 最低限必要になる想定パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 開発中は pip install -e . でパッケージを編集可能モードでインストール

3. 環境変数 / .env
   - プロジェクトルートに .env を作成すると、自動的に読み込まれます（config モジュールによる自動ロード）
   - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例: .env に記載するキー）
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須) — 通知用 Slack Bot トークン
     - SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネルID
     - DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト data/monitoring.db)
     - KABUSYS_ENV (任意, 値: development|paper_trading|live, デフォルト development)
     - LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト INFO)
     - OPENAI_API_KEY (AI機能を使う場合に必要)

   - 例 (.env)
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

使い方（簡単なコード例）
------------------------

- DuckDB 接続の用意（デフォルトのファイルパスは settings.duckdb_path）
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    res = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(res.to_dict())

- ニュースの銘柄別センチメントを算出して ai_scores に保存
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 市場レジームを判定して market_regime に書き込む
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- ファクター計算 / 研究ユーティリティ
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns
    m = calc_momentum(conn, target_date=date(2026,3,20))
    v = calc_value(conn, target_date=date(2026,3,20))
    vol = calc_volatility(conn, target_date=date(2026,3,20))
    fwd = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])

- 監査データベース初期化（監査ログ専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

- J-Quants から直接データを取得する（低レベルAPI）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    idt = get_id_token()  # settings.jquants_refresh_token を使用
    records = fetch_daily_quotes(id_token=idt, date_from=date(2026,1,1), date_to=date(2026,3,20))

運用時の注意点 / 実装上のポイント
--------------------------------
- 自動環境変数読み込み
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LLM 呼び出し
  - OpenAI JSON Mode を利用し、レスポンスは厳密な JSON を期待します。レスポンスパース失敗時はフォールバック（0.0）で継続します。
- API レート制御 & リトライ
  - J-Quants 用に固定インターバルの RateLimiter を実装（120 req/min 想定）。HTTP 408/429/5xx 等は指数バックオフで再試行します。401 はトークン自動リフレッシュを行います。
- セキュリティ
  - RSS 収集では URL 正規化・トラッキング除去、受信サイズ制限、リダイレクト先のプライベートアドレス検査等を実装しています。
- ルックアヘッドバイアス回避
  - 研究・AIモジュールは、対象日より未来のデータを参照しない実装になっています。バックテストには注意を払ってください。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント算出（OpenAI連携）
    - regime_detector.py            — ETF MA200 と マクロセンチメントから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の公開
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - audit.py                      — 監査ログ（DDL、初期化）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility の計算
    - feature_exploration.py        — forward returns / IC / summary / rank

テスト / 開発
--------------
- 各種外部API呼び出し（OpenAI / J-Quants / RSS の HTTP）はモック化してユニットテストを作成してください。
- ai モジュールの _call_openai_api はテストのために patch 可能（ファイル内で分離実装）。
- .env の自動ロードを無効にして環境依存性を排除するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用。

ライセンス / 貢献
-----------------
- （このリポジトリのライセンス／貢献規約をここに記載してください）

最後に
------
この README はコードベースの主要な機能と使い方を簡潔にまとめたものです。詳細な設計資料（DataPlatform.md / StrategyModel.md 等）や運用手順書がある場合はそちらも併せて参照してください。必要であればサンプル .env.example、requirements.txt、簡単な CLI スクリプト例などの追加ドキュメントを作成します。必要な出力や追記事項を教えてください。