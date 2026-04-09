# KabuSys

KabuSys は日本株のデータ取得・ETL、ニュース NLP、市場レジーム判定、研究用ファクター計算、監査ログ管理などを含む日本株自動売買／データプラットフォームの Python ライブラリです。本 README はコードベース（src/kabusys）に基づく概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群を含みます。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（ETL）と DuckDB への冪等保存
- RSS からのニュース収集およびニュースの前処理（SSRF 対策、トラッキングパラメータ除去等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- ETF（1321）200日移動平均乖離とマクロセンチメントを合成した市場レジーム判定
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）管理

設計上、バックテスト／ルックアヘッドバイアスに配慮した実装（現在時刻を直接参照しない、DB の日付条件を厳格化）や、外部 API に対する堅牢なリトライ／フォールバック処理を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、ページネーション、レート制御、保存関数）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（銘柄別センチメント score_news）
  - 市場レジーム判定（score_regime）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数 / .env 自動読み込み、設定値ラッパー（settings）

---

## 要件

- Python 3.10+
- 必要な外部パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）および環境変数の設定

（実際のパッケージ要件はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## インストール

ローカルで編集しながら使う場合の例：

1. ソースルートで仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージと依存をインストール
   - pip install -e .                # editable install
   - pip install duckdb openai defusedxml

（プロジェクトに requirements ファイルや Poetry があればそちらに従ってください）

---

## 環境変数と .env

config.py は自動でプロジェクトルートの `.env` と `.env.local`（.git または pyproject.toml を基準に探索）を読み込みます。自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 認証リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で参照）
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading のモック埋め合せ動作（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

簡易的な .env.example:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（DB 初期化等）

- 監査ログ用 DuckDB の初期化例:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続（UTC タイムゾーンが設定済み）

- ETL 用 DuckDB（スキーマ準備は別モジュールで管理されている想定）の接続:

import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

（必要に応じて data/schema 初期化関数がある場合は呼ぶ）

---

## 使い方（代表的な API）

以下は Python API の利用例。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY など）を設定してください。

- 日次 ETL を実行する

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（銘柄別）をスコアリングする

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None は環境変数参照
print("written:", n_written)

- 市場レジームをスコアリングする

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 研究用ファクター計算（例: momentum）

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)

注意点:
- score_news / score_regime は OpenAI API を呼び出します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl 等はネットワーク I/O（J-Quants）を含みます。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- DuckDB 接続を渡す際は適切なファイルパス（settings.duckdb_path）を利用してください。

---

## 主要な設計上の注意事項

- ルックアヘッドバイアス防止のため、モジュール内の多くの関数は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計です。バックテストでは適切な target_date を与えてください。
- 外部 API 呼び出しは堅牢化（リトライ、指数バックオフ、401 リフレッシュなど）されていますが、実行環境のレート制限や API キーの制約には注意してください。
- news_collector は SSRF 対策と XML パースに defusedxml を使用しています。RSS フィード取得時に内部アドレスや非 http/https スキームをブロックします。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で行われます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 jquants_client の補助モジュール等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, execution/, strategy/ など（パッケージとして __all__ で公開される想定）

（上記はリポジトリ内の代表的なモジュールを抜粋したものです。実際のトップレベルにはさらにモジュールが存在する場合があります）

---

## ロギング／監視

- 設定は環境変数 LOG_LEVEL で指定します（デフォルト INFO）。
- 実行中の監視に使う設定（PID ファイル、kill フラグ、CPU/MEM/DISK閾値等）は Settings にて環境変数経由で指定できます。

---

## 開発・テストのヒント

- config の自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストで環境を汚したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
- OpenAI 呼び出し部分は内部で明示的に分離され、テスト時はモック（unittest.mock.patch）で差し替えやすいように設計されています。
- DuckDB を使った関数は、":memory:" を渡してインメモリ DB で単体テストを行うことが可能です。

---

## ライセンス / 貢献

- 本 README ではライセンス情報を含めていません。リポジトリの LICENSE ファイルを確認してください。
- バグ報告・プルリクエストはリポジトリの Issue / PR を通じてお願いします。

---

この README はコードベース内の docstring と実装に基づいて作成しています。追加で README に記載したい運用手順（例: cron ジョブ、デプロイ方法、監視設定、具体的な SQL スキーマ定義など）があれば教えてください。README を拡張して運用向けの手順やサンプルスクリプトを追記します。