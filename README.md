KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータプラットフォーム、リサーチ、AI支援のニュースセンチメント評価、監査ログ、ETL、マーケットカレンダー管理などを含む自動売買基盤ライブラリです。主に以下用途で使います。

- J-Quants API からのデータ取得・差分ETL（株価・財務・カレンダー）
- ニュース記事の取得・前処理・LLM による銘柄別センチメント算出
- 市場レジーム（bull / neutral / bear）判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB を中心としたローカル DB 保存（デフォルトパス data/kabusys.duckdb）

主な機能一覧
-------------
- 環境変数・設定管理（kabusys.config.Settings）
  - .env / .env.local 自動読み込み（プロジェクトルート判定）
  - 必須環境変数の明示・検証
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch / save の冪等化（ON CONFLICT DO UPDATE）
  - レート制限・リトライ・トークン自動リフレッシュ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、記事ID生成
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini, JSON mode）でセンチメント算出
  - バッチ処理、リトライ、レスポンス検証、ai_scores テーブルへ書き込み
- 市場レジーム検出（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成
  - market_regime テーブルへ冪等書き込み
- 研究モジュール（kabusys.research）
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- 監査ログ管理（kabusys.data.audit）
  - 監査テーブル定義 / 初期化（init_audit_schema / init_audit_db）
  - UUID ベースのトレーサビリティ設計

セットアップ手順
----------------

前提
- Python 3.10 以降（コード中の型ヒントで | 演算子を使用）
- ネットワークアクセス（J-Quants / OpenAI 等）を行う環境

1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 最低必要パッケージ例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt や pyproject.toml があればそれを使ってください）
   - 開発時は pip install -e . でローカルインストール（プロジェクトがパッケージ化されている場合）

4. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（kabusys.config が自動でロード）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨の .env（最小例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

1) DuckDB 接続の作成
- デフォルト DB パスは settings.duckdb_path（例: data/kabusys.duckdb）

例:
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

3) ニュースセンチメントを算出して ai_scores に書き込む
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  n = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込み銘柄数: {n}")

4) 市場レジームを算出して market_regime に書き込む
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key=None)

5) 監査ログ DB の初期化
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可

6) 研究（ファクター計算）の利用例
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # 結果は dict のリスト

環境変数一覧（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI) : OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注系）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知設定
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視設定
- KABUSYS_ENV : 実行環境 (development | paper_trading | live)
- LOG_LEVEL : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env 読み込みを無効化

自動 .env 読み込みの動作
- プロジェクトルートは .git または pyproject.toml を基準に自動検出します。
- 読み込み順序: OS 環境変数 > .env.local (上書き) > .env
- テスト等で自動読み込みを停止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（主要ファイル）
--------------------------------
（パッケージルート: src/kabusys）

- __init__.py
- config.py                          : 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                       : ニュースの LLM スコアリング（ai_scores へ保存）
  - regime_detector.py                : 市場レジーム判定（market_regime へ保存）
- data/
  - __init__.py
  - jquants_client.py                 : J-Quants API クライアント（fetch/save/トークン管理）
  - pipeline.py                       : ETL パイプライン（run_daily_etl 等）
  - etl.py                            : ETLResult の再エクスポート
  - news_collector.py                 : RSS 収集・前処理・保存ユーティリティ
  - calendar_management.py            : JPX カレンダー・営業日ユーティリティ
  - quality.py                        : データ品質チェック
  - stats.py                          : 共通統計ユーティリティ（zscore_normalize）
  - audit.py                          : 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py                : モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py            : 将来リターン・IC・統計サマリー等
- monitoring/ (パッケージ骨子: 監視処理があればここに)
- strategy/, execution/, monitoring/  （パッケージ公開名として __all__ に含まれるが実装は別途）

注意事項 / 設計上のポイント
----------------------------
- 全体方針として「ルックアヘッドバイアス防止」を重視しています：内部で datetime.today() / date.today() を安易に使わず、ETL/スコア関数は明示的な target_date を受け取る設計です。
- OpenAI 呼び出しはリトライ・JSON バリデーションを行い、API 失敗時にフェイルセーフ（スコア 0 やスキップ）するように設計されています。
- J-Quants API はレート制限（120 req/min）を守るための固定間隔レートリミッタを実装しています。
- DuckDB への保存は出来る限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行います。
- ニュース収集は SSRF 対策、受信サイズ制限、XML パースの安全ライブラリ（defusedxml）を使用しています。

テスト・開発
------------
- テスト時には環境変数自動ロードを無効にするか、モック（OpenAI / HTTP / J-Quants）を注入して実行してください。
- news_nlp や regime_detector の内部 API 呼び出しはテスト時に patch して差し替え可能な設計になっています（モジュール内の _call_openai_api をモックするなど）。

貢献
----
バグ報告や機能改善の提案は Pull Request または Issue を通じて受け付けます。コードスタイル / テスト方針に従って実装をお願いします。

免責
----
本 README はコードベースの解説を目的としています。実際の発注・運用は十分な検証とリスク管理の下で行ってください。本プロジェクトは教育・研究用途を想定しており、実運用での損失に対して責任を負いません。

必要であれば、README に「例となる .env.example」や「よくあるエラーと対処法」の追記、各モジュールの API リファレンス（関数シグネチャと戻り値の詳細）を追加できます。どちらを追加しますか？