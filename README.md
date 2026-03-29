# KabuSys

日本株向けの自動売買 / データプラットフォーム（KabuSys）の軽量実装です。  
データ収集（J-Quants）、ETL、データ品質チェック、特徴量算出、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどの基盤機能を提供します。

概要・目的
- J-Quants API からの株価・財務・市場カレンダー取得を自動化して DuckDB に保存
- ニュースを収集して LLM（OpenAI）で銘柄センチメントを算出
- ファクター（モメンタム、バリュー、ボラティリティ等）計算と研究用ユーティリティ
- ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）機能

主な特徴（機能一覧）
- 環境変数管理（.env / .env.local を自動ロード、必要に応じて無効化可能）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ・ページネーション対応）
- ETL：日次差分取得（prices / financials / market_calendar）＋品質チェック
- ニュース収集（RSS）と前処理（URL除去・トラッキング削除・SSRF対策）
- ニュースNLP：OpenAI を用いた銘柄ごとのセンチメント算出（JSON mode でレスポンス検証）
- 市場レジーム判定：ETF（1321）200日移動平均乖離＋マクロニュースの LLM センチメントを合成
- リサーチ用ユーティリティ：ファクター計算（momentum / value / volatility）、forward return、IC、統計サマリー、Z スコア正規化
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査テーブル群（signal_events, order_requests, executions）と初期化ユーティリティ
- DuckDB を主要ストレージとして使用（軽量で SQL ベース、ETL/分析に適合）

要件
- Python 3.10+
- 必要なライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）で実装済み

インストール（例）
1. 仮想環境を作成・アクティベート
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. （開発）パッケージとしてインストール
   - pip install -e .

設定（環境変数）
- 本プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（config モジュール）。
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数例（.env）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  （必要に応じて）
- SLACK_BOT_TOKEN=your_slack_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb  （省略時のデフォルト）
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development | paper_trading | live
- LOG_LEVEL=INFO | DEBUG | WARNING | ERROR | CRITICAL

注意: トークン等の機密情報は Git にコミットしないでください。

セットアップ手順（簡易）
1. data ディレクトリを作成
   - mkdir -p data

2. 環境変数を .env に設定（上記参照）

3. DuckDB 接続作成（例コード）
   - import duckdb
   - conn = duckdb.connect(str(Path('data/kabusys.duckdb')))

4. 監査ログ用 DB 初期化（任意）
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db('data/audit.duckdb')

使い方（代表的な操作例）

- 日次 ETL 実行
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    conn = duckdb.connect('data/kabusys.duckdb')
    res = run_daily_etl(conn, target_date=date(2026,3,20))
    print(res.to_dict())

- ニュースセンチメント（1日分）を算出して ai_scores に保存
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect('data/kabusys.duckdb')
    n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を省略すると環境変数 OPENAI_API_KEY を使用

- 市場レジーム判定（1321 の MA200 とマクロニュース）
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    import duckdb
    conn = duckdb.connect('data/kabusys.duckdb')
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査スキーマ初期化（既存 DuckDB 接続に対して）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- 研究用ユーティリティの利用例
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
    results = calc_momentum(conn, target_date)
    normalized = zscore_normalize(results, ["mom_1m", "mom_3m", "mom_6m"])

実装上の注意（設計方針の要点）
- ルックアヘッドバイアス対策：内部実装で datetime.today() / date.today() を無秩序に参照せず、関数呼び出しに target_date を渡す設計
- API 呼び出しはリトライ・バックオフを備え、失敗時にはフェイルセーフ（ゼロスコア等）で継続
- ETL は差分更新・バックフィルを採用し後出し修正を吸収
- ニュース収集は SSRF 対策・XML 関連攻撃対策（defusedxml）・レスポンスサイズ制限を実装
- DuckDB への保存は冪等性を考慮（ON CONFLICT DO UPDATE 等）

よく使うモジュール一覧
- kabusys.config: 環境変数・設定管理（.env 自動読み込み）
- kabusys.data:
  - pipeline: ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - jquants_client: J-Quants REST クライアント（fetch_*, save_*）
  - news_collector: RSS 収集と前処理
  - quality: データ品質チェック
  - stats: 汎用統計（zscore_normalize）
  - audit: 監査テーブル初期化ユーティリティ
  - calendar_management: 営業日判定・カレンダー更新ジョブ
- kabusys.ai:
  - news_nlp.score_news: ニュースセンチメント算出
  - regime_detector.score_regime: 市場レジーム判定
- kabusys.research: ファクター計算・特徴量解析ユーティリティ

ディレクトリ構成（主要ファイル）
- src/kabusys/
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
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (※コードベースに参照あり、監視関連は別ファイル群を想定)
  - execution/ (発注/約定関連：実行層の実装を想定)
  - strategy/ (戦略実装層を想定)
- pyproject.toml / setup.cfg (プロジェクト設定、存在する場合)

（注）上記はリポジトリ内の主要モジュールを抜粋した構成です。実際のファイル・フォルダは開発途中で増減する可能性があります。

運用上の注意
- API トークン（J-Quants / OpenAI / Slack 等）は安全に保管してください。CI や本番環境ではシークレット管理サービスを利用してください。
- KABUSYS_ENV を "live" にすると本番向けの挙動（フラグ等）が有効になる想定です。paper_trading（検証）やdevelopment を使い分けてください。
- OpenAI 呼び出しは API 利用料が発生します。バッチ頻度やモデル選定に注意してください。

トラブルシューティング（簡易）
- 環境変数が読み込まれない場合:
  - プロジェクトルートに .env/.env.local があるか確認
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
- DuckDB ファイルの読み書き権限エラー:
  - data ディレクトリの作成と適切なアクセス権を確認
- J-Quants API エラー（401 等）:
  - JQUANTS_REFRESH_TOKEN の有効性を確認。get_id_token() は自動リフレッシュを試みます。

ライセンス・貢献
- 本リポジトリに LICENSE が含まれる場合はそれに従ってください。バグ修正や機能追加は Pull Request を受け付ける前提で設計されています。

---
何か特定の利用例（例: ETL の cron 設定、Slack 通知の組み込み、監査データのサンプルスキーマ）や README の補足（コマンド例、Docker 化手順など）が必要であれば教えてください。必要に応じて追加セクションを作成します。