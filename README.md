# KabuSys

日本株自動売買プラットフォームのライブラリ群（モジュール群）の一部実装です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、AI を使ったニュースセンチメント／市場レジーム判定、監査ログなどのユーティリティを提供します。

---

## 概要

KabuSys は日本株の自動売買システムを構成する共通コンポーネント群です。本コードベースは主に以下を扱います。

- J-Quants API を用いた株価/財務/マーケットカレンダーの取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理
- OpenAI を利用したニュースセンチメント（銘柄別）および市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）を保存するスキーマ初期化

設計上の共通方針として「ルックアヘッドバイアス防止（バックテストの公平性）」「冪等性」「フェイルセーフ（API失敗時に処理継続）」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し（ページネーション、認証自動リフレッシュ、レートリミット、DuckDB への冪等保存）
  - pipeline: 日次 ETL のエントリ（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
  - quality: データ品質チェック（missing / duplicates / spike / date consistency）
  - news_collector: RSS 取得・前処理・保存（SSRF 対策、トラッキングパラメータ除去）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログテーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロニュースセンチメントを合成して market_regime を更新
- research/
  - factor_research: モメンタム／バリュー／ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（情報係数）、ファクター統計サマリ 等
- config: .env 自動読み込みと Settings（必須・推奨環境変数のラッパー）

---

## 要件（推奨）

- Python 3.10+（型ヒントの union 演算子 `|` を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース）
- J-Quants のリフレッシュトークン、OpenAI API キー 等の環境変数

（プロジェクトの requirements.txt がある場合はそれを使用してください）

---

## セットアップ

1. リポジトリをクローン／チェックアウト

2. Python 仮想環境を作成して有効化（例）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. 依存パッケージをインストール（プロジェクトに requirements.txt があればそれを利用）

   ```bash
   pip install duckdb openai defusedxml
   # または
   pip install -r requirements.txt
   ```

4. パッケージを開発モードでインストール（任意）

   ```bash
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（kabusys.config が自動読み込み）。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主要）

必須／推奨の一部を抜粋します。README 作成時点のコード参照。

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用する場合）

認証・API 関連:
- KABU_API_PASSWORD — kabu ステーション API を使う場合
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

通知（任意）:
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID

データベース / ファイルパス（デフォルトあり）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

ランタイム設定:
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

注意: Settings クラスは未設定の必須キーに対して ValueError を投げます。

---

## 使い方（主要なユースケース）

以下はライブラリをインポートして実行する Python スニペット例です。適切に依存関係と環境変数を設定した上で実行してください。

- DuckDB 接続を作る例:

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（run_daily_etl）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しないと今日で実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を計算して ai_scores に書き込む:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定しておくか api_key 引数を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} scores")
  ```

- 市場レジーム判定（regime）:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB の初期化（監査専用 DuckDB）:

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_schema は上の関数内部で実行されます
  ```

- J-Quants API から直接データを取得する（単体呼び出し）:

  ```python
  from kabusys.data.jquants_client import fetch_listed_info, fetch_daily_quotes

  info = fetch_listed_info()  # id_token を省略すると settings.jquants_refresh_token を使用して取得
  quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,31))
  ```

- RSS 取得の例（news_collector.fetch_rss）:

  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しはネットワークと API キーを必要とします。レスポンスのパース・API エラーに対してフォールバックする実装になっていますが、API 利用量には注意してください。
- ETL / データ保存・品質チェックは DuckDB 上のテーブルスキーマが前提です。テーブルが存在しない場合は ETL 関数が schema 初期化を行わないため、必要に応じてスキーマ作成ロジックを用意してください（実プロジェクトでは schema モジュールが別に存在する想定）。

---

## ディレクトリ構成（主要ファイル）

以下はこのコードベースで確認できる主要モジュールのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/  (README の対象コードには詳細実装なし)
    - strategy/    (README の対象コードには詳細実装なし)
    - execution/   (README の対象コードには詳細実装なし)

各モジュールは機能ごとに分離され、テストや再利用がしやすいように設計されています。

---

## テスト／ローカル開発時のヒント

- config はプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動読み込みします。テストで自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI 呼び出し（news_nlp / regime_detector）の内部で OpenAI クライアントへの実際の呼び出しを行う箇所は、ユニットテストではモック（patch）して外部呼び出しを避ける設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB 接続はファイルパス（settings.duckdb_path）か ":memory:" を指定できます。テストでは ":memory:" を使うと便利です。

---

## 貢献・ライセンス

本 README はコードベースから派生した説明です。実運用に使用する場合は、秘匿情報（APIキー等）の管理や schema 初期化、運用ジョブ（cron / systemd）やログ／監視の組み込みを別途行ってください。ライセンスやコントリビュート規約はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本リポジトリに存在する場合）。

---

必要であれば、README にサンプル .env.example、DuckDB スキーマ作成スクリプト、より詳しいユースケース（バックテスト用の注意点等）を追加で作成します。どの情報を追加しますか？