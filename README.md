KabuSys — 日本株自動売買基盤（README）
====================================

概要
----
KabuSys は日本株のデータ取得・品質管理・ファクター研究・AI によるニュースセンチメント評価・市場レジーム判定・監査ログ管理を含む自動売買プラットフォームのコアライブラリです。  
主に以下用途を想定しています。

- J-Quants からの市場データ ETL（株価、財務、マーケットカレンダー）
- ニュース収集と OpenAI を用いた銘柄別センチメントスコア生成
- ETF ベースの長期トレンドとマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注／約定に関する監査ログ（監査テーブルの初期化・管理）
- 冪等性、ルックアヘッドバイアス防止、堅牢なリトライ・レート制御等の設計方針を重視

主な機能一覧
--------------
- ETL（kabusys.data.pipeline）
  - run_daily_etl: 日次パイプライン（カレンダー→株価→財務→品質チェック）
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants API クライアント（kabusys.data.jquants_client）
  - トークン管理・リトライ・レート制御・ページネーション対応
  - raw_prices / raw_financials / market_calendar への冪等保存
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news 保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いた銘柄別センチメントスコア算出（JSON Mode、バッチ処理、リトライ）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離 + マクロセンチメント（LLM）で日次判定
- 研究・ファクター（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付整合性チェック（QualityIssue のリストで返す）
- 監査ログ（kabusys.data.audit）
  - 監査テーブル DDL / インデックス、init_audit_db / init_audit_schema による初期化

設計上の注意点（抜粋）
---------------------
- Look-ahead bias（未来情報参照）を避ける設計：target_date ベースの処理、datetime.today() の過度利用回避
- API 安定性確保：リトライ（指数バックオフ）、429/5xx 対応、トークン自動リフレッシュ
- 冪等性：DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を利用
- セキュリティ：RSS 収集での SSRF 対策、defusedxml を用いた XML パース
- テスト容易性：OpenAI 呼び出しなどはモック差し替えを想定した設計

セットアップ手順
----------------
1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（最低限の例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を使って管理してください。

3. リポジトリをインストール（開発モード）
   - pip install -e .

4. 環境変数（.env）を準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API のパスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知に利用する場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - その他: PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL / KABUSYS_ENV

   例 .env（抜粋）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb

使い方（簡単なサンプル）
-----------------------

- DuckDB 接続を開いて日次 ETL を実行する
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースのセンチメントスコアを取得して DB に書き込む
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> OPENAI_API_KEY を利用
    print(f"scored {count} codes")

- 市場レジーム判定を実行する
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数で

- 監査用 DB の初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

注意点・運用上のヒント
--------------------
- OpenAI 呼び出しは料金がかかります。API キーの管理・コスト制御に注意してください。
- J-Quants API はレート制限があるため、同時多重実行・スケジューラ運用時は間隔を調整してください。
- ETL や AI スコアリング関数には例外や API 障害に対するフォールバックが組み込まれていますが、ログ監視やアラートは必須です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DuckDB のバージョン差分により executemany の空リスト渡し等で挙動差が出るため、ライブラリ内で互換性対応をしています。運用時は DuckDB の既知バージョンで検証してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         (環境変数 / 設定)
- ai/
  - __init__.py
  - news_nlp.py                     (銘柄別ニュースセンチメント)
  - regime_detector.py              (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py               (J-Quants API クライアント + 保存処理)
  - pipeline.py                     (ETL パイプライン)
  - etl.py                          (ETL インターフェース再エクスポート)
  - news_collector.py               (RSS ニュース収集)
  - quality.py                      (データ品質チェック)
  - stats.py                        (統計ユーティリティ)
  - calendar_management.py          (マーケットカレンダー管理)
  - audit.py                        (監査ログ DDL / 初期化)
- research/
  - __init__.py
  - factor_research.py              (モメンタム / バリュー / ボラティリティ)
  - feature_exploration.py          (IC / 将来リターン / 統計要約)

ライセンス / 貢献
-----------------
この README はコードの構造と利用方法を簡潔に示す目的です。実際の運用では、それぞれのモジュールに対するユニットテスト、運用監視、バックアップ方針、アクセス制御等を整備してください。貢献や問題報告はリポジトリの PR / Issues を利用してください。

付録: 主要な環境変数（まとめ）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- OPENAI_API_KEY — OpenAI API キー（AI機能用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_ENV — environment（development / paper_trading / live）

以上。README の内容やサンプルをプロジェクトの運用方針に合わせて適宜調整してください。必要ならば各モジュールの API サンプルや .env.example を追記します。