# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → ファクター計算 → AIによるニュースセンチメント評価 → 戦略判定・監査ログといった一連の処理をサポートします。

---

## 概要

KabuSys は日本株の研究・運用向けに設計されたモジュール群です。主な目的は次の通りです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して DuckDB に格納する（差分取得・冪等保存・レートリミット対応）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュースを収集・前処理し、OpenAI（gpt-4o-mini 等）で銘柄別・マクロセンチメントを判定
- ファクター計算・リサーチユーティリティ（モメンタム・バリュー・ボラティリティ等）
- 市場レジーム判定（ETF MA と マクロニュースの合成）
- 監査ログ（シグナル → 発注 → 約定を追跡する監査テーブル）を DuckDB に初期化・管理

設計上の特徴：

- Look-ahead bias に配慮した日時・クエリ設計（バックテスト安全性）
- API リトライ・指数バックオフ・レート制御
- DuckDB を中心に冪等保存（ON CONFLICT）でデータ整合性を確保
- テストしやすさ（API 呼び出し部分を差し替え可能、環境変数自動ロードを無効化可能）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーの差分取得
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（quality.run_all_checks 等）
- ニュース処理 / NLP
  - RSS 収集（news_collector.fetch_rss）および前処理
  - OpenAI を用いた銘柄別ニューススコアリング（ai.news_nlp.score_news）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary など
  - zscore_normalize（data.stats）
- 監査ログ（audit）
  - 監査用テーブル定義・初期化（init_audit_schema / init_audit_db）
- 設定管理
  - 環境変数・.env 自動ロード（config.Settings / settings）

---

## 必要条件

- Python 3.10+
- 推奨ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI API 等）
- J-Quants リフレッシュトークン、OpenAI API キー 等の設定（環境変数）

実際のプロジェクトでは requirements.txt を用意してください。最低限のインストール例：

pip install duckdb openai defusedxml

（パッケージ化されている場合は pip install -e . や requirements.txt を利用してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して依存関係をインストール

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   # requirements.txt が無い場合:
   pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が起動時に探索してロードします）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

4. 必須環境変数（代表）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY : OpenAI API キー（ai モジュールを使うときに必要）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（発注周り）
   - 追加（任意）:
     - KABUSYS_ENV : 開発環境 ("development" / "paper_trading" / "live")（デフォルト development）
     - LOG_LEVEL : ログレベル ("DEBUG","INFO",...)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH 等

   例 .env:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. データディレクトリを作成（必要に応じて）

   mkdir -p data

---

## 基本的な使い方（例）

以下は代表的な使い方のサンプルです。実行環境によってパスや日付を調整してください。

- DuckDB 接続を作って日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API が必要）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すか環境変数 OPENAI_API_KEY をセット
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)

- 市場レジームスコアを計算して保存

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ用データベースを初期化（ファイル作成込み）

  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # ":memory:" を指定するとメモリ DB

- RSS を取得する（news_collector）

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])

注意点：
- OpenAI API 呼び出しはレスポンスの検証とリトライロジックを備えていますが、API コストとレート制限に注意してください。
- DuckDB の接続はスレッドセーフに扱ってください。長寿命プロセスでは接続管理を明確に。

---

## 主要モジュール（ディレクトリ構成）

下記はプロジェクト内の主要ファイル・モジュール群の概略です（抜粋）。

- kabusys/
  - __init__.py （パッケージ定義）
  - config.py （環境変数・設定管理）
  - ai/
    - __init__.py
    - news_nlp.py （ニュースの集約・OpenAI による銘柄センチメント評価）
    - regime_detector.py （ETF MA とマクロニュースで市場レジーム判定）
  - data/
    - __init__.py
    - jquants_client.py （J-Quants API クライアント、保存関数含む）
    - pipeline.py （ETL パイプラインのエントリポイント）
    - etl.py （ETLResult の再エクスポート）
    - news_collector.py （RSS 収集・前処理）
    - calendar_management.py （市場カレンダー管理 / 営業日判定）
    - quality.py （データ品質チェック）
    - stats.py （汎用統計ユーティリティ）
    - audit.py （監査ログテーブルの DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py （モメンタム／バリュー／ボラティリティ等）
    - feature_exploration.py （将来リターン・IC・統計サマリー）

各モジュールは README の docstring に設計方針・処理フローが明示されています。ソースコード自体が詳細なドキュメントになっています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン（get_id_token に利用）
- OPENAI_API_KEY (required for AI modules): OpenAI API キー
- KABU_API_PASSWORD: kabuステーション API のパスワード
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL: ログレベル（"INFO" など）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

（他に LINE や監視設定用の環境変数が存在します。config.Settings を参照してください）

---

## テスト・開発メモ

- OpenAI 呼び出し部分は内部でラップされており、ユニットテストでは該当関数をモックして差し替えられるよう設計されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）から行われます。テスト時に CWD に依存しないよう設計されています。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- DuckDB の executemany に空リストを渡すといったバージョン依存の挙動に注意（コード内でガードあり）。
- 外部 API はネットワークエラー・429・5xx に対してリトライ実装がありますが、長期的にはレート計画やコスト管理を必ず行ってください。

---

## 貢献

- バグ報告・プルリクエストは歓迎します。設計方針に従って、Look-ahead bias を導入しないこと、外部 API 呼び出しは差し替え可能にすること、DB 書き込みは可能な限り冪等にすることを守ってください。

---

以上がこのコードベースの README です。個別の関数やモジュールの使い方は各ファイルの docstring を参照してください。必要であればサンプルスクリプトや CI 設定、requirements.txt を追加した README の拡張も作成できます。