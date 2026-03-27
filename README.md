# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants からのデータ取得（株価・財務・市場カレンダー）、ニュース収集と NLP による銘柄センチメント算出、リサーチ用ファクター計算、監査ログ（トレーサビリティ）管理、そして市場レジーム判定などを提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「ETL の冪等性」「外部 API 呼び出しの堅牢なリトライ/フェイルセーフ」です。

## 機能一覧

- データ取得 / ETL
  - J-Quants API からの株価日足、財務情報、上場/カレンダー情報取得（ページネーション対応、レート制御、トークン自動リフレッシュ）
  - 差分更新（バックフィル対応）と DuckDB への冪等保存（ON CONFLICT による更新）
  - データ品質チェック（欠損・スパイク・重複・日付不整合検出）

- ニュース処理 / NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事 ID のハッシュ化）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（バッチ処理、JSON Mode、リトライ）
  - マクロニュースを使った市場レジーム（bull/neutral/bear）判定（ETF 1321 の MA200 乖離と LLM スコアを重み付け）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB SQL と Python）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー、Z スコア正規化

- 監査・実行ログ
  - signal_events / order_requests / executions を含む監査スキーマの初期化と管理（監査専用 DuckDB 初期化ユーティリティ）
  - 発注・約定のトレーサビリティ（UUID ベース、冪等キー）

- ユーティリティ
  - 環境変数設定自動読み込み（.env/.env.local をプロジェクトルートから自動検出）
  - ログレベル / 実行環境判定（development / paper_trading / live）

## 前提・依存関係

- Python 3.10 以上（型付けのパイプ演算子およびその他の記法に対応）
- 必要な Python パッケージ（参考）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

実際のインストールでは pyproject/requirements に合わせてインストールしてください。

## セットアップ手順

1. リポジトリをクローン／配置
   - プロジェクトルートには pyproject.toml または .git がある前提で .env 自動読み込みを行います。

2. Python 環境を作成し依存ライブラリをインストール
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb openai defusedxml
     ```
   - 開発パッケージや固定バージョンはプロジェクトの lock ファイル / pyproject を参照してください。

3. 環境変数（または .env ファイル）を準備
   - 必須（コード上で未設定だと例外が発生します）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（実行環境で必要な場合）
     - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID: 通知先チャネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視データ用 SQLite パス（デフォルト data/monitoring.db）
     - OPENAI_API_KEY: OpenAI の API キー（AI 機能を使う場合）
   - 自動読み込みについて:
     - プロジェクトルートの .env → .env.local の順に自動読み込みされます（OS 環境変数を保護）。
     - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データベース初期化（監査ログ用の DuckDB など）
   - 監査ログ専用 DB を初期化する例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
     ```
   - アプリ全体で使用する DuckDB を接続する場合:
     ```python
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

## 使い方（代表的な例）

以下はライブラリを直接インポートして使う簡単なコード例です。実運用用のラッパー CLI / ジョブスケジューラ等を作成して呼び出すことを想定しています。

- 日次 ETL を実行する（市場カレンダー、株価、財務の差分取得 + 品質チェック）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores テーブルへ保存:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数で設定している場合、第3引数は省略可
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定を実行（ETF 1321 とマクロニュースの組合せ）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算（モメンタム等）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records), records[:3])
  ```

- 監査スキーマ初期化（既存 connection に追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- OpenAI 呼び出しがある関数（score_news, score_regime 等）は OPENAI_API_KEY を環境変数にセットするか、api_key 引数で指定してください。
- J-Quants API を使う関数は JQUANTS_REFRESH_TOKEN（リフレッシュトークン）を必要とします。
- ETL / API 呼び出しはネットワーク／レート制御／リトライを含むため、長時間実行される場合があります。

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 配下の主なモジュール:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し、バッチ）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            — ETL パイプライン（差分取得 / 品質チェック / 結果クラス）
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - news_collector.py      — RSS ニュース取得・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（Z スコア等）
    - audit.py               — 監査ログスキーマの定義・初期化
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - ai/、data/、research/ 以下に細かいヘルパー関数と堅牢性を重視した実装が入っています。

（上記は主要モジュールの抜粋です。詳細はソースを参照してください。）

## 運用上の注意・ベストプラクティス

- ルックアヘッドバイアス対策として、内部関数は target_date 未満・以前のデータのみ参照するように設計されています。バックテストではさらにデータ取得のタイミングに注意してください。
- OpenAI / J-Quants の API 呼び出しにはレート制限とリトライロジックが組み込まれていますが、運用環境でのキー管理やコスト管理は利用者側で行ってください。
- .env.local を .env より上書きで使えるため、ローカルの機密情報を .env.local として管理する運用ができます。
- 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- DuckDB のファイルパスは settings.duckdb_path で参照できます。初回起動時にディレクトリを作成するコードがある箇所もありますが、権限などに注意してください。

---

不明点や README に追記してほしいサンプル（CLI スクリプト例、systemd / cron の運用例、テーブルスキーマ抜粋など）があれば教えてください。必要に応じて具体的な運用手順やサンプルスクリプトを追加します。