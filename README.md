# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP、ファクター計算、研究ユーティリティ、監査ログ、J-Quants / kabu関連クライアントなど、トレーディングシステムに必要な機能をモジュール化して提供します。

主な設計方針：
- Look‑ahead bias の防止（date の参照を明示的に受け取る設計）
- DuckDB を中心としたローカルデータベース運用
- OpenAI（gpt-4o-mini）によるニュースセンチメント評価（冗長化・リトライ等の堅牢化）
- ETL / 品質チェック / 監査ログの冪等性（再実行安全）重視

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 自動読み込み・管理（kabusys.config）
  - プロジェクトルートの .env / .env.local を自動読み込み（無効化可）
  - 必須値取得ユーティリティ
- データ ETL（kabusys.data.pipeline）
  - J-Quants からの差分取得（株価・財務・カレンダー）
  - 保存（DuckDB）と品質チェック（kabusys.data.quality）
  - 日次 ETL の統合エントリポイント
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レートリミット管理、トークン自動更新、ページネーション対応
  - raw_prices / raw_financials / market_calendar への保存関数（冪等）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日取得、夜間バッチ更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、SSRF 対策、前処理、raw_news 保存
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック、QualityIssue レポート
- 監査ログ（kabusys.data.audit）
  - signal / order_request / execution の監査テーブル初期化・管理
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算 (momentum / volatility / value)
  - 将来リターン計算、IC（情報係数）、統計サマリ、Z-score 正規化
- AI ベース NLP（kabusys.ai）
  - score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースを合成して市場レジーム判定
  - 両モジュールとも OpenAI 呼び出しに堅牢なリトライ・フォールバック実装あり

---

## 必要な環境変数（主なもの）

以下はアプリケーション内で参照される主要な環境変数です。実行に必要なものは使用する機能によります。

必須（機能を使う場合）：
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（ETL / jquants_client）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系機能）

任意 / デフォルトあり：
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に 1 を設定
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（未設定時は空文字）
- DUCKDB_PATH — データベースファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値（CPU/MEMORY/DISK）

.env の読み込み順:
- OS 環境変数 > .env.local > .env（プロジェクトルートを自動検出。.git または pyproject.toml を基準）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-dir>

2. Python 仮想環境を作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（最低限の例）:
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使ってください。）
   開発用に:
   pip install -e .

4. .env を用意:
   プロジェクトルートに `.env` （および必要なら `.env.local`）を作成し、上記の必須変数をセットしてください。
   例:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb

   自動読み込みを無効化する場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成:
   mkdir -p data

---

## 使い方（主要な例）

以下は Python スクリプトや REPL からの利用例です。

- DuckDB 接続を作る（設定の DUCKDB_PATH を利用）:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に保存:
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> 環境変数 OPENAI_API_KEY を使用
  print(f"書き込み銘柄数: {count}")

- 市場レジーム判定（regime）を計算:
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算:
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  m = calc_momentum(conn, date(2026, 3, 20))
  v = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

- 監査 DB を初期化（独立 DB を利用したい場合）:
  from pathlib import Path
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db(Path("data/audit.duckdb"))

注意点:
- AI 系関数は OpenAI API 呼び出しを行うため、API キーと料金を確認してください。
- ETL / API 呼び出しにはネットワークと十分な権限（J-Quants トークンなど）が必要です。
- 多くの関数は Look‑ahead を避けるため target_date を明示的に受け取ります。内部で date.today() を使わない設計です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数・.env 読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント評価 / score_news
  - regime_detector.py           — マーケットレジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch / save）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult の再公開
  - calendar_management.py       — マーケットカレンダー管理 / calendar_update_job
  - news_collector.py            — RSS 取得・前処理・保存
  - quality.py                   — データ品質チェック（QualityIssue）
  - stats.py                     — zscore_normalize 等の統計ユーティリティ
  - audit.py                     — 監査ログ（DDL 定義・初期化）
- research/
  - __init__.py
  - factor_research.py           — Momentum / Value / Volatility ファクター計算
  - feature_exploration.py       — 将来リターン / IC / 統計サマリ / rank
- monitoring/ (存在する可能性のあるモジュール)...
- execution/, strategy/ (戦略・発注層は別ディレクトリに実装想定)

---

## 実運用上の注意と設計メモ

- 冪等性: ETL・保存関数（save_*）は ON CONFLICT を利用して再実行可能な設計です。
- レート制御: J-Quants クライアントは 120 req/min の制限に合わせた RateLimiter を実装しています。
- フェイルセーフ: AI 呼び出し失敗時は 0.0 を返す等、主要ワークフローを停止させない設計が入っています（ログで通知）。
- セキュリティ: news_collector は SSRF 対策（ホスト種別チェック・リダイレクト検査）、defusedxml を利用した XML パースを行います。
- 時刻管理: 監査ログは UTC を前提（init_audit_schema は TimeZone を UTC に固定します）。raw_news.datetime は UTC に変換して格納します。
- テスト性: OpenAI の API 呼び出しは内部で差し替え可能にしてあり、テスト時はモックで代替できます。

---

もし README に追記したい点（CI / デプロイ手順、テストコマンド、サンプル .env.example の具体値など）があれば教えてください。必要に応じて実行例や CLI スクリプトの雛形も作成します。