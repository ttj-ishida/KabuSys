# KabuSys

日本株向けのデータ基盤＋研究＋自動売買補助ライブラリです。  
DuckDB を内部データベースとして利用し、J-Quants API / RSS / OpenAI 等と連携してデータ収集（ETL）、品質チェック、特徴量計算、ニュースセンチメント評価、マーケットレジーム判定、監査ログの管理などを行います。

バージョン: 0.1.0

---

## 概要（Project 概要）

KabuSys は以下の機能群を備えた Python パッケージ設計です：

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- ニュース（RSS）収集と前処理、銘柄への紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄ごと）およびマクロセンチメント評価
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- ファクター計算（Momentum / Value / Volatility など）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマ定義と初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動読み込み機構付き）

設計上の注意点：
- ルックアヘッドバイアス防止のため、各処理は「target_date を引数で与える」設計で内部で `date.today()` 等を無条件参照しない実装を採用しています。
- DuckDB を使った SQL + Python の組み合わせで計算を行い、外部システムへの発注処理等は本パッケージの研究／データプラットフォーム領域で分離しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得 / 前処理 / 保存）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント解析（銘柄別スコア -> ai_scores に書き込み用の score_news）
  - マクロセンチメントと ETF MA を組み合わせた市場レジーム判定（score_regime）
  - OpenAI 呼び出しにはリトライ / フォールバックの保険あり（失敗時は安全側の値で継続）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（将来リターン計算 / IC 計算 / 統計サマリー / rank 等）
- config
  - .env / .env.local 自動ロード（プロジェクトルート検出）と Settings オブジェクトで環境変数をラップ
  - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 必要条件

- Python 3.10 以上
- 主要依存パッケージ（例、環境によって適宜インストールしてください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ中心で実装されていますが、他ユーティリティやテストで追加依存がある場合があります）

依存はプロジェクトの requirements.txt / pyproject.toml を参照してください（本コードベースにはサンプル依存が想定されます）。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境を作成し有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - あるいは pyproject.toml / Poetry を使う場合は該当ツールでインストール

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成します。config モジュールは自動でプロジェクトルート（.git または pyproject.toml を起点）を探索し、環境変数を読み込みます（OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト向け）。

必須の環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN  — J-Quants API のリフレッシュトークン
- SLACK_BOT_TOKEN         — Slack 通知を使う場合
- SLACK_CHANNEL_ID        — Slack 通知先チャンネル
- KABU_API_PASSWORD       — kabuステーション API を使う場合
- OPENAI_API_KEY          — OpenAI を利用する AI 機能（score_news / score_regime）
- その他（オプション）:
  - KABUSYS_ENV (development|paper_trading|live) — 実行環境
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

（.env のパースは export 形式やクォート、インラインコメント等に対応）

---

## 使い方（簡単な例）

以下はライブラリ API を直接呼び出すサンプルです。実際は本プロジェクトの CLI やジョブスケジューラと組み合わせて運用します。

- DuckDB に接続して ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコア化して ai_scores テーブルに書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定（ma200 + マクロセンチメント）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, target_date=date(2026, 3, 20))
v = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions のテーブルが作成されます
```

注意事項：
- OpenAI 呼び出しは API キーを必要とします（env: OPENAI_API_KEY）。API の失敗時はフォールバック（0.0 等）するように設計されていますが、レートやコストを考慮して運用してください。
- J-Quants API はレート制限や認証トークン処理を行います。JQUANTS_REFRESH_TOKEN を正しく設定してください。

---

## ディレクトリ構成

主要モジュール一覧（パスは src/kabusys 以下）:

- __init__.py — パッケージエクスポート（version, submodules）
- config.py — 環境変数 / .env 自動ロード / Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースの OpenAI ベースセンチメント解析（score_news）
  - regime_detector.py — マクロセンチメント + ETF MA による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — JPX カレンダー管理、営業日判定、calendar_update_job
  - etl.py — ETL インターフェース再エクスポート
  - pipeline.py — 日次 ETL パイプライン（run_daily_etl 他）および ETLResult
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（QualityIssue 型とチェック関数）
  - audit.py — 監査ログ用 DDL と初期化ユーティリティ
  - jquants_client.py — J-Quants API クライアント（fetch/save 系）
  - news_collector.py — RSS 取得 / 前処理 / 保存（raw_news / news_symbols へ）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（上記はソース内のドキュメントを要約したもので、詳細は各モジュールの docstring を参照してください。）

---

## 開発・運用のヒント

- テストや CI で .env 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI への API 呼び出しは各 ai モジュール内で `_call_openai_api` をラップしているため、ユニットテストでは該当関数をモックして挙動を制御できます（例: unittest.mock.patch）。
- DuckDB の executemany はバージョンによって挙動に差があるため、コード中に互換性確保のための注意処理が含まれています（空リストの executemany 回避など）。
- ニュース収集では SSRF 対策や受信サイズ制限、XML の安全パース（defusedxml）を行っています。RSS ソース追加時は URL の検証や文字コードに注意してください。
- ETL は非破壊・冪等性を前提に設計されていますが、運用時は監査ログやバックアップを整備してください。

---

以上です。各モジュールには詳細な docstring を含めてありますので、実装詳細や設計理由を知りたい場合は該当ファイルを参照してください。必要であれば README にサンプル .env.example や推奨の requirements.txt、あるいは運用手順（cron / systemd / Airflow 等での実行例）を追記します。どの情報を追加しますか？