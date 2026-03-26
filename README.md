# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター計算、監査ログ（発注トレーサビリティ）などを含む、研究〜運用フェーズ向けユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株のアルゴリズム取引システムを構成するための内部ライブラリ群です。主に次の領域をカバーします。

- データプラットフォーム（J-Quants API からの差分 ETL、データ品質チェック、マーケットカレンダー管理）
- ニュース収集（RSS）と前処理（SSRF 対策・URL 正規化）
- ニュースに対する LLM（OpenAI）ベースのセンチメント解析（銘柄単位 / マクロセンチメント）
- 研究用ファクター計算・特徴量解析（モメンタム・ボラティリティ・バリュー・IC 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 環境設定管理（.env 自動読み込み・必須環境変数検査）

設計上の特徴として、ルックアヘッドバイアスの防止、DuckDB を中心としたローカル DB 利用、API 呼び出しでのリトライ・レートリミッティング、フェイルセーフ（API 失敗時は中立化・スキップ）などが考慮されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 機能、トークン自動リフレッシュ、レート制限）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days 等）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - ニュース収集（RSS 取得、正規化、raw_news への保存支援）
  - 監査ログ初期化（監査テーブル作成、init_audit_db）
  - 統計ユーティリティ（zscore 正規化）

- ai
  - ニュース NLP（銘柄ごとのセンチメント算出：score_news）
  - 市場レジーム推定（ma200 と マクロセンチメントの合成：score_regime）

- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - data.stats の zscore_normalize

- config
  - .env / 環境変数の自動読み込み（プロジェクトルート基準）
  - settings オブジェクト経由の安全な設定取得（必須チェック含む）

---

## 必要な環境 / 依存

（プロジェクトの setup.py / pyproject.toml が別途ある想定。最低限必要なパッケージは次の通り）

- Python 3.9+（型ヒントで | 型などを使っているため 3.10 以上推奨）
- duckdb
- openai
- defusedxml

インストール例（仮）
pip install duckdb openai defusedxml

また、OpenAI と J-Quants の API キー／トークンが必要です（下記参照）。

---

## 環境変数と設定

自動で .env / .env.local をプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）から読み込みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（アプリケーション起動や一部機能で必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD : kabuステーション等のAPIパスワード（使用するモジュールがある場合）
- SLACK_BOT_TOKEN : Slack 通知用トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID

任意／デフォルトあり:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY : OpenAI API キー（AI 関数に未指定の場合、env から読み込み）

.env.example を参照して .env を作成してください（リポジトリに .env.example があることを想定）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定します。
   - 最小: JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY（AI 機能を利用する場合）

5. DuckDB ファイルや出力先ディレクトリを作成（自動作成する関数もありますが、手動で確認）
   mkdir -p data

---

## 使い方（例）

以下は主要機能の簡単な利用例です。実行は Python スクリプトや REPL から行います。

- DuckDB 接続を作成して日次 ETL を実行する

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュース NLP（銘柄単位のスコア付け）

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されている場合、api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（ma200 と マクロセンチメント合成）

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます

- 研究用ファクター計算（例：モメンタム）

from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト

注意点:
- LLM を使う関数（score_news, score_regime）は OpenAI API を呼びます。API キーは api_key 引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- 各処理は Look-ahead バイアスに配慮して `target_date` を明示的に与える設計です。内部で date.today() / datetime.today() を参照しないか限定的に使っています（コメントを参照）。

---

## .env 自動読み込みの挙動

- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点に .env と .env.local を自動読み込みします。
  読み込み順: OS 環境変数（優先） > .env.local > .env
- テストや特殊用途で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- settings オブジェクトを利用して必須パラメータを取得します（未設定時は ValueError）。

例:
from kabusys.config import settings
print(settings.duckdb_path)

---

## ディレクトリ構成（抜粋）

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
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - stats.py
  - quality.py
  - audit.py
  - trakt…（その他データ関連モジュール）
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research や他のサブパッケージ（strategy / execution / monitoring は __all__ に含まれるが、本リストは主要モジュールの抜粋です）

各ファイルは（README に含めた）機能説明のドキュメント文字列を持ち、DuckDB を前提とした SQL / Python ハイブリッド処理で実装されています。

---

## 開発・貢献

- テストや CI の実行方法、コーディング規約、ブランチ戦略等は別途 CONTRIBUTING.md を用意することを推奨します。
- 外部 API（OpenAI / J-Quants）呼び出し部分はモックしやすいように設計されています（ユニットテストでの差し替えを想定）。

---

もし README に追加したい内容（インストール用の pyproject/requirements の具体例、CI 設定、より詳しいサンプルスクリプト、環境変数の .env.example テンプレートなど）があれば教えてください。必要に応じて追記・補完します。