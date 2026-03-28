KabuSys — 日本株自動売買プラットフォーム（README）
=====================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI 評価・監査テーブルを備えた自動売買システムのコアライブラリです。  
主に以下を提供します。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- ニュースの収集と LLM による銘柄センチメント評価（news_nlp）
- 市場レジーム判定（ETF + マクロニュース + LLM）（regime_detector）
- ファクター計算・特徴量探索（research パッケージ）
- データ品質チェック（quality）
- 監査ログ（signal → order → execution のトレーサビリティ）用の DuckDB スキーマ初期化
- カレンダー管理・営業日判定ユーティリティ

主要な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- API 呼び出しはリトライ・バックオフやフェイルセーフを考慮
- DuckDB を主要なローカルデータストアとして利用（冪等保存を前提）
- LLM 呼び出しは JSON mode を利用し、レスポンス検証を厳格化

機能一覧
--------
- data
  - ETL パイプライン: 日次 ETL（prices / financials / calendar）
  - J-Quants クライアント（取得・保存／ページネーション・レート制御・トークンリフレッシュ）
  - カレンダー管理（営業日判定、next/prev trading day、calendar 更新ジョブ）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
  - 質問: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
- ai
  - news_nlp.score_news: ニュースを銘柄単位で LLM に送りセンチメント（ai_scores）を書き込む
  - regime_detector.score_regime: ETF の MA 乖離とマクロニュース LLM 評価を合成して market_regime テーブルに書き込む
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、rank / zscore 正規化
- utils / config
  - 環境変数管理（.env/.env.local 自動ロード、必須チェック）
  - settings オブジェクト経由で設定取得（JQUANTS_REFRESH_TOKEN 等）

セットアップ手順
---------------
1. Python 環境作成（推奨: 3.10+）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例（最低限の依存）:
     - pip install duckdb openai defusedxml
   - 実運用ではさらに HTTP クライアントや Slack/DB 関連パッケージが必要になる可能性があります。

3. パッケージのインストール（開発モード）
   - プロジェクトルートに pyproject.toml / setup.cfg 等がある場合:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env（と任意で .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定が必要な環境変数（settings で必須とされているもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（使用するモジュールがある場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 送信先チャンネル
   - 推奨／任意:
     - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 呼び出しで省略時に参照）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   - .env 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方（簡単なコード例）
-----------------------

- DuckDB 接続を用意する
  - 例:
    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - 例:
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日が対象
    print(result.to_dict())

- ニュースセンチメントを生成して ai_scores に書き込む
  - 例:
    from kabusys.ai.news_nlp import score_news
    from datetime import date
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("書き込み銘柄数:", n_written)

  - score_news は OPENAI_API_KEY を環境変数か api_key 引数で受け取ります。失敗時は例外（キー未設定）または空スコアで継続します。

- 市場レジーム判定を実行する
  - 例:
    from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DB を作る）
  - 例:
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # 必要に応じてこの audit_conn を監査ログ操作に利用

- カレンダー・営業日ユーティリティ
  - 例:
    from kabusys.data.calendar_management import is_trading_day, next_trading_day
    from datetime import date
    is_trade = is_trading_day(conn, date(2026, 3, 20))
    nxt = next_trading_day(conn, date(2026, 3, 20))

注意点 / 運用上のポイント
- LLM 呼び出し（OpenAI）はレート・課金が関係するため、本番では API キー管理や呼び出し頻度に注意してください。
- J-Quants API にはレート制限があり、jquants_client モジュールで制御（120 req/min）・リトライが組み込まれています。
- ETL は差分更新を前提としており、backfill_days 等で後出し修正の吸収を行います。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、モジュール内でガードしています。
- ニュース収集は SSRF 対策・サイズチェック・XML 解析の安全策（defusedxml）を実装しています。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
  - パッケージエントリ（__version__ = "0.1.0"）

- config.py
  - 環境変数の読み込み / settings オブジェクト（.env 自動ロード・必須チェック等）

- ai/
  - __init__.py
  - news_nlp.py
    - news を集約して OpenAI に送信、ai_scores へ書き込み
    - calc_news_window / score_news / 内部の API 呼び出しとレスポンス検証
  - regime_detector.py
    - ETF(1321) の MA 乖離とマクロニュース LLM 評価を合成して market_regime に書き込み

- data/
  - __init__.py
  - calendar_management.py
    - market_calendar の管理、営業日判定、calendar_update_job
  - pipeline.py
    - ETL のメイン処理（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - ETLResult データクラス
  - etl.py
    - ETLResult の再エクスポート
  - jquants_client.py
    - J-Quants API クライアント（取得・保存・認証・ページネーション・レート制御）
  - news_collector.py
    - RSS 取得・前処理・ID 生成・SSRF 防止・raw_news 保存用ユーティリティ（fetch_rss 等）
  - stats.py
    - zscore_normalize（クロスセクション正規化）
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログスキーマ定義と初期化（signal_events, order_requests, executions）

- research/
  - __init__.py
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials を参照）
  - feature_exploration.py
    - calc_forward_returns / calc_ic / factor_summary / rank

補足（開発・テスト）
-------------------
- テストを書く際は、環境変数の自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- OpenAI 呼び出しやネットワーク I/O はモックしやすいように内部呼び出しをラップしています（ユニットテストでの patch が容易）。
- DuckDB をインメモリで利用したい場合、db_path に ":memory:" を指定して init_audit_db 等を呼べます。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0" です。
- ライセンス情報や配布設定はリポジトリのトップレベル（pyproject.toml / LICENSE）をご確認ください。

最終更新
--------
- 本 README はコードベースの実装（src/kabusys/*.py）に基づいて生成しています。実際の運用・拡張時は該当モジュールのドキュメント文字列やプロジェクトの上流ドキュメント（DataPlatform.md / StrategyModel.md 等）も参照してください。

もし README に追加したいサンプルコマンドや CI／デプロイ手順、あるいは具体的な .env.example を載せたい場合は教えてください。必要に応じて追記します。