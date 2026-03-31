KabuSys — 日本株自動売買プラットフォーム
概要
このリポジトリは日本株のデータ収集（ETL）・品質チェック・特徴量生成・ニュース/NLP スコアリング・市場レジーム判定・監査ログ管理を含む、バックテスト／自動売買基盤のコアモジュール群です。モジュールは DuckDB を主なローカルデータストアとして想定し、J-Quants や RSS、OpenAI（LLM）など外部 API と連携してデータを取得・処理します。

主な目的
- 日次 ETL（株価・財務・市場カレンダー）の差分取得と保存
- ニュースの収集と LLM による銘柄センチメント算出（ai_score）
- 市場レジーム（bull/neutral/bear）の判定（ETF + マクロニュース）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索補助
- 監査ログ（シグナル→発注→約定）のスキーマ定義と初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

機能一覧
- 環境設定管理: 自動で .env / .env.local をプロジェクトルートから読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。必須環境変数をラップした settings オブジェクトを提供。
- ETL（kabusys.data.pipeline）:
  - run_daily_etl：日次 ETL（市場カレンダー、株価、財務、品質チェック）
  - 個別 ETL：run_prices_etl, run_financials_etl, run_calendar_etl
  - ETL 結果を ETLResult にまとめる
- J-Quants クライアント（kabusys.data.jquants_client）:
  - fetch / save の実装（ページネーション、レートリミット、リトライ、トークン自動更新）
  - save_* は DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）:
  - RSS 取得（SSRF 対策・サイズ制限・URL 正規化・ID 生成）
  - raw_news / news_symbols への冪等保存を想定
- データ品質（kabusys.data.quality）:
  - 欠損チェック、スパイク、重複、日付整合性など
- 統計ユーティリティ（kabusys.data.stats）:
  - zscore_normalize（クロスセクション Z 正規化）
- 研究用モジュール（kabusys.research）:
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索・IC 等）
- AI（kabusys.ai）:
  - score_news：ニュースを LLM に投げて銘柄ごとのセンチメントを生成し ai_scores に保存
  - score_regime（regime_detector）：ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して market_regime に書き込み
  - OpenAI 呼び出しには retry/バックオフや JSON モード対応が組み込まれている
- 監査ログ（kabusys.data.audit）:
  - init_audit_schema / init_audit_db：signal_events, order_requests, executions を含む監査テーブルを初期化
  - 監査スキーマは冪等で作成、UTC タイムゾーンを固定

前提（推奨環境）
- Python 3.10 以上（代替構文（X | Y）や typing の利用のため）
- ローカル DB: DuckDB（Python パッケージ）
- 外部依存: openai（OpenAI SDK）、defusedxml（RSS 安全パース）
- ネットワーク経路で J-Quants・OpenAI へアクセス可能であること

セットアップ手順
1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository-root>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -e .
     （プロジェクトルートに setup.cfg / pyproject がある場合は editable install）
   - または明示的に:
     pip install duckdb openai defusedxml

   補足: 要件ファイルがある場合は pip install -r requirements.txt を利用してください。

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（および .env.local）を置くことで自動ロードされます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   例: .env（最低限必要なキー）
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

   - config.Settings は上記キーを必須／任意でラップしています。足りない場合は ValueError が発生します。

5. データディレクトリの作成（必要なら）
   - mkdir -p data

使い方（よく使う API の例）
- DuckDB 接続の作り方
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する（Python）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアを取得して ai_scores に書き込む
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

  注意: score_news は OPENAI_API_KEY 環境変数または api_key 引数を必要とします。

- 市場レジームスコアを計算して保存
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB を初期化する（監査用別 DB）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査ログを操作できます

- ファクター計算（研究用）
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

注意点 / 運用上のヒント
- Look-ahead バイアス防止: 多くの関数は内部で datetime.today() を直接参照せず、外部から target_date を渡す設計です。バックテストでは必ず過去の情報のみを用いるよう target_date を指定してください。
- OpenAI / J-Quants の呼び出しはリトライやバックオフが組み込まれていますが、API 利用料金とレート制限に注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テスト時に自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany の挙動（バージョン依存）に注意している箇所があります。空のバルク引数などを送らない設計になっています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     - 環境変数/設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                  - ニュース NLU / スコアリング
    - regime_detector.py           - 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（fetch/save）
    - pipeline.py                  - ETL パイプライン（run_daily_etl など）
    - etl.py                       - ETLResult 再エクスポート
    - news_collector.py            - RSS 収集（SSRF 対策等）
    - quality.py                   - データ品質チェック
    - stats.py                     - 統計ユーティリティ（zscore 正規化等）
    - calendar_management.py       - マーケットカレンダー管理
    - audit.py                      - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           - ファクター計算（momentum/value/vol）
    - feature_exploration.py       - 将来リターン・IC・統計サマリー等
  - monitoring/ (想定: 監視・プロセスマネジメント系のモジュール)
  - strategy/  (想定: 戦略定義やシグナル生成)
  - execution/ (想定: 発注/ブローカー接続)
  - ai/ その他の補助モジュールや拡張

よくある質問（FAQ）
- Q: OpenAI キーはどこに入れればよいですか？
  A: 環境変数 OPENAI_API_KEY に設定するか、score_news / score_regime に api_key 引数で渡してください。

- Q: .env の読み込み順は？
  A: OS 環境変数 > .env.local > .env の順で読み込みます。OS 環境変数は上書きされません（保護）。

- Q: 自動ロードを無効にできますか？
  A: はい。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを行いません（テスト時に有用）。

- Q: DuckDB のスキーマはどこにありますか？
  A: 本リポジトリでは save_* / init_audit_schema のような関数でテーブルを作成・更新する想定です。運用時は初期化用スクリプトを作成して実行してください。

貢献
- バグ修正・改善提案はプルリクエストで歓迎します。設計思想（Look-ahead バイアス回避、冪等性、API リトライ方針）を尊重して実装してください。

ライセンス
- このリポジトリのライセンス情報はルートの LICENSE ファイルを参照してください（ない場合はリポジトリ管理者に確認してください）。

以上。セットアップやサンプルコードについてさらに具体的な説明（例: 実際の .env.example 内容、スキーマ初期化スクリプト、CI 用のコマンド等）が必要であれば教えてください。