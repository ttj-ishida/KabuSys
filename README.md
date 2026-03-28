# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリセット。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ・発注トレーサビリティなどを統合的に提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分取得（ETL）と DuckDB への保存
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント計算（銘柄単位 / マクロ）
- 市場レジーム判定（ETF の 200 日 MA とマクロセンチメントの合成）
- 研究用ファクター計算（Momentum / Value / Volatility 等）と統計ユーティリティ
- 監査ログ（signal / order_request / executions）のスキーマ初期化と専用 DB ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の特徴:
- ルックアヘッドバイアス対策：内部処理で datetime.today()/date.today() を不用意に参照しない
- 冪等性：DB 保存は ON CONFLICT / DO UPDATE 等で安全に上書き
- フェイルセーフ：外部 API 失敗時は局所的にフォールバックして全体を止めない
- テストしやすさ：API キー / トークン / コールを引数で注入可能

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - market calendar ヘルパー（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（RSS fetch + 前処理 + 保存）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計：zscore_normalize
- ai:
  - ニュース NLP（score_news：銘柄別 ai_score を ai_scores テーブルへ）
  - 市場レジーム判定（score_regime：1321 の MA とマクロセンチメント合成）
- research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）
- config:
  - 環境変数読み込み（.env 自動ロード）と Settings オブジェクト

---

## 必要条件 / 依存ライブラリ

- Python 3.10+（型注釈で Path|None などを使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ: urllib, json, logging 等）

例（pip インストール）:
pip install duckdb openai defusedxml

※プロジェクト化されている場合は requirements.txt / pyproject.toml に合わせてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを入手

2. 仮想環境の作成（推奨）
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール
pip install -r requirements.txt
（requirements.txt がない場合）
pip install duckdb openai defusedxml

4. 環境変数の設定
プロジェクトルートに `.env` を作成するか、OS 環境変数で設定します。自動ロードは config モジュールでプロジェクトルート（.git または pyproject.toml）を検出して行われます。テスト等で自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する .env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意:
- Settings クラスのプロパティは必須キーが未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。
- OpenAI キーなどは関数呼び出し時に明示的に渡すことも可能（テストや一時利用向け）。

---

## 使い方（主要な例）

以下はライブラリ内部 API を直接呼ぶ簡単な使用例です。実運用では CLI やジョブスケジューラから呼び出します。

- DuckDB 接続を作成して ETL を実行する
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を省略すると今日（ただし内部で営業日に調整されます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントの計算（OpenAI API キーは環境変数か引数で指定）
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote ai_scores for {written} codes")

- 市場レジーム判定
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI の API キーは環境変数 OPENAI_API_KEY か api_key 引数で

- 監査ログ DB 初期化（別 DB を監査専用に作る場合）
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます

- カレンダー判定ユーティリティ
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))

---

## ディレクトリ構成

パッケージの主要ファイルと役割（抜粋）:

src/kabusys/
- __init__.py — パッケージメタ情報
- config.py — .env / 環境変数の読み込みと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector.py — ETF(1321) の MA とマクロセンチメントを合成して market_regime に書き込む
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理 / 営業日判定
  - quality.py — データ品質チェック
  - news_collector.py — RSS フィード収集と前処理
  - audit.py — 監査ログ（テーブル定義・初期化）
  - stats.py — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — forward returns / IC / summary / rank

（プロジェクトルートには pyproject.toml / .git / .env などが存在する想定）

---

## 実装上の注意・トラブルシュート

- 環境変数未設定:
  Settings プロパティは未設定時に ValueError を送出します。JQUANTS_REFRESH_TOKEN や SLACK_BOT_TOKEN、OPENAI_API_KEY など必須値は .env に設定するか OS 環境変数で渡してください。

- 自動 .env 読み込み:
  config.py はプロジェクトルート（.git か pyproject.toml）を起点に .env を自動ロードします。CI / テストでこれを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI / J-Quants のレート制限・リトライ:
  OpenAI 呼び出し・J-Quants 呼び出しはリトライロジックと指数バックオフを備えていますが、大量バッチで実行する際は API レート制限に注意してください。news_nlp や regime_detector ではバッチサイズや最大リトライが定義されています。

- Look-ahead バイアス:
  多くの関数は内部で datetime.today() を不用意に参照しない設計です。バックテスト等では target_date を明示的に渡してください。

- DuckDB の executemany 空リスト:
  一部の DuckDB バージョン（例: 0.10）で executemany に空リストを渡すとエラーになるため、コードは空チェックを行っています。もし insert が失敗する場合は params が空でないか確認してください。

- RSS 収集のセキュリティ:
  news_collector は SSRF 対策（リダイレクト検査、プライベート IP 拒否）、gzip サイズ検査、defusedxml を導入しています。外部フィードの追加は十分に信用できるソースを指定してください。

---

## 開発・テスト時のヒント

- API 呼び出しの差し替え:
  テストでは OpenAI 呼び出しや HTTP 層をモックできるように設計されています。内部の `_call_openai_api` や `_urlopen` 等を unittest.mock.patch で差し替えてテストしてください。

- 設定の開始:
  .env.example を作って必要なキーだけ埋め、まずは小さい target_date や memory DB (":memory:") で動作確認することをおすすめします。

---

必要であれば README に CLI 例、docker-compose サンプル、CI の設定例（GitHub Actions）や、さらに詳しい .env.example を追加できます。どの情報がさらに欲しいか教えてください。