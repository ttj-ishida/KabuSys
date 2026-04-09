# KabuSys

日本株自動売買システム（KabuSys）のコードベース用 README。

概要、機能、セットアップ手順、使い方サンプル、ディレクトリ構成を日本語でまとめています。開発向けのライブラリ群（データ取得／ETL、NLP／LLM を使ったニュース分析、ファクター研究、監査ログなど）を含むモジュール群で構成されています。

------------------------------------------------------------
概要
------------------------------------------------------------

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買のためのライブラリ群です。本コードベースには以下の主要コンポーネントがあります。

- データ取得・ETL（J-Quants API 経由で株価、財務、マーケットカレンダー取得）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）とニュース NLP（OpenAI を使ったセンチメント）
- 市場レジーム判定（MA とマクロニュースの LLM センチメント合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用テーブル）
- 設定読み込み（.env / 環境変数）

設計上のポイント:
- ルックアヘッドバイアスに注意（内部で date.today()/datetime.today() を直接参照しない設計の関数が多い）
- DuckDB を中心にローカル DB を利用
- OpenAI（gpt-4o-mini）を用いた JSON モードでの LLM 呼び出し（news_nlp / regime_detector）
- 冪等性・トランザクション処理を重視した保存処理

------------------------------------------------------------
主な機能一覧
------------------------------------------------------------

- データ取得・保存
  - J-Quants から株価（daily_quotes）, 財務（statements）, マーケットカレンダーを取得（jquants_client）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次 ETL の実行（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新・バックフィル対応
- データ品質チェック（quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合を検出
- ニュース収集（news_collector）
  - RSS 取得、テキスト前処理、raw_news への保存（冪等）
  - SSRF 対策、XML パースの安全化（defusedxml）
- ニュース NLP（news_nlp）
  - 銘柄ごとにニュースを集約し OpenAI へバッチ送信して ai_scores に書き込み
- 市場レジーム判定（regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- ファクター計算 / 研究（research）
  - Momentum / Value / Volatility 等の計算
  - 将来リターン、IC、統計サマリー等
- 監査ログ（audit）
  - signal_events / order_requests / executions といったテーブル群の初期化と管理
- 設定管理（config）
  - .env 自動読み込み（プロジェクトルート検出）と環境変数経由の設定取得
  - 環境（development / paper_trading / live）、ログレベル、各種パス、PaperTrading の挙動設定

------------------------------------------------------------
セットアップ手順（開発環境向け）
------------------------------------------------------------

前提:
- Python 3.10+ を推奨（typing | None の新構文を利用）
- Git リポジトリルートに配置されていること（config の自動 .env ロードで .git・pyproject.toml を参照）

1) 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 必要パッケージのインストール
   - 必須（最低）:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / extras が用意されている場合はそちらを利用してください）

3) 環境変数 / .env の作成
   - プロジェクトルートに .env を作成すると自動で読み込まれます（.env.local は上書き）。
   - 主要なキー（例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_FILL_MODE=instant
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     KILL_FLAG_CLEAR_ON_START=0
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で使用）。

4) データディレクトリ作成（必要に応じて）
   - settings.duckdb_path の親ディレクトリは自動作成されない箇所もあるため、必要なら作成してください。
   - 監査 DB を別ファイルで初期化する場合、parent ディレクトリは自動作成されます（audit.init_audit_db）。

------------------------------------------------------------
基本的な使い方（Python API）
------------------------------------------------------------

以下はライブラリを直接利用する簡単な例です。実運用ではログ設定やエラーハンドリングを追加してください。

- DuckDB 接続の作成例

from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）

from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュース NLP の実行（ai_scores への書き込み）

from kabusys.ai.news_nlp import score_news
from datetime import date
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {count}")

- 市場レジーム判定の実行（market_regime への書き込み）

from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")

- 監査 DB の初期化（監査専用 DB を作る場合）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへ書き込みが可能

- 設定参照の例

from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須変数（未設定時は ValueError）

注意点:
- OpenAI キーが必要な関数（score_news, score_regime 等）は api_key 引数または環境変数 OPENAI_API_KEY を要求します。未設定の場合は ValueError を送出します。
- run_daily_etl などは内部で DuckDB テーブル（raw_prices, raw_financials, market_calendar 等）を参照・更新します。バックテスト目的で使用する場合は事前に適切なデータ投入やスナップショットを行ってください（ルックアヘッドバイアス対策のため）。

------------------------------------------------------------
設定項目（主な環境変数）
------------------------------------------------------------

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY （LLM 呼び出しが必要な機能で使用）
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB、デフォルト data/monitoring.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用モック挙動）
- PAPER_TRADING_SQLITE_PATH（paper trading の DB パス）
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

------------------------------------------------------------
ディレクトリ構成（主要ファイル）
------------------------------------------------------------

src/kabusys/
- __init__.py
- config.py

src/kabusys/ai/
- __init__.py
- news_nlp.py
- regime_detector.py

src/kabusys/data/
- __init__.py
- jquants_client.py
- pipeline.py
- etl.py
- stats.py
- quality.py
- calendar_management.py
- news_collector.py
- audit.py
- pipeline.py (ETLResult が定義されている)
- etl.py (ETL の公開ラッパー)

src/kabusys/research/
- __init__.py
- factor_research.py
- feature_exploration.py

src/kabusys/research/*（ファクター計算・IC・統計サマリー）

（上記は本リポジトリで提供されている主要モジュールの抜粋です）

------------------------------------------------------------
運用上の注意／ヒント
------------------------------------------------------------

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。テスト時に自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しではリトライ・タイムアウトの考慮が実装されていますが、API コスト・レートリミットには注意してください。
- J-Quants API 呼び出しは内部でレートリミット制御およびトークン自動更新を行いますが、リフレッシュトークン（JQUANTS_REFRESH_TOKEN）は必須です。
- DuckDB のスキーマやテーブルは ETL / audit の初期化処理で作成される想定です。初期化処理を行ってからパイプラインを動かしてください。
- デバッグやログ出力は LOG_LEVEL で制御できます。開発時は DEBUG へ切り替えると詳細ログが得られます。

------------------------------------------------------------
貢献・テストについて
------------------------------------------------------------

- コード内に unittest.mock.patch 等で差し替え可能な内部関数が設計されており、テスト容易性が考慮されています（例: OpenAI 呼び出しのラッパーをモックする等）。
- データ取得の実行は外部 API に依存するため、CI ではモック／スタブを使った単体テストを推奨します。

------------------------------------------------------------
補足
------------------------------------------------------------

この README は現行ソース（src/kabusys 以下）を参照して作成しています。実際に運用する際は README に加えてプロジェクトの pyproject.toml / requirements.txt / デプロイ手順書等も参照してください。質問や追加で必要なサンプル（例: docker-compose、systemd ユニット、より詳細な初期化スクリプトなど）があればお知らせください。