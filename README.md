# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注/約定トレース）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築・運用するための共通基盤を提供します。主な機能は以下のカテゴリに分かれます。

- データ収集・ETL（J-Quants API 経由で株価・財務・市場カレンダーを取得し DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- ニュース収集（RSS）と NLP（OpenAI を利用した銘柄別センチメント）
- 市場レジーム判定（ETF の MA とマクロニュースセンチメントの合成）
- 研究用モジュール（ファクター計算、将来リターン、IC 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ：DuckDB ベース）
- 設定管理（.env の自動読み込み・環境変数ラッパ）

設計の共通方針として「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗は極力例外化せずフォールバック）」「DuckDB ベースの冪等保存」が重視されています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（認証、ページネーション、リトライ、レート制御）
  - fetch / save 関数：日足 (raw_prices), 財務 (raw_financials), market_calendar 等
- data/pipeline
  - run_daily_etl: カレンダー→株価→財務→品質チェックを順次実行する日次 ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- data/quality
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- data/news_collector
  - RSS フィードの安全な取得、前処理、raw_news への冪等保存補助
  - SSRF 対策、最大サイズ制限、トラッキングパラメータ除去等
- ai/news_nlp
  - 銘柄ごとのニュースをまとめて OpenAI に投げ、銘柄別センチメント（ai_scores）を作成
  - バッチ・リトライ・レスポンスバリデーション実装
- ai/regime_detector
  - ETF（1321）の 200 日移動平均乖離とマクロニュース LLM のスコアを合成し market_regime を生成
- research/*
  - calc_momentum, calc_value, calc_volatility 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary 等の解析ユーティリティ
- data/audit
  - signal_events / order_requests / executions を定義する監査テーブルの作成・初期化
- config
  - 環境変数ラッパー（.env 自動読み込み、必須値チェック、KABUSYS_ENV 判定等）

---

## 必須環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須: Slack 統合する場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須: 通知する場合）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注統合時）
- OPENAI_API_KEY — OpenAI を利用する場合に必要（news_nlp / regime_detector）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（省略時：development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

注意: 実行時には .env（または環境変数）で上記を設定してください。パッケージはプロジェクトルートの .env / .env.local を自動的に読み込みます（無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

---

## 前提（推奨）

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt があればそれを使用してください:
   - pip install -e . など

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

   自動ロードを無効化する場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベースの親ディレクトリ作成
   - mkdir -p data

---

## 使い方（例）

以下は Python スクリプトや REPL での利用例です。DuckDB 接続に対して各機能を呼び出します。

- 日次 ETL を実行する（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定しない場合は今日を基準に処理します
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント）を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OpenAI APIキーを環境変数で設定しておく（または api_key 引数で渡す）
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログデータベースの初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 order_requests / executions 等の操作に利用
  ```

注意: 上記の API 呼び出しは DuckDB 上に必要なテーブルスキーマが存在することを前提とします。スキーマ初期化用の別モジュール（例: data.schema）やマイグレーション手順がある場合はそれに従ってください。

---

## 自動環境変数読み込みについて

- パッケージ import 時に、プロジェクトルート（.git または pyproject.toml を検出）から `.env` と `.env.local` を自動的に読み込みます。
- 読み込み順序: OS環境変数 > .env.local > .env
- テストなどで自動ロードを無効化するには:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要モジュール / ディレクトリ構成

（主要なファイルと役割を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM ベースセンチメント付与（ai_scores へ書き込み）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save, retry, rate limit）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETL 型のエクスポート（ETLResult）
    - news_collector.py     — RSS 収集と前処理
    - calendar_management.py— 市場カレンダー管理（営業日ロジック）
    - quality.py            — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py              — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー等

---

## 設計上の注意点 / 制約

- DuckDB をデータストアとして使用します。ETL は基本的にローカル／単一ファイル DuckDB を想定しています。
- OpenAI（gpt-4o-mini 想定）へのコールはレスポンスのバリデーションとリトライを組んでいますが、APIキーはユーザー側で管理してください。
- Look-ahead バイアスに対して配慮した実装が施されています（内部で date.today() を盲目的に使わない、DB クエリは target_date 未満のデータのみ参照する等）。
- ETL の各ステップは独立してエラーハンドリングされ、1ステップ失敗でも他ステップは継続する設計です（実運用での停止条件は運用ポリシーに依存します）。
- news_collector は SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）などセキュリティ対策を実装しています。

---

## 貢献 / 追加導入

- 新しいデータソース、監査ログの拡張、発注ブローカー統合（kabuステーション等）は既存モジュールを拡張する形で追加できます。
- テスト用に環境変数自動読み込みを無効化 (`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`) してユニットテストを実行してください。
- OpenAI 呼び出しの部分はユニットテストでモック化されることを想定した設計です（内部関数を差し替え可能）。

---

README は以上です。必要であれば「導入例（docker-compose）」や「スキーマ初期化手順」「運用チェックリスト」などの追加セクションも作成します。どの情報を優先して追加しますか？