# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants からのデータ取得（株価・財務・市場カレンダー）、ニュース収集、NLP によるニュースセンチメント、自動ETLパイプライン、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- データ取得・保存
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得と DuckDB への冪等保存
  - ニュース RSS 収集と前処理・raw_news / news_symbols への登録
- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
- NLP / AI
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 / マクロ）
  - market regime（bull/neutral/bear）判定ロジック（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用モジュール
  - Momentum / Value / Volatility などのファクター計算、将来リターン計算、IC（Information Coefficient）、Zスコア正規化
- ユーティリティ
  - 市場カレンダー管理（営業日判定、next/prev trading day など）
  - データ品質チェックモジュール
  - セットアップ時の環境変数自動読み込み（.env / .env.local をプロジェクトルートから自動検出）

---

## 前提条件

- Python 3.10+
- 以下の主要依存（例）
  - duckdb
  - openai（OpenAI の Python SDK）
  - defusedxml
- ネットワークアクセス（J-Quants API / ニュースRSS / OpenAI）

requirements.txt が無い場合は上記ライブラリをインストールしてください。例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / 取得
   - 例: git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存インストール
   - pip install -r requirements.txt
   - あるいは必要なパッケージを個別にインストール:
     - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合必須）
   - OPENAI_API_KEY: OpenAI を使う機能を使う場合に指定（score_news / score_regime 等）。関数呼び出しで引数に渡すことも可。

6. 推奨設定（.env サンプル）
   - 以下のキーが利用可能です（いくつかのデフォルトあり）。
     - JQUANTS_REFRESH_TOKEN (必須)
     - OPENAI_API_KEY
     - KABU_API_PASSWORD (発注連携使用時)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO

---

## 使い方（基本例）

ここでは主要なユースケースの使い方を示します。関数はモジュール API を直接呼び出して利用します。

- DuckDB 接続の作成（例）
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（スクリプト/ジョブ）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - import duckdb, datetime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  - print(result.to_dict())

- ニュースの銘柄別センチメント取得（AI）
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - count = score_news(conn, target_date=datetime.date(2026, 3, 20))
  - print(f"書込銘柄数: {count}")

  ※ OpenAI API キーを渡す場合:
    - score_news(conn, target_date, api_key="sk-...")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=datetime.date(2026, 3, 20))

- 監査ログ・監査DBの初期化
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # これで監査用テーブルが作成される

- RSS フィード取得（ニュースコレクタ）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - for a in articles:
  -     print(a["id"], a["title"])

- J-Quants クライアントを直接使う
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使う
  - quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,1))

- データ品質チェック（例）
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - for i in issues: print(i)

注意:
- AI 呼び出しは OpenAI の利用料が発生します。API キー管理とレート制御に注意してください。
- DuckDB の executemany は空リストを受け付けない点をコード内で考慮していますが、外部から組み合わせる際は注意してください。

---

## 開発/デバッグのヒント

- 自動で .env を読み込む処理は kabusys.config にあり、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env/.env.local を読み込みます。テスト時に自動読み込みを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- settings オブジェクトから各種設定値にアクセスできます:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など
- OpenAI の呼び出し部はリトライやフェイルセーフを備えていますが、API 例外はログに出ます（完全に失敗した場合はスコアに 0 を用いる等のフォールバックがあります）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ宣言（version 等）
- config.py — 環境変数 / 設定読み込み・Settings 定義（自動 .env 読込）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（銘柄別）ロジック（OpenAI 呼び出し、バッチ処理、バリデーション）
  - regime_detector.py — マクロセンチメント + MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 / 保存ロジック / レート制御 / 認証）
  - pipeline.py — ETL パイプライン（run_daily_etl + 個別 ETL ジョブ）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・保存ユーティリティ
  - calendar_management.py — 市場カレンダー管理（営業日判定 / 更新ジョブ）
  - quality.py — データ品質チェック
  - audit.py — 監査ログテーブル定義 & 初期化ユーティリティ
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
- ai/, data/, research/ の各モジュールは DuckDB 接続や設定を受け取り、Look-ahead バイアス防止のため内部で日付を直接参照しない設計になっています。

---

## 注意事項

- 本ライブラリは実運用での発注機能（kabuステーション連携等）を含むことが想定されています。発注を有効にする際は必ずテスト環境・ペーパートレード環境で十分に検証してください（KABUSYS_ENV を paper_trading に設定する等）。
- OpenAI / J-Quants / kabu API の利用規約と料金に従ってください。
- パフォーマンスや安全性（SSRF 対策、入力正規化、リトライ処理）は各モジュールで配慮していますが、運用時にはログ監視とアラート設定を推奨します。

---

必要であれば README にサンプル .env.example、より詳細なコマンドライン例、CI / テスト実行手順などを追加できます。どの情報を優先して追記しますか？