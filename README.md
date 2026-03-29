# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集 / NLP スコアリング、研究用ファクター計算、および監査ログ（発注〜約定トレース）周りのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計されたモジュール群を含む Python パッケージです。

- J-Quants API からの株価・財務・カレンダーの差分取得（ETL）
- RSS からのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（ai_score）
- ETF を使った市場レジーム判定（MA + LLM）
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution）用のスキーマ初期化ユーティリティ

設計上の特徴:
- DuckDB を主なローカルデータストアとして使用
- Look-ahead bias を避ける設計（内部で datetime.today()/date.today() を安易に使わない）
- API 呼び出しに堅牢なリトライ・スロットリング・フェイルセーフ実装
- 冪等性を重視（DB 保存は ON CONFLICT / INSERT RETURNING 等で安全に）

---

## 機能一覧

主な機能（モジュール）と簡単な説明:

- kabusys.config
  - .env / 環境変数読み込み、設定オブジェクト（settings）を提供
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証・ページネーション・保存ユーティリティ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline (ETL)
  - run_daily_etl: 日次 ETL（calendar → prices → financials → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult データクラス
- kabusys.data.news_collector
  - RSS 取得、テキスト前処理、raw_news への冪等保存の想定ロジック
  - SSRF 対策、gzip サイズチェック、トラッキングパラメータ除去
- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行
- kabusys.data.audit
  - 監査用テーブル定義・初期化 (signal_events / order_requests / executions)
  - init_audit_schema / init_audit_db
- kabusys.data.calendar_management
  - 営業日判定・前後営業日取得・カレンダー更新ジョブ
- kabusys.ai.news_nlp
  - raw_news をまとめて OpenAI に渡し、各銘柄のセンチメントを ai_scores に書き込む（score_news）
  - バッチ・リトライ・レスポンス検証ロジックを含む
- kabusys.ai.regime_detector
  - ETF (1321) の 200 日 MA 乖離 + マクロニュース LLM を組み合わせて日次で market_regime を判定（score_regime）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索）

---

## 前提 / 必要環境

- Python 3.10+
  - 型ヒントに | を使っているため 3.10 以上を推奨
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）

（本プロジェクトは setup 配置に依存します。requirements.txt / pyproject.toml がある場合はそちらに従ってください）

---

## セットアップ手順

1. リポジトリをクローン、またはソースを配置
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトに pyproject.toml/requirements.txt があればそれを使用
     - pip install -e . など
4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（デフォルト）。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主に必要な環境変数:
     - JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
     - KABU_API_PASSWORD = <kabuステーション API パスワード>
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID （Slack 通知を使う場合）
     - OPENAI_API_KEY = <OpenAI API Key>（AI 機能を使う場合）
     - DUCKDB_PATH（省略時 data/kabusys.duckdb）
     - SQLITE_PATH（省略時 data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、省略時 development）
     - LOG_LEVEL（DEBUG / INFO / ...、省略時 INFO）
   - .env のパースはシェル風（export KEY=val やクォート、コメント）に対応しています

5. データベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（例）

以下は主要なユースケースのサンプルです。実行前に必要な環境変数（と OpenAI キー）が設定されていることを確認してください。

- DuckDB 接続の作成:

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は today）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai_scores へ書き込み）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジーム判定:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DB の初期化（監査専用 DB を別に持つ場合）:

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成されます
  ```

- 研究用ファクター計算の実行:

  ```python
  from datetime import date
  from kabusys.research import calc_momentum, zscore_normalize

  records = calc_momentum(conn, target_date=date(2026,3,20))
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意点:
- AI 関連処理（score_news, score_regime）は OpenAI API を呼び出します。API キーの管理と利用量に注意してください。
- モジュールは「ルックアヘッドバイアス」を避ける設計になっており、target_date を明示して実行することを推奨します。
- ETL は部分失敗を許容する設計です（各ステップは個別にエラーハンドリングされ、結果は ETLResult に集約されます）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 処理に必要）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

---

## ディレクトリ構成（主要ファイル）

（src 配下の kabusys パッケージ想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコアリング
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル初期化
    - stats.py — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラ / バリュー等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 開発・運用に関する注意

- ローカル / CI / 本番での環境変数の取り扱いに注意してください（.env の管理は適切に）。
- OpenAI や J-Quants などの外部 API 呼び出しは料金とレート制限があるため、実行頻度に注意してください。
- DuckDB は単一ファイル DB のため、バックアップ・排他制御（複数プロセス同時書き込み）を考慮してください。
- テスト時には環境変数の自動ロードを無効にするため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと便利です。
- モジュール内部で time やリトライ待機を行います。テストでは該当関数をモックして高速化してください。

---

README に記載のない詳細（スキーマ詳細、API の振る舞い、StrategyModel.md / DataPlatform.md に基づく設計仕様）はソース内の docstring / コメントを参照してください。必要であれば README に追記しますので、追加で欲しい内容（例: .env.example のサンプル、pyproject / requirements のテンプレート、具体的な SQL スキーマ抜粋 等）があれば教えてください。