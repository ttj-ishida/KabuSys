KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株のデータ取得（J-Quants）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、リサーチ（ファクター計算・特徴量解析）、ETL や市場カレンダー管理、監査ログ（発注〜約定のトレース）などを含むバックエンドライブラリ群です。DuckDB をデータレイクとして利用し、OpenAI（gpt-4o-mini）を使ったニュース解析／市場レジーム判定を行う設計になっています。

主な特徴
- ETL パイプライン（J-Quants から日次株価／財務／カレンダーを差分取得・保存）
- ニュース収集（RSS → raw_news に保存）とニュース NLP（銘柄別センチメント算出）
- 市場レジーム判定（1321 ETF の MA200 乖離 + マクロニュース LLM センチメントの合成）
- 研究用ユーティリティ（モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン、IC、統計サマリー、Z スコア正規化）
- データ品質チェックモジュール（欠損・スパイク・重複・日付不整合）
- 市場カレンダー管理（JPX カレンダーの取得・営業日判定）
- 監査ログ（signal → order_request → execution のトレーサビリティ、DuckDB にスキーマを初期化する関数あり）
- 自動 .env 読み込み（プロジェクトルートの .env / .env.local を優先順に読み込み。無効化フラグあり）

セットアップ手順（開発環境想定）
前提
- Python 3.10+（typing の union 型アノテーション等を使用しているため 3.10 以上を推奨）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1) リポジトリをクローン
    git clone <repo-url>
    cd <repo>

2) 仮想環境作成（任意）
    python -m venv .venv
    source .venv/bin/activate  # macOS / Linux
    .venv\Scripts\activate     # Windows (PowerShell でなければ)

3) 依存パッケージのインストール
requirements.txt がない場合は次の最低依存をインストールしてください：
    pip install duckdb openai defusedxml

プロジェクト用途によって他のパッケージ（例: requests 等）を追加してください。

4) 環境変数設定（.env）
プロジェクトルートに .env を作成するか、環境変数を設定します。主要なキー：
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         — OpenAI API キー（score_news / regime 判定で使用）
- KABU_API_PASSWORD      — kabuステーション API パスワード（発注等で使用）
- KABU_API_BASE_URL      — kabuステーション API のベース URL（オプション、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須な箇所があれば）
- SLACK_CHANNEL_ID       — Slack チャンネル ID（必須な箇所があれば）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — 監視等で使う SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV            — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL              — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env 読み込みはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込み）。無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要 API と実行例）
※ すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...)）を受け取る設計です。

1) DuckDB 接続の作成例
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL を実行する
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    res = run_daily_etl(conn, target_date=date(2026, 3, 20), id_token=None)
    print(res.to_dict())

3) ニュースのセンチメントスコア算出（前日15:00–当日08:30 JST ウィンドウ）
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None→ENV の OPENAI_API_KEY を参照

戻り値は書き込んだ銘柄数（int）。エラー時は例外または 0 を返す場合があります（API エラーはフェイルセーフでスキップ）。

4) 市場レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OpenAI キーは env を利用可

結果は market_regime テーブルへ冪等的に保存されます。

5) 監査ログスキーマの初期化
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit_duckdb.db")
    # または既存 conn に対してテーブルを追加:
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

6) 設定値の取得（Settings）
    from kabusys.config import settings
    print(settings.jquants_refresh_token)
    print(settings.duckdb_path)

自動的に .env/.env.local や OS 環境変数から値を読み込みます。必須キーが未設定の場合は ValueError を投げます。

環境変数と挙動のポイント
- 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml のあるパス）を基準に .env / .env.local を読み込む。優先順は OS 環境 > .env.local > .env。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化可能。
- settings.env は development / paper_trading / live のいずれかのみ許容。
- OpenAI、J-Quants の API はキー未設定時に ValueError を発生させます（呼び出し側で捕捉してください）。

ディレクトリ構成（主要ファイルと説明）
src/kabusys/
- __init__.py                      — パッケージ定義、__version__ 等
- config.py                        — 環境変数・設定管理（Settings クラス）
- ai/
  - __init__.py                    — ai パッケージ公開 API（score_news を公開）
  - news_nlp.py                    — ニュースの LLM スコアリング（score_news）
  - regime_detector.py             — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py         — 市場カレンダー管理（営業日判定 / 更新ジョブ）
  - etl.py                         — ETL の公開インターフェース（ETLResult 再エクスポート）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - stats.py                       — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py                     — データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py                       — 監査ログスキーマ定義 & 初期化
  - jquants_client.py              — J-Quants API クライアント（取得・保存関数）
  - news_collector.py              — RSS 収集・正規化・保存ロジック
- research/
  - __init__.py
  - factor_research.py             — モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py         — 将来リターン計算、IC、統計サマリー、ランク関数
- research から data.stats 等のユーティリティを利用する設計になっています。

実運用上の注意点（設計方針からの留意点）
- ルックアヘッドバイアス回避: 日付・ウィンドウ計算は明示的な target_date を基準に行い、date.today() 等を内部で参照しない実装が原則です（テスト・バックテストで重要）。
- フェイルセーフ: LLM 呼び出しや外部 API エラー時は可能な限りフェイルセーフ（部分スキップやデフォルト値）で継続するように実装されています。ただし、致命的な DB 書き込みエラーなどは例外が上がります。
- 冪等性: ETL 保存や監査スキーマの初期化等は冪等であることを意図しています（ON CONFLICT / トランザクション処理）。
- セキュリティ: news_collector は SSRF 対策、XML パーサの安全化（defusedxml）、受信サイズ制限などを行っています。

推奨ワークフロー（例）
1. .env を準備して必要な API キーを設定
2. DuckDB を初期化（必要に応じてデータベースファイルを作成）
3. run_daily_etl をスケジュール（cron / Airflow / 任意バッチ）で起動
4. ETL 後に score_news → score_regime → 研究・戦略評価の順で処理
5. シグナル〜発注〜約定は監査テーブルでトレースを残す

ライセンス・貢献
- このリポジトリに付与されているライセンス情報がある場合はプロジェクトルートの LICENSE を参照してください。
- バグ修正や機能追加は PR でお願いします。テストや型チェック（mypy など）を併せて追加いただけると助かります。

付録：よく使う関数（リファレンス）
- ETL / pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
- News NLP / ai.news_nlp.score_news(conn, target_date, api_key=None)
- Regime / ai.regime_detector.score_regime(conn, target_date, api_key=None)
- Audit init / data.audit.init_audit_db(path) / data.audit.init_audit_schema(conn)
- Calendar update / data.calendar_management.calendar_update_job(conn, lookahead_days=90)

不明点や README に追加してほしいサンプル（実行スクリプト、requirements ファイル、.env.example など）があれば教えてください。README に追記して提供します。