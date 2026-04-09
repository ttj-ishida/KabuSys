KabuSys — 日本株自動売買／データ基盤ライブラリ
================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買支援モジュール群です。  
主に以下を提供します。

- J-Quants API からの株価・財務・カレンダー取得（差分ETL、保存、品質チェック）
- ニュース収集（RSS）と LLM によるニュースセンチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- ファクター計算・特徴量探索（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化
- 環境変数を中心とした設定管理

主なユースケースは「夜間の ETL バッチでデータを更新 → ニュース/レジーム/ファクターを評価 → シグナル生成 → 監査ログ／発注連携」といったパイプライン構築です。バックテスト用途のデータ整備やリサーチ用途にも最適化されています。

機能一覧
--------
- データ取得・保存
  - J-Quants API クライアント（fetch & save: 日足 / 財務 / 上場情報 / カレンダー）
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合チェック（quality.run_all_checks）
- ニュース処理 / NLP
  - RSS 収集（安全対策: SSRF 対応、トラッキング除去、XML 脆弱性対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - 市場マクロセンチメントを組み合わせた市場レジーム判定（regime_detector.score_regime）
- リサーチ / ファクター
  - momentum / volatility / value 等の定量ファクター計算（research パッケージ）
  - forward return / IC / 統計サマリ等の特徴量探索ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- 設定管理
  - settings（環境変数・.env の自動読み込み、必須キー取得ユーティリティ）

セットアップ手順
----------------
前提
- Python 3.10 以降（型注釈の union 型（|）や futures annotations を想定）
- pip が利用可能

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - 必須依存例（プロジェクトが配布される package metadata があればそれに従ってください）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   - 開発中に package として使う場合:
     - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を配置すると自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 代表的な環境変数（.env に設定する例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_station_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_FILL_MODE=instant   # instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development   # development|paper_trading|live
     - LOG_LEVEL=INFO

   - 注意: settings.jquants_refresh_token 等は必須アクセス時に ValueError を投げます。実行環境でキーを必ず設定してください。

使い方（簡単なコード例）
-----------------------

基本的なパターンは DuckDB 接続を作り、必要な API 関数を呼ぶことです。

1) DuckDB 接続を作る（設定のパスを利用）
   from kabusys.config import settings
   import duckdb
   conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

3) ニュースのセンチメントスコア付与（OpenAI APIキーが必要）
   from kabusys.ai.news_nlp import score_news
   from datetime import date
   written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す

4) 市場レジームの判定
   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   status = score_regime(conn, target_date=date(2026, 3, 20))
   # データベースの market_regime テーブルに結果が書き込まれます

5) 監査ログ（audit）スキーマを初期化する（独立DBでも可）
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可

6) 設定参照
   from kabusys.config import settings
   token = settings.jquants_refresh_token
   is_live = settings.is_live

挙動・設計上の注意点
-------------------
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を起点）を探索して .env/.env.local を読み込みます。
  - 読み込み順: OS環境変数 > .env.local > .env
  - OS 環境変数はデフォルトで保護され、.env の上書きは行いません。
  - 自動読み込みを止めたい場合 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Look-ahead Bias 対策:
  - ニュースウィンドウや MA 計算等、内部処理は target_date 未満のデータのみ参照するよう設計されています（datetime.today()/date.today() を直接参照しない方針）。
  - ETL や分析処理をバックテストに使う場合は、適切に過去データだけを用いる等の注意が必要です。

- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini を使う設計です。API レスポンスが期待通りでない場合はフェイルセーフ（スコア=0.0 やスキップ）します。
  - テスト容易性のため API 呼び出し部分は差し替え可能（モック）に実装されています。

- J-Quants クライアント:
  - レート制限（120 req/min）やトークン自動リフレッシュ、リトライ（指数バックオフ）を実装しています。
  - fetch_* と save_* の組合せで差分 ETL を行う想定です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py               — パッケージ初期化（version 等）
- config.py                 — 環境変数/.env 読み込みと settings オブジェクト
- ai/
  - __init__.py             — ai API 再エクスポート
  - news_nlp.py             — ニュース NLP（score_news）
  - regime_detector.py      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py             — ETL パイプライン（run_daily_etl etc.）
  - etl.py                  — ETL 結果クラス再公開（ETLResult）
  - news_collector.py       — RSS 収集（SSRF 対策・正規化）
  - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - quality.py              — データ品質チェック
  - audit.py                — 監査ログテーブル定義と初期化
- research/
  - __init__.py             — 再エクスポート（factor 等）
  - factor_research.py      — ファクター計算（momentum/value/volatility）
  - feature_exploration.py  — forward returns / IC / summary / rank
- research/...              — 研究用ユーティリティ群

（プロジェクトルートには pyproject.toml / .git / .env のようなファイルがある想定）

開発・貢献
--------
- コードはモジュールごとにロギングと例外ハンドリングを行っています。ユニットテストや統合テスト時は外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックすることを推奨します。
- .env.example があれば参照して必要な環境変数を用意してください。

参考（短い例）
--------------
- ETL を毎朝 cron で実行する例（疑似コード）:
  - python -c "from kabusys.config import settings; import duckdb; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect(str(settings.duckdb_path)); run_daily_etl(conn)"

ライセンスや追加ドキュメント
-------------------------
- この README はコードベースから抽出した機能説明と利用手順の概要です。実運用前に各モジュールの詳細（リトライ挙動、DB スキーマ、環境変数の完全リスト、.env.example、運用 runbook）を参照・整備してください。

---
不明点や README に追記したいサンプル（.env.example、起動スクリプト例、CI 設定等）があれば教えてください。追加して翻訳・整備します。