# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリの一部実装です。J-Quants / JPX / RSS / OpenAI（LLM）などからデータを取得・整備し、ファクター計算やニュースセンチメント、マーケットレジーム判定、監査ログなどを提供します。

以下の README はこのコードベースに含まれる主な機能・セットアップ方法・使い方・ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリはライブラリ本体の一部を抜粋した形のコードベースです。実運用には追加の設定・依存関係・運用環境構築が必要です。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存ライブラリ
- セットアップ手順
- 環境変数（.env）について
- 使い方（主要な API の例）
- ディレクトリ構成（ファイル一覧と説明）
- ライセンス / 注意事項

---

プロジェクト概要
----------------
KabuSys は日本株のデータ ETL、品質チェック、ニュースセンチメント解析（OpenAI を利用）、市場レジーム判定、研究用ファクター計算、監査ログ（注文〜約定のトレース）などを提供する Python モジュール群です。

設計上の特徴：
- DuckDB をデータストアに使用し、SQL と Python を組み合わせて効率的に処理
- Look-ahead bias を避ける設計（内部で date.today() / datetime.today() を直接参照しない関数設計）
- API 呼び出しに対するリトライ・バックオフ・レート制御を組み込み
- LLM（OpenAI）を用いたニュースの JSON モード解析（レスポンス検証付き）
- ETL は差分更新・バックフィル・品質チェックを含むワークフロー

主な機能一覧
--------------
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の検査、環境モード（development/paper_trading/live）やログレベル管理
- データ ETL（kabusys.data.pipeline, jquants_client）
  - J-Quants API から株価（daily quotes）、財務情報、市場カレンダーを差分取得して DuckDB に保存
  - レートリミット・リトライ・トークンリフレッシュに対応
- データ品質チェック（kabusys.data.quality）
  - 欠損値・重複・スパイク（急騰急落）・日付整合性チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 防御、トラッキングパラメータ除去、raw_news への保存向けユーティリティ
- カレンダー管理（kabusys.data.calendar_management）
  - market_calendar の管理、営業日判定、next/prev_trading_day など
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義と初期化（冪等）
  - 監査 DB 初期化ユーティリティ
- 研究用モジュール（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- AI 関連（kabusys.ai）
  - ニュース NLP（銘柄ごとのセンチメントを LLM で算出して ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- その他ユーティリティ（kabusys.data.stats 等）

必要条件 / 依存ライブラリ
------------------------
- Python 3.10+ （型注釈に | を使っているため最低 3.10 を想定）
- 必要パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging, typing など

（package 管理ファイルが無い抜粋版のため実際の requirements.txt は適宜用意してください。上記は最低限の主要依存です）

セットアップ手順
-----------------
1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （その他必要なパッケージがあれば追加してください）

3. パッケージをローカルインストール（開発用）
   - リポジトリルートに setup.py/pyproject.toml がある場合:
     - pip install -e .

   （この抜粋では src/ 配下にパッケージがあるため、PYTHONPATH を適切に設定するか -e インストールしてください）

4. 環境変数の設定
   - プロジェクトルートに .env を作成するか、環境変数を直接設定してください。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード (kabu 専用連携がある場合)
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime でも引数で注入可能）
   - オプション（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live (default: development)
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
   - 自動 .env ロード:
     - .env と .env.local をプロジェクトルート（.git または pyproject.toml がある場所）から自動で読み込みます。
     - OS 環境変数 > .env.local > .env の優先度です。
     - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データベース用ディレクトリの作成（必要に応じて）
   - デフォルトの duckdb パスは data/kabusys.duckdb。親ディレクトリを作成してください:
     - mkdir -p data

環境変数（.env）の書式に関して
------------------------------
- .env ファイルは .env.example を参考に作成してください（この抜粋に .env.example は含まれていませんが、キー名は config.Settings のプロパティから確認できます）。
- config モジュールはシェルスタイルの export KEY=val、クォートあり/なし、コメント行を処理できます。
- .env.local は .env を上書きする目的で使われます（ローカル専用の秘密保管）。

使い方（主要な API 例）
----------------------

以下は簡単な Python スクリプト例です。実行前に環境変数（OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN 等）を設定してください。

- DuckDB 接続と日次 ETL 実行例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）スコアリング:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に与えることも可能。None の場合は環境変数 OPENAI_API_KEY を使用
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査 DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続
  ```

- 研究用ファクター計算例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  dt = date(2026, 3, 20)
  momentum = calc_momentum(conn, dt)
  value = calc_value(conn, dt)
  vol = calc_volatility(conn, dt)
  ```

注: 上記はライブラリ API を直接呼び出す最小サンプルです。実運用ではログ設定、例外処理、ジョブスケジューリング（cron / Airflow など）を組み合わせてください。

ディレクトリ構成
-----------------

以下はこのコード抜粋に含まれる主要ファイルと簡単な説明です（src/kabusys 配下）:

- src/kabusys/__init__.py
  - パッケージメタデータ（__version__ 等）

- src/kabusys/config.py
  - 環境変数読み込み・設定管理（.env 自動ロード、必須チェック、環境モード判定）

- src/kabusys/ai/
  - __init__.py → score_news の再エクスポート
  - news_nlp.py → ニュースを LLM に投げて銘柄ごとのセンチメント（ai_scores）を生成するロジック
  - regime_detector.py → ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を生成

- src/kabusys/research/
  - __init__.py
  - factor_research.py → Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py → 将来リターン計算、IC、rank、統計サマリー

- src/kabusys/data/
  - __init__.py
  - calendar_management.py → 市場カレンダーの管理・営業日判定
  - etl.py → ETL インターフェース（ETLResult 再エクスポート）
  - pipeline.py → 日次 ETL ワークフロー（prices/financials/calendar の差分取得・保存・品質チェック）
  - stats.py → zscore_normalize 等の統計ユーティリティ
  - quality.py → データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py → 監査ログ（signal_events, order_requests, executions）DDL / 初期化
  - jquants_client.py → J-Quants API クライアント（取得・保存ロジック、レートリミット・リトライ・トークン更新）
  - news_collector.py → RSS 取得と前処理、SSRF 対策、記事ID生成など

（注）パッケージの一部（strategy, execution, monitoring 等）は __init__ の __all__ に表れている可能性がありますが、この抜粋には含まれていないファイルが存在します。実運用用の完全なリポジトリでは追加モジュールがある想定です。

ライセンス / 注意事項
--------------------
- この README はコード抜粋に基づく概要ドキュメントです。実運用する場合は依存関係・セキュリティ設定（API キー管理）・テストを必ず行ってください。
- OpenAI / J-Quants / 各 RSS ソース利用時の利用規約やレート制限、プライバシーに従って運用してください。
- 本コードを改変して商用利用する場合は、元リポジトリのライセンスを確認してください（この抜粋にライセンスファイルは含まれていません）。

もし README に追加したい具体的な内容（例: 実行する CLI、CI 設定、具体的な .env.example、requirements.txt、開発フロー、テスト方法など）があれば教えてください。必要に応じてサンプル .env.example や requirements.txt の草案も作成します。