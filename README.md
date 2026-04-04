# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注・約定追跡）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発に必要な以下の機能を提供します。

- J-Quants API を用いたデータ取得・差分 ETL（株価、財務、カレンダー）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント解析（銘柄単位）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用途のファクター計算（モメンタム / バリュー / ボラティリティ）と統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 設定は環境変数 / .env で管理（自動読み込み機構あり）

設計上の特徴:
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない等）
- DuckDB を中心としたローカル DB 管理（軽量で高速な分析に適する）
- OpenAI 呼び出しには再試行・タイムアウト・レスポンス検証を導入
- ETL / 品質チェックは部分失敗を許容し、呼び出し元が判断できる形で結果を返す

---

## 機能一覧

主な提供機能（モジュール別概略）

- kabusys.config
  - 環境変数 / .env 自動ロード、設定値アクセス（settings）
  - KABUSYS_ENV / LOG_LEVEL 等の検証

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline: run_daily_etl をはじめとした ETL エントリポイント
  - news_collector: RSS 収集・前処理・raw_news 保存
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック群
  - audit: 監査ログ用スキーマ初期化 / init_audit_db

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）200 日 MA とマクロセンチメントを合成し market_regime に書き込み

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize: クロスセクション Z スコア正規化

---

## セットアップ手順

前提: Python 3.9+（typing | union 型などを使用）を想定しています。必要に応じて適切な Python バージョンを使用してください。

1. リポジトリをクローン（またはプロジェクトディレクトリへ移動）:

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール（最低限）:

   pip install duckdb openai defusedxml

   ※ 実行環境や用途により他パッケージが必要になる場合があります。プロジェクト配布に pyproject.toml / requirements.txt がある場合はそちらを使ってください。

4. 開発 editable インストール（オプション）:

   pip install -e .

5. 環境変数を設定: .env を作成するか OS 環境に設定します。自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。自動ロードを無効化する場合:

   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（または推奨）環境変数の例:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
- DUCKDB_PATH（省略可）: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH（監視用）: デフォルト `data/monitoring.db`
- KABUSYS_ENV: development / paper_trading / live（validation あり）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

.env の読み込み優先順:
OS 環境変数 > .env.local（上書き） > .env（未上書き）

---

## 使い方（主要な例）

以下はライブラリの主要機能を簡単に呼び出す例です。実運用ではログ設定やエラーハンドリングを追加してください。

準備: DuckDB 接続の作成

from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースセンチメントをスコア化して ai_scores に保存

from kabusys.ai.news_nlp import score_news
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {count}")

3) 市場レジーム判定（1321 の MA200 乖離 + マクロセンチメント）

from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

4) 研究用ファクター計算

from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))

5) 監査ログ DB 初期化（監査テーブルを作成）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db(settings.duckdb_path)  # ファイルがなければ作成される

6) カレンダー / 営業日ユーティリティ

from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
is_trading = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))

注意点:
- OpenAI 呼び出しはネットワーク依存・API 利用料が発生します。テスト時は内部の _call_openai_api をモックしてください（各モジュールに注記あり）。
- ETL や保存処理は DuckDB 側で ON CONFLICT（冪等）設計になっています。

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注に必要）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH: 監視 / プロセスマネジメント用
- KILL_FLAG_CLEAR_ON_START: "1" で起動時に kill フラグをクリア
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live（validationあり）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

.env 例（.env.example を参考に作成してください）:

JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## ディレクトリ構成

リポジトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 - 環境設定・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py             - ニュースセンチメント（銘柄別）と ai_scores 書き込み
    - regime_detector.py      - ETF (1321) MA + マクロセンチメントによる市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント（取得・保存）
    - pipeline.py             - ETL パイプライン（run_daily_etl 等）
    - news_collector.py       - RSS 取得・前処理・raw_news 保存
    - calendar_management.py  - 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py              - データ品質チェック
    - stats.py                - 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                - 監査ログ用 DDL / 初期化ユーティリティ
    - etl.py                  - ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      - モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py  - 将来リターン / IC / 統計サマリー等

各ファイルには詳細な docstring があり、関数の引数・戻り値・副作用（DB 書き込みなど）に関する設計意図やフォールバック動作が記載されています。

---

## 開発・運用上の注意

- DuckDB は大きな分析に向くが、同時書き込みや永続化戦略については本番運用前に検討してください。
- OpenAI 呼び出しにはレート・料金があるため、バッチ設計やモックによるテストを推奨します。
- 自動 .env ロードはプロジェクトルート（.git / pyproject.toml）を基準に行います。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御してください。
- ETL・品質チェックは部分失敗を許容する設計です。結果（ETLResult）を確認して運用判断をしてください。
- 監査ログ（audit）スキーマは一度作成すると削除せず運用する想定です。init_audit_db で冪等に初期化できます。

---

必要に応じて、README に追加したい内容（例: CLI 実行方法、より具体的な .env.example、テスト手順、運用のベストプラクティスなど）を指定してください。