KabuSys — 日本株自動売買プラットフォーム（README）
概要
- KabuSys は日本株向けのデータプラットフォーム／研究／AI スコアリング／監査ログ／ETL を含む自動売買支援ライブラリです。
- 主な目的は J-Quants など外部データソースから日次データを取得・保存し、News NLP / 市場レジーム判定 / ファクター計算 等を実行して戦略・発注層へ渡すための共通基盤を提供することです。
- パッケージ名: kabusys、現在のバージョンは __version__ = "0.1.0"。

主な機能
- data
  - J-Quants API クライアント（fetch/save の一通りのラッパ）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS パーシング、前処理、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損、スパイク、重複、将来日検出）
  - 監査ログ（signal_events / order_requests / executions のスキーマ初期化・DB 初期化）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース NLP スコアリング（score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込む）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- research
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索・統計（forward returns, IC, factor_summary, rank）
- config
  - .env/.env.local または環境変数から設定をロードする仕組み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
  - settings オブジェクトを経由して設定にアクセス（例: from kabusys.config import settings）

動作環境（推奨）
- Python 3.10 以上（Union 型記法 Path | None 等を使用）
- 必要主なライブラリ（プロジェクト依存に合わせてインストールしてください）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants, RSS ソース, OpenAI）が必要

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabu ステーション API のパスワード（本プロジェクトの一部で参照）
  - SLACK_BOT_TOKEN       : Slack 通知に使用するボットトークン
  - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
  - OPENAI_API_KEY        : OpenAI 呼び出しに使用（ai.score_news / ai.score_regime）
- 任意・デフォルトあり:
  - KABUSYS_ENV           : 実行環境 ("development" / "paper_trading" / "live")、デフォルト "development"
  - LOG_LEVEL             : ログレベル ("DEBUG","INFO",...)、デフォルト "INFO"
  - DUCKDB_PATH           : デフォルト data/kabusys.duckdb
  - SQLITE_PATH           : デフォルト data/monitoring.db
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を起点）にある .env と .env.local を自動で読み込みます（OS 環境変数 > .env.local > .env の優先順）。
  - 自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セットアップ手順（開発用の一例）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール（requirements.txt / pyproject.toml があればそちらを利用）
   - 例:
     - pip install duckdb openai defusedxml

   - 開発インストール（pyproject.toml がある場合）:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定します。
   - 例 .env（最小例、実運用では秘密を安全に管理してください）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB などの初期化（監査 DB を使う場合）
   - Python REPL やスクリプトで監査 DB を初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - デフォルトのプロジェクト DB パスは settings.duckdb_path（data/kabusys.duckdb）です。

基本的な使い方（コード例）
- 共通: DuckDB 接続を作成して各関数に渡す（関数は DuckDB 接続を引数に取る設計）
  - 例: ETL の実行
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  - ニューススコアリング（OpenAI API キーが必要）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20))
    print("書き込んだ銘柄数:", written)

  - 市場レジーム判定
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か引数で指定

  - 監査 DB 初期化（別 DB に分ける場合）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

- 研究用関数（例: モメンタム）
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026,3,20))
    # records: list of dict with keys date, code, mom_1m, mom_3m, mom_6m, ma200_dev

注意点・設計上の特徴
- Look-ahead バイアス防止:
  - 多くのモジュール（ai, research, data）は datetime.today() を直接参照しないか、target_date を明示的に受け取る設計です。バックテストや日次バッチで意図しない未来データ参照を防ぎます。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は gpt-4o-mini を想定した JSON モードの呼び出しを行います。API 呼び出しはリトライや失敗時のフォールバックが組み込まれています（失敗時はスコア = 0.0 等）。
- J-Quants クライアント:
  - rate limiter / retry / id_token 自動リフレッシュ / pagination に対応しています。
- DB 書き込みはできる限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- ニュース収集: SSRF、XML Bomb、過大サイズ対策（受信サイズ制限）などセキュリティ対策を組み込んでいます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP スコアリング
    - regime_detector.py                — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（fetch/save）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 他）
    - etl.py                            — ETL 公開インターフェース（ETLResult）
    - news_collector.py                 — RSS ニュース収集
    - quality.py                        — データ品質チェック
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py            — マーケットカレンダー管理
    - audit.py                          — 監査ログ（スキーマ初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py                — ファクター計算（momentum/value/volatility）
    - feature_exploration.py             — forward returns / IC / summary / rank
  - research/*（上記モジュール）
  - その他: monitoring / strategy / execution / etc.（パッケージエクスポートで参照可能）

よくある運用フロー（例）
1. 毎朝（バッチ）:
   - run_daily_etl を実行して calendar / prices / financials を更新し品質チェックを実行
2. ニュース収集:
   - RSS を定期実行し raw_news を蓄積
3. ニューススコアリング:
   - score_news を呼び出して ai_scores を更新
4. レジーム判定:
   - score_regime を呼び出して market_regime を更新（取引方針調整）
5. 研究:
   - research の関数でファクター評価を行い戦略へ反映
6. 監査ログ:
   - 発注フローでは order_requests / executions 等を用いてトレースを保持

ライセンス・貢献
- （ここにライセンス情報や貢献方法の案内を追加してください。）
- セキュリティや秘密情報（API トークン等）は .env を git 管理しないよう注意してください。

最後に
- 実行前に必要な API キーや .env の設定を確認してください。
- テスト時に自動 .env ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 追加の利用方法（発注実行、モニタリング、Slack 通知など）は各モジュールの docstring を参照してください。