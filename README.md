# KabuSys

日本株向けのデータプラットフォームおよび自動売買（研究→シグナル→発注）を支援するライブラリ群です。  
ETL（J-Quants）→データ品質チェック→ファクター計算→AIによるニュース解析→市場レジーム判定→監査ログ整備まで、バックテスト／運用に必要な共通機能を提供します。

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート基準、.env / .env.local）
  - 必須環境変数の明示的チェック

- データ ETL（J-Quants）
  - 日次株価（OHLCV）取得・保存（ページネーション対応、レートリミット遵守、リトライ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集／NLP（OpenAI）
  - RSS 収集（SSRF対策、トラッキング削除、前処理）
  - 銘柄ごとニュース集約 → OpenAI（gpt-4o-mini）でセンチメント算出（ai_scores テーブルへ）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）

- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクタ―サマリ
  - Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - シグナル→発注要求→約定までの監査テーブル定義・初期化ユーティリティ
  - 冪等性やインデックス設計済み

---

## セットアップ手順

1. リポジトリをクローン／パッケージを配置

2. Python 環境の準備（例: venv）
   - Python 3.10+ を推奨

3. 依存ライブラリ（概略）
   - duckdb
   - openai
   - defusedxml
   - （その他 urllib / 標準ライブラリ中心）
   - 例（pip）:
     pip install duckdb openai defusedxml

4. 環境変数 (.env) の用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主に必要な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL     : kabu API のベース URL（任意, デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite path（監視用デフォルト）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視設定
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL             : DEBUG/INFO/...（デフォルト INFO）
   - OPENAI_API_KEY        : OpenAI を使う機能で参照されます（score_news, score_regime 等）

5. データベース初期化（監査ログなど）
   - 監査DBを初期化して接続する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な例）

- 設定取得
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env)

- 日次 ETL 実行（J-Quants 取得→保存→品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント算出（OpenAI 必須）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が環境に必要
  print(f"scored {n} codes")

- 市場レジーム判定（MA とマクロニュース合成）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  r = score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success

- 研究関連（ファクター計算）
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))

- 監査スキーマ初期化（既存接続に対して）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

注意:
- OpenAI を使う関数は api_key 引数を受け取れる場合があります。api_key を直接渡すか環境変数 OPENAI_API_KEY を設定してください。
- 日付の扱いは Look-ahead bias に配慮して実装されています（内部で date.today() を直接参照しない設計の関数が多い）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings オブジェクトを提供。.env / .env.local の自動ロード機能あり。
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news / news_symbols → OpenAI で銘柄別センチメントを算出し ai_scores に書き込む。
    - regime_detector.py
      - ETF(1321)の200日MA乖離とマクロニュースセンチメントを合成し market_regime に書き込む。
  - data/
    - __init__.py
    - calendar_management.py
      - 市場カレンダーの管理（営業日判定、next/prev_trading_day 等）。
    - pipeline.py
      - ETL のメインロジック（run_daily_etl など）と ETLResult。
    - etl.py
      - ETLResult の再エクスポートインターフェース。
    - stats.py
      - zscore_normalize 等の統計ユーティリティ。
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）。
    - audit.py
      - 監査ログテーブル定義と初期化ユーティリティ。
    - jquants_client.py
      - J-Quants API クライアント（取得・保存関数、認証、レート制限、リトライ）。
    - news_collector.py
      - RSS 取得・前処理・id生成・raw_news への保存を想定したユーティリティ。
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算。
    - feature_exploration.py
      - 将来リターン、IC、ファクター統計サマリ、ランク付け。
  - monitoring/, strategy/, execution/, その他
    - パッケージ __all__ に含めている名前空間（実装ファイル群はプロジェクトにより追加される想定）

---

## 実運用上の注意

- 認証トークン（J-Quants / OpenAI / kabuステーション 等）は安全に管理してください。リポジトリにハードコードしないこと。
- DuckDB の executemany が空リストを受け付けないバージョン向けのケアがコード内に含まれています。環境によってはバージョン差に注意してください。
- OpenAI 呼び出しはレート・エラー時にフォールバックやリトライ実装がありますが、API キーやコストの管理を行ってください。
- calendar / ETL はバックフィルや lookahead に関する設計があるため、バックテスト時のデータ取得タイミングに注意して利用してください（Look-ahead bias 防止のための設計が各所にあります）。

---

## 追加情報 / 開発メモ

- 自動 .env ロード:
  - プロジェクトルートはこのパッケージファイルの親階層で .git または pyproject.toml を探索して決定します。見つからない場合は自動ロードをスキップします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（テスト時に有用）。

- ロギング:
  - settings.log_level でログレベルを制御できます。

- テスト:
  - OpenAI 等の外部 API 呼び出し部分は内部の _call_openai_api をモックすることで単体テストしやすく設計されています。

---

必要であれば、README にインストール用の requirements.txt / example .env.example のテンプレートや、より具体的な利用例（ETL の cron 設定例、監視ジョブの使い方、Slack 通知フロー）を追記します。どのような追加情報が欲しいか教えてください。