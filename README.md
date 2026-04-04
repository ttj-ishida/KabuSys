# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュースの収集と LLM によるスコアリング、ファクター計算、監査ログ（発注〜約定トレース）など、アルゴリズムトレーディングの基盤機能を提供します。

主な設計方針
- DuckDB を中心としたローカルデータプラットフォーム
- Look‑ahead bias を避ける設計（内部で date.today()/datetime.today() を直接参照しない）
- 冪等 (idempotent) な DB 保存・ETL
- 外部 API 呼び出し（J‑Quants / OpenAI）はリトライ・バックオフ・レート制御あり
- 失敗時はフェイルセーフ（可能な限り例外を上位へ伝播させず続行する設計箇所あり）

---

## 機能一覧

- データ取得・ETL
  - J‑Quants から株価（OHLCV）、財務、JPX マーケットカレンダーを差分取得（jquants_client）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP
  - RSS フィード収集・前処理（news_collector）
  - ニュースを銘柄ごとに集約して OpenAI に送信しセンチメントスコアを ai_scores に書込む（news_nlp.score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - Momentum / Value / Volatility 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC 計算、統計サマリー（research.feature_exploration）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理（data.audit）
- ユーティリティ
  - カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - データ統計ユーティリティ（zscore_normalize）

---

## 前提・依存関係

- Python 3.10+
- 必須ライブラリ（一例）
  - duckdb
  - openai
  - defusedxml
- その他 標準ライブラリ（urllib, json, datetime, logging 等）

requirements.txt はリポジトリに含まれていない想定のため、プロジェクト用途に合わせて必要パッケージをインストールしてください。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. Python を用意（3.10 以上推奨）

2. リポジトリルートでパッケージをインストール
   - 開発中:
     pip install -e .

   - または production のみ必要なパッケージを個別にインストール:
     pip install duckdb openai defusedxml

3. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を置くと自動でロードします（デフォルト設定）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（少なくとも API を使う場合）
- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu API 用パスワード（発注系を使う場合）
- OPENAI_API_KEY : OpenAI を使う場合（news_nlp / regime_detector / 他）
- あると便利な設定
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)

例（.env）
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（基本的な API 例）

※ すべて Python から呼び出す想定です。プロセス起動スクリプトや cron などでラップして運用してください。

- DuckDB 接続準備（デフォルト path を使用）
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ニュースのスコアリング（対象日を明示）
from datetime import date
from kabusys.ai.news_nlp import score_news
n_written = score_news(conn, target_date=date(2026, 3, 19))  # 例
print("scored:", n_written)

- 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 19))

- 監査ログ DB 初期化（別 DB にすることを推奨）
from kabusys.data.audit import init_audit_db
aud_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- J‑Quants から手動で株価取得
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を参照
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))

- カレンダー更新ジョブ（夜間バッチ想定）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)

注意点
- OpenAI 呼び出しは api_key 引数で明示的に渡すことが可能（api_key=None の場合は環境変数 OPENAI_API_KEY を使用）。
- 多くの関数は target_date を明示的に受け取り、内部で現在時刻を参照しない設計です（バックテスト安全性）。

---

## 設定の自動ロード挙動

- パッケージ読み込み時（kabusys.config）はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  - .env を先にロード（既存の OS 環境変数を上書きしない）
  - .env.local を次にロード（既存の OS 環境変数を上書き可能）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- 必須の値を使う際は settings オブジェクトが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN がない場合）。

例:
from kabusys.config import settings
token = settings.jquants_refresh_token  # 未設定なら ValueError

---

## ディレクトリ構成（主要ファイルと役割）

src/kabusys/
- __init__.py - パッケージエクスポート
- config.py - 環境変数 / 設定管理（.env 自動ロード / settings オブジェクト）

src/kabusys/ai/
- __init__.py
- news_nlp.py - ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出、ai_scores に書込む
  - calc_news_window(target_date)
  - score_news(conn, target_date, api_key=None)
- regime_detector.py - ETF 1321 の MA200 乖離 + マクロニュースセンチメントで market_regime を作成
  - score_regime(conn, target_date, api_key=None)

src/kabusys/data/
- __init__.py
- jquants_client.py - J‑Quants API クライアント（fetch/save 系）
- pipeline.py - ETL パイプライン（run_daily_etl, run_prices_etl, ...）および ETLResult
- etl.py - ETLResult の再エクスポート
- calendar_management.py - 市場カレンダー管理・ユーティリティ（is_trading_day, next_trading_day, calendar_update_job）
- news_collector.py - RSS 収集・前処理・raw_news への保存
- quality.py - データ品質チェック群（check_missing_data, check_spike, ...）
- stats.py - 汎用統計ユーティリティ（zscore_normalize）
- audit.py - 監査ログテーブル初期化（init_audit_schema / init_audit_db）

src/kabusys/research/
- __init__.py
- factor_research.py - Momentum / Value / Volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
- feature_exploration.py - 将来リターン、IC、統計サマリー等

---

## 開発・運用上の注意

- DuckDB のバージョン差異（executemany の挙動やリストバインド）に注意（コード内に互換性処理あり）。
- OpenAI / J‑Quants の API リクエストはレート制御・リトライがあるが、運用時はレート制限に余裕を持つこと。
- ニュース収集は SSRF 対策・XML パース対策（defusedxml）済み。ただし外部 RSS の信頼性は保証しない。
- 監査ログは削除せずに永続化する前提。order_request_id は冪等キーとして扱われます。
- 本リポジトリは CLI ツールを含みません。必要に応じて運用用のスクリプト（cron / systemd timer / Airflow 等）を用意してください。

---

もし README に追加したい項目（例: CI / テストの実行方法、サンプル .env.example の完全版、運用 runbook など）があれば教えてください。必要に応じてサンプルスクリプトや docker-compose 等のテンプレートも作成できます。