KabuSys — 日本株自動売買プラットフォーム（README 日本語）

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買補助ライブラリです。
主な目的は以下です。
- J-Quants からの株価・財務・カレンダー等データの差分ETL
- ニュース収集・NLP（OpenAI）によるニュースセンチメント評価
- 市場レジーム判定（MA200 とマクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order → execution のトレーサビリティ）を DuckDB で管理
- データ品質チェック（欠損・スパイク・重複・日付整合性）

主な機能
--------
- data/jquants_client.py: J-Quants API からのデータ取得、DuckDB への冪等保存（save_*）
  - レートリミッタ、リトライ、トークン自動リフレッシュ対応
- data/pipeline.py: 日次 ETL（run_daily_etl）／個別 ETL ジョブ（run_prices_etl 等）
- data/news_collector.py: RSS フィード取得・前処理・raw_news への保存
  - SSRF・GZip・XML 脆弱性対策を実装
- data/quality.py: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- data/audit.py: 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- data/calendar_management.py: JPX カレンダー管理・営業日判定（is_trading_day, next_trading_day 等）
- data/stats.py: 汎用統計ユーティリティ（zscore_normalize）
- research/*: ファクター計算・特徴量解析（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等）
- ai/news_nlp.py: ニュース記事を銘柄ごとに集計し OpenAI でスコアリング（score_news）
- ai/regime_detector.py: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成し市場レジームを判定（score_regime）
- config.py: 環境変数／.env 読み込みと Settings（各種キーの必須チェック）

前提（依存パッケージ）
--------------------
この README はソースをベースにした推奨依存です（実際の requirements.txt がある場合はそちらを優先してください）。
- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外の軽微な追加がある場合があります）

環境変数（主なもの）
-------------------
アプリケーションは環境変数で設定を取得します。欠損するとエラーとなるものがあります。
必須（Settings._require を参照）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API パスワード（発注等を行う場合）
- SLACK_BOT_TOKEN       : Slack 通知に使用する BOT トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルトあり／挙動を変更するもの）:
- KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite 等のパス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

.env の自動読み込み
-------------------
パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、
OS 環境変数 > .env.local > .env の順で値を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セットアップ手順（開発向け）
--------------------------
1. Python をインストール（3.10 以降推奨）
2. リポジトリをクローン／チェックアウトし、プロジェクトルートに移動
3. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
4. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （別途 requirements.txt がある場合は pip install -r requirements.txt）
5. 環境変数を用意
   - .env を作成する（.env.example があれば参照）
   - 必須のトークン類（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN など）を設定
6. DuckDB 用ディレクトリを作る（settings.duckdb_path の親ディレクトリ）
   - mkdir -p data

使い方（コード例）
-----------------

- 設定取得と DuckDB 接続
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定することも可能
    print(result.to_dict())

- ニュースのスコアリング（OpenAI を使用）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key を渡すか環境変数 OPENAI_API_KEY を設定

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB の初期化
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- ファクター計算（研究用途）
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
    records = calc_momentum(conn, target_date=date(2026,3,20))

実装の注意点 / テスト向けポイント
---------------------------------
- OpenAI 呼び出し等の外部 API はユニットテストでモック可能に設計されています（モジュール内の _call_openai_api 等をパッチ）。
- ETL や保存処理は冪等性（ON CONFLICT DO UPDATE）を考慮しています。
- Look-ahead bias を防ぐため、各処理は target_date を明示的に受け取り、datetime.today() 等を直接参照しない設計になっています。
- news_collector は SSRF 回避・XML 脆弱性対策・レスポンスサイズ上限を実装しており安全性を考慮しています。

ディレクトリ構成（主要ファイル）
------------------------------
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
  - calendar_management.py
  - news_collector.py
  - stats.py
  - quality.py
  - audit.py
  - pipeline.py (ETLResult の定義など)
  - etl.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/  (パッケージ参照のみ; 実装はコードベースに応じて)
- strategy/    (戦略・発注層は別実装想定)
- execution/   (ブローカー連携は別実装想定)

付記
----
この README は提供されたソースコードに基づく概要と利用例です。実際に運用する際は以下を推奨します。
- 運用用キーを安全に管理する（Vault, Kubernetes Secrets 等）
- 本番環境（live）では発注・証券会社連携コードの十分なフェイルセーフを確認
- テストや CI でネットワーク依存部（OpenAI, J-Quants, RSS）をスタブ化

ライセンスや貢献方法についてはリポジトリのトップレベルファイル（LICENSE, CONTRIBUTING 等）を参照してください。