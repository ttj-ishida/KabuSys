# KabuSys — 日本株自動売買プラットフォーム（README 日本語）

概要
- KabuSys は日本株向けのデータプラットフォームおよび自動売買支援ライブラリ群です。
- 主な役割はデータ ETL（J-Quants からの株価 / 財務 / カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算・研究ユーティリティ、監査ログ（発注〜約定トレーサビリティ）などです。
- 設計方針として「ルックアヘッドバイアスの排除」「冪等性」「エラー時のフェイルセーフ」「DuckDB を中心とした SQL ベース処理」を重視しています。

主な機能
- データ収集（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場情報、JPX カレンダー取得（pagination・自動リトライ・レート制限対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次 ETL（カレンダー→株価→財務→品質チェック）
  - 差分取得／バックフィル／品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS からニュース取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF 対策、サイズ制限、トラッキングパラメータ除去等の安全対策
- AI（OpenAI）連携
  - ニュースの銘柄別センチメントスコアリング（gpt-4o-mini, JSON mode）
  - マクロニュースと ETF の MA を組み合わせた市場レジーム（bull/neutral/bear）判定
  - リトライ・レスポンスバリデーション・クリップなど堅牢な実装
- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル DDL と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止
- ユーティリティ
  - マーケットカレンダーの判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - データ品質チェック集合（run_all_checks）

必要条件（推奨）
- Python >= 3.10（型アノテーションで | 記法等を使用）
- DuckDB（Python パッケージ）
- OpenAI Python クライアント（AI 機能を使う場合）
- defusedxml（ニュース RSS パースの安全対策）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

インストール（ローカル開発向け）
1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - ない場合、概ね次のパッケージを入れてください:
     - pip install duckdb openai defusedxml

3. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

環境変数（必須 / 任意）
- 必須（実行する機能により必要なもの）
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
  - SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を使う場合）
  - SLACK_CHANNEL_ID: Slack チャンネル ID
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- 任意
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
  - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト development）
  - LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")
- .env 自動読み込み
  - プロジェクトルートに .env/.env.local があれば自動で読み込みます（OS 環境変数が優先）。
  - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順（例）
1. .env 作成
   - プロジェクトに .env.example がある想定です。.env を作成して上記環境変数を設定してください。
2. DuckDB ファイル初期化（必要に応じて）
   - Python REPL やスクリプトで監査 DB を初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
3. ETL 初回実行
   - Python スクリプトで日次 ETL を実行（J-Quants トークンが必要）:
     from datetime import date
     import duckdb
     from kabusys.data.pipeline import run_daily_etl
     conn = duckdb.connect(str(requirements := "data/kabusys.duckdb"))  # 例
     res = run_daily_etl(conn, target_date=date(2026, 3, 20))
     print(res.to_dict())

使い方（主要 API 例）

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュース NLP スコアリング（OpenAI 必須）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"scored {n_written} codes")

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを組み合わせる）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究用ファクター計算
  - 例（モメンタム）:
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026,3,20))
    # records は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]

- 監査テーブル初期化
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events/order_requests/executions 等のテーブルが作成されます

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py         — マクロ + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - news_collector.py          — RSS ニュース収集
    - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Value / Volatility 等
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー 等

注意事項 / 運用メモ
- OpenAI を使用する機能（news_nlp, regime_detector）は API キーが必要です。キー未設定時は ValueError を送出します。
- J-Quants API を使用する ETL はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必須です。
- DuckDB へ書き込む処理は内部でトランザクションを使う箇所があります。エラー時は適切にロールバックされる設計ですが、運用ではバックアップを推奨します。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基準に行われます。テスト環境で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ニュース RSS の取得には外部 HTTP アクセスが必要です。SSRF 対策やレスポンスサイズ制限が入っていますが、運用時のアクセス制御は別途検討してください。
- 本ライブラリは「データ処理・研究・監査ログ」の提供が主目的であり、実際の売買発注フロー（kabu API 連携部分）は設定に応じて実装・拡張してください。

フィードバック / 貢献
- バグ報告・機能追加は issue / pull request で受け付けてください（リポジトリルールに従ってください）。

以上。必要であれば README に追記するサンプルスクリプトや環境変数雛形（.env.example）を作成します。どの例を追加しますか？