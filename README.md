# KabuSys

日本株自動売買プラットフォームのための内部ライブラリ群。データETL、ニュースNLP（LLMベース）、市場レジーム判定、リサーチ用ファクター計算、監査ログなど、自動売買基盤に必要な主要コンポーネントを提供します。

本READMEはこのコードベース（src/kabusys）に対する概要、機能、セットアップ手順、主要な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- RSSからのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄毎）とマクロセンチメントのスコア化
- ETF（1321）200日移動平均乖離とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）とリサーチ用ユーティリティ
- データ品質チェック・監査ログ（signal→order→execution のトレーサビリティ）
- DuckDB ベースのローカルデータ保存処理

設計方針として「ルックアヘッドバイアスの防止」「冪等性」「フェイルセーフ（API失敗時の継続）」を重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSSの正規化、SSRF対策、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査テーブル初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュースセンチメント: score_news (銘柄別 ai_scores へ書き込み)
  - マクロ / レジーム判定: score_regime (market_regime テーブルへ書き込み)
  - 両方とも OpenAI Chat Completions（JSON Mode）を使用し、リトライ/バックオフやレスポンス検証を実装
- research
  - ファクター計算：calc_momentum / calc_value / calc_volatility
  - 特徴量探索：calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数 / .env 自動読み込み（.env.local 優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で設定参照（例: settings.jquants_refresh_token）

---

## 要件（推奨）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai（OpenAI公式クライアント）
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime など

（実際の pip パッケージはプロジェクトの packaging に応じて requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （追加で logging / 他ライブラリがあれば適宜インストール）
4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` を作成すると自動で読み込まれます（.env.local は .env の上書き）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。
5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注周り）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で参照）
   - 省略可能設定:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトからライブラリを呼び出す例です。DuckDB 接続を渡して操作します。

- 共通準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path を返す
  ```

- 日次 ETL を実行する（カレンダー・株価・財務を差分取得し品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄毎）スコア付け（ai_scores に書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数で設定されていれば api_key 引数は省略可
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（market_regime に書き込む）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログ用 DB の初期化（独立した監査用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- ファクター計算（リサーチ用）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  ```

- その他ユーティリティ
  - カレンダー判定: kabusys.data.calendar_management.is_trading_day(conn, some_date)
  - データ品質チェック: kabusys.data.quality.run_all_checks(conn, target_date=...)
  - 環境設定参照: from kabusys.config import settings; settings.log_level / settings.env / settings.is_live など

注意:
- score_news / score_regime など OpenAI を使う処理は API キーが必須です（引数で注入可能）。
- すべての API 呼び出しはリトライやフォールバックロジックを持っていますが、API制限・課金に注意してください。
- ETL / AI 処理はルックアヘッドバイアスを避ける実装方針です（target_date 引数を正しく与えてください）。

---

## .env 自動読み込みについて

- モジュール kabusys.config はパッケージロード時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 読み込み優先度: OS 環境 > .env.local > .env
- 自動読み込みを無効化するには環境変数を先にセットしておく:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイルと役割）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュース記事の LLM ベース スコアリング（score_news）
  - regime_detector.py — マクロ + ETF MA200 乖離で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の公開（再エクスポート）
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - news_collector.py — RSS ニュース収集・正規化・保存
  - quality.py — データ品質チェック（欠損/スパイク/重複/日付整合）
  - audit.py — 監査ログスキーマ初期化（signal/order/execution）
  - stats.py — 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー, ランク変換
- research パッケージおよびその他モジュールはリサーチ用途で外部副作用なしに設計されています

---

## 注意点・運用メモ

- OpenAI や J-Quants は API レート・課金に注意して使用してください。コード内にリトライ・バックオフを実装していますが、運用環境でのレート管理は必須です。
- DuckDB スキーマやテーブルは ETL 実行前に適切に作成されている必要があります（ETL 側で期待するテーブルが無いと動作しません）。初期スキーマ作成手順は別途スクリプト/ドキュメントで準備してください。
- 監査テーブルは削除を想定していません（トレーサビリティ保持）。init_audit_db は既存 DB に対して冪等にテーブルを追加します。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、自前で環境を注入してください。AI呼出しやネットワークはモックしやすいように内部呼び出し `_call_openai_api` などを差し替えられる設計です。

---

## 参考（よく使う設定 / コマンド）

- 仮想環境作成・パッケージインストール
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb openai defusedxml
  ```
- ETL 実行（例スクリプト run_etl.py を用意して実行）
- AI スコアリングを定期で実行する場合は cron / Airflow / Prefect 等で target_date を適切に渡してスケジュールしてください。

---

必要であれば README にサンプル .env.example、requirements.txt、または初期スキーマ作成 SQL のテンプレートを追記できます。どの内容を追加したいか教えてください。