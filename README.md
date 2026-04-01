# KabuSys

日本株向けのデータプラットフォーム & 自動売買リサーチ基盤ライブラリです。  
J-Quants / JPX からのデータ取得、ETL、データ品質チェック、ニュース NLP（LLM）によるセンチメント評価、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主な想定用途:
- 日次 ETL による株価・財務・マーケットカレンダーの更新
- ニュースを LLM でスコアリングして銘柄ごとの AI スコアを作成
- ETF / マクロを組み合わせた市場レジーム判定
- ファクター作成・IC 計算等のリサーチ
- 発注トレーサビリティ（監査ログ）用の DuckDB スキーマ初期化

---

## 特長 / 機能一覧

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分で取得・保存（ページネーション・レート制御・リトライ付き）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- データ品質
  - 欠損・スパイク・重複・日付不整合などの品質チェック機能
- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、URL 正規化、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメント（score_news）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定（score_regime）
- 研究（research）
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 を追跡する DuckDB スキーマ定義と初期化ユーティリティ
- 設定管理
  - .env / 環境変数による設定（自動ロード機能あり、プロジェクトルート検出）

---

## 動作要件 / 依存関係

- Python >= 3.10（PEP 604 の型注釈等を使用）
- 必須ライブラリ（一例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

（プロジェクトの requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   - 開発中は編集可能インストールが便利です:
     ```bash
     pip install -e .
     ```
   - 必要に応じて追加で:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注等）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用（任意）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — one of development / paper_trading / live
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL

   - .env の簡単な例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ・監査 DB の初期化（必要時）
   - 監査ログ用 DB の初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # or ":memory:"
     ```
   - 既存接続に監査スキーマを追加:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（簡単なコード例）

以下は主要な API の使い方例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- 日次 ETL の実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを作成（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"Wrote scores for {n_written} codes")
  ```

- 市場レジームを判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS を取得する（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

- 監査 DB の初期化（既出）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

注意点:
- OpenAI 呼び出しは外部 API を使用するため、API キーと課金設定が必要です。テスト時は内部の API 呼び出し関数をモックできます（各モジュール内に差し替えフックあり）。
- DuckDB の executemany は空リストを受け付けない箇所があるため、ライブラリは空チェックを行っています。使用時は接続に渡すテーブル定義が適切に作成されていることを確認してください。

---

## 設定の自動読み込みについて

- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を検出）を基に `.env` / `.env.local` を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数で:
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 必須環境変数が未設定の場合、Settings プロパティは ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。

---

## ディレクトリ構成（主要ファイルと概要）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM で解析して ai_scores テーブルに書き込む
    - regime_detector.py — ETF MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理・保存ヘルパ
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py — 品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py — z-score 等の統計ユーティリティ
    - audit.py — 監査ログ（発注→約定）スキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - (その他) strategy / execution / monitoring 等のパッケージが想定されている（__all__ に記載）

---

## よくあるトラブルシュート

- ValueError: 環境変数が設定されていません
  - settings のプロパティは必須変数が未設定のときに例外を投げます。`.env` を作成するか環境変数をエクスポートしてください。
- OpenAI API 呼び出しで失敗する
  - API キー設定（OPENAI_API_KEY）を確認。テストではモックを使用して API 呼び出しを差し替えてください。
- DuckDB にテーブルがない / executemany のエラー
  - ETL を実行する前にスキーマが正しく作成されているか確認してください。audit.init_audit_schema 等で監査テーブルを生成できます。

---

## 貢献 / 開発ヒント

- 自動環境読み込みはテストの邪魔になることがあるため、CI / テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- OpenAI 呼び出し周り・外部 API 呼び出しはモジュール内で差し替え可能（ユニットテストでは patch を活用）。
- DuckDB に依存するクエリは SQL 文面で分かりやすく記述しています。互換性のため executemany の扱いに注意してください。

---

必要であれば README に使用例（より詳細なコード片）、.env.example、あるいは開発用 Makefile / docker-compose の例を追加できます。どの情報がさらに必要か教えてください。