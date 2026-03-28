# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。本リポジトリはデータETL、ニュース収集・NLPによるセンチメント評価、市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「DuckDBベースのローカルデータストア」「外部API呼び出しに対する堅牢なリトライ・フェイルセーフ」です。

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数のチェック（settings オブジェクト）

- データプラットフォーム（data）
  - J-Quants API クライアント（取得・保存・ページネーション・認証リフレッシュ・レートリミット）
  - ETL パイプライン（run_daily_etl / 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news、SSRF/サイズ/トラッキング対策）
  - 監査ログ（signal_events / order_requests / executions テーブルの作成・初期化）

- AI（kabusys.ai）
  - ニュースNLP（gpt-4o-mini を用いたバッチセンチメント評価、ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントで日次レジーム判定、market_regime テーブルへ保存）

- リサーチ（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- ユーティリティ
  - DuckDB を使った冪等保存、トランザクション管理
  - ログ出力・警告・フェイルセーフ設計

---

## セットアップ手順

※プロジェクトに pyproject.toml / setup.py がある想定です。ない場合は PYTHONPATH を通すか、ローカルで直接 import してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   pip install -U pip
   ```

3. 必要パッケージをインストール
   最低限必要なライブラリ:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   プロジェクトにパッケージ設定があれば開発モードでインストール:
   ```
   pip install -e .
   ```

4. 環境変数（.env）を用意
   プロジェクトルートに `.env`（または `.env.local`）を作成すると自動読み込みされます。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...  # AI 機能を使う場合必須
   - DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
   - SQLITE_PATH=data/monitoring.db   # デフォルト
   - KABUSYS_ENV=development|paper_trading|live  # デフォルト: development
   - LOG_LEVEL=INFO|DEBUG|...  # デフォルト: INFO

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な利用例）

以下は Python から直接呼ぶ想定の最小例です。DuckDB 接続は duckdb.connect("path") を使用します。

- 日次 ETL 実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を指定しない場合は今日を使います
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db, init_audit_schema

  # ファイルベース DB を作る場合
  conn = init_audit_db("data/audit.duckdb")
  # 既存接続に追加する場合
  # conn = duckdb.connect("data/kabusys.duckdb")
  # init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, date(2026, 3, 20))
  v = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注意点:
- AI 機能（news_nlp / regime_detector）は OpenAI API を利用します。`OPENAI_API_KEY` を環境変数に設定するか、各関数の `api_key` 引数で渡してください。
- ETL / 保存処理は DuckDB のスキーマを前提とします。初回実行時はスキーマ作成やマイグレーションが必要な場合があります（スキーマ作成ユーティリティが別途提供されていることを想定）。

---

## 重要挙動・運用メモ

- .env 自動読み込み
  - ランタイム開始時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探し、`.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先され、`.env.local` は既存の OS 環境変数を保護しつつ上書きできます。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途など）。

- フェイルセーフ設計
  - AI API 呼び出しはリトライ・バックオフを実装しています。API 失敗時にはゼロスコアやスキップで継続するようフェイルセーフ設計です（例: マクロセンチメントの取得失敗は macro_sentiment = 0.0）。
  - ETL の各ステップは独立してエラーハンドリングされ、1ステップの失敗で全体が止まらないようになっています。結果は ETLResult.errors / quality_issues に格納されます。

- ルックアヘッドバイアス対策
  - 日付計算やDBクエリは target_date 未満 / 以前 といった条件を用いて外部時刻依存を避けるよう設計されています。内部で datetime.today() / date.today() を不用意に参照しない実装方針です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールです。プロジェクト全体は src レイアウトを想定しています。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLU / ai_scores 書込み
    - regime_detector.py     # 市場レジーム判定（ma200 + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETL インターフェース（ETLResult 再エクスポート）
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - news_collector.py      # RSS 収集・前処理・保存
    - audit.py               # 監査ログ（監査テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Value / Volatility 計算
    - feature_exploration.py # 将来リターン / IC / factor summary / rank

---

## 開発・貢献

- コードはロギングを活用しています。問題解析時は LOG_LEVEL を DEBUG に設定してください。
- テストを書く際は _call_openai_api やネットワーク層（jquants_client._request, news_collector._urlopen など）をモックすると容易です。
- DuckDB を使うため、スキーマ変更や大きなデータ操作はローカルでの十分な検証を行ってください。

---

必要に応じて README を拡張します（例: スキーマDDL、マイグレーション手順、CI / 実行スクリプト、具体的な .env.example ファイルのテンプレートなど）。どの情報を追加したいか教えてください。