# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。ETF／株価データのETL、ニュース収集とLLMベースのニュースセンチメント、ファクター計算、監査ログ（発注トレーサビリティ）、マーケットカレンダー管理などを包含します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を提供するモジュール群で構成された Python パッケージです。

- J-Quants API を用いた株価・財務・上場情報・マーケットカレンダーの取得と DuckDB への保存（ETL）
- ニュース収集（RSS）から raw_news を作成するニュースコレクタ
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント分析（ai.news_nlp）
- マクロセンチメントと価格指標（1321 ETF の 200 日 MA 乖離）を合成した市場レジーム判定（ai.regime_detector）
- ファクター生成・特徴量解析・IC 計算等のリサーチユーティリティ（research）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用のスキーマ初期化ユーティリティ
- 環境設定管理（.env 自動読み込み / settings オブジェクト）

設計上の要点:
- ルックアヘッドバイアスを避けるため、内部で date.today() や datetime.today() に依存しない設計（呼び出し側が target_date を与える）
- DuckDB を主な永続化層に利用
- 冪等性（ON CONFLICT）とリトライ・バックオフロジックを重視
- 外部 API 呼び出し失敗時はフェイルセーフ（多くの処理でスキップして継続）

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・レート制御・保存関数）
  - マーケットカレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS -> raw_news、SSRF 対策、URL 正規化）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency, run_all_checks）
  - 監査スキーマ初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM でセンチメントスコア生成し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数読み込み（.env / .env.local 自動読み込み）。settings オブジェクト経由で設定参照。

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

実運用ではさらに logging 等の設定、Slack 連携用ライブラリなどが必要になる可能性があります。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   - 例（UNIX/macOS）:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストールします（例）:

   - pip install -U pip
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。

3. パッケージを編集可能モードでインストール（オプション）:

   - pip install -e .

4. 環境変数を設定します（.env をプロジェクトルートに置くと自動で読み込まれます）。
   - 自動ロードは config モジュール (_find_project_root 経由) によりプロジェクトルートの .env/.env.local を優先的に読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注関連）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）

その他（デフォルト値あり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/…
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視用 DB デフォルト data/monitoring.db
- PID_FILE_PATH、CPU_THRESHOLD_PCT など（監視設定）

.env の簡易例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

前準備: DuckDB 接続を用意します。ここではファイル DB を使用する例。

Python スクリプト例:

- ETL（日次 ETL 実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら環境変数 OPENAI_API_KEY を使用
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（別 DB として使用する例）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は監査スキーマが初期化済みの DuckDB 接続
  ```

- マーケットカレンダー関連
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- score_news / score_regime は OpenAI の API キー（引数か OPENAI_API_KEY 環境変数）が必須です。
- ETL 系は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）を設定しておく必要があります。
- 多くの関数は target_date を引数として受け取り、内部で日時を固定しルックアヘッドを避ける設計です。

---

## 設定の自動読み込み挙動

- 起点は config._find_project_root() により .git か pyproject.toml が見つかる親ディレクトリ（プロジェクトルート）を探索します。見つかった場合、project_root/.env（上書きしない）→ project_root/.env.local（上書き） の順で読み込みます。
- OS 環境変数は .env の上位優先です（.env の上書きは行われません）が、.env.local は override=True として読み込むため .env の値を上書きできます。ただし既存の OS 環境変数（読み込み時に存在していたもの）は protected として上書きされません。
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュール構成です（src/kabusys 以下）。

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
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (コードベースに存在する想定の監視関連モジュール)
  - execution/ (発注・実行ロジック用の想定モジュール)
  - strategy/ (トレード戦略定義用の想定モジュール)

（上記はコード中にあるファイルを元にした抜粋です）

---

## 開発・テストのヒント

- OpenAI / 外部 API 呼び出しはモック可能な設計（内部の _call_openai_api を patch）になっています。ユニットテストでは外部への実際のリクエストを避けるためにモックしてください。
- duckdb.connect(":memory:") を使えばインメモリ DB でテストが容易です。
- 自動 .env 読み込みを無効化してテスト専用の環境を構築するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用します。

---

## ライセンス・連絡

この README ではライセンス情報・連絡先の記載がありません。実運用する際はリポジトリの LICENSE やプロジェクト管理者に従ってください。

---

README は以上です。README に載せたい追加の内容（例: 実行スクリプト、CI 設定、より詳細な API 仕様など）があれば教えてください。