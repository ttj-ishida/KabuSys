# KabuSys

日本株向けの自動売買・データ基盤ライブラリセットです。  
データ取得（J-Quants）、ETL、ニュース収集・NLP、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム／研究基盤向けライブラリです。主に次を目的としています。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得と DuckDB への永続化（ETL）
- RSS によるニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント分析（銘柄別 ai_score、マクロセンチメント）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究ユーティリティ（forward returns / IC / summary）
- 監査ログ（signal → order_request → executions）のスキーマ初期化・管理
- データ品質チェック（欠損、スパイク、重複、日付整合性）

設計方針として、バックテストでのルックアヘッドバイアス回避、冪等な DB 書き込み、API リトライ／レート制御、フェイルセーフ（API 失敗時は局所的にスキップして継続）などが組み込まれています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - news_collector（RSS 取得、前処理、SSRF 対策、記事ID生成）
  - calendar_management（営業日判定、next/prev 等）
  - quality（品質チェック群）
  - audit（監査ログスキーマの初期化・専用 DB 初期化）
  - stats（zscore 正規化など）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores に保存）
  - regime_detector.score_regime（ETF とマクロセンチメントを合成して market_regime を作成）
- research/
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
- config.py
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`）と Settings クラス

---

## システム要件（推奨）

- Python 3.10+
- DuckDB
- openai (OpenAI SDK)
- defusedxml
- そのほか標準ライブラリのみで動作する箇所も多いですが、上記が主要依存です。

（実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／展開してパッケージをインストール（開発モード推奨）

   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要パッケージをインストール（例）

   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env の用意

   プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（起動時に OS 環境変数より下位で読み込み）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（主な一覧）:

   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視設定
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
   - KABUSYS_ENV: environment（development / paper_trading / live）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB 用ディレクトリの作成（必要に応じて）

   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下はライブラリを直接インポートして利用する最小例です。実行は Python スクリプトや REPL で行います。

- DuckDB 接続を開いて日次 ETL を実行する

  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を省略すると今日（ただしカレンダーで調整される）
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に書き込む

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # 環境変数 OPENAI_API_KEY を参照
  print(f"written {written} codes")
  ```

- 市場レジーム判定（regime）を計算する

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 19))
  ```

- 監査ログ（audit）用 DB の初期化

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit_duckdb.duckdb")
  # conn を使って order_requests 等の操作を行える
  ```

- J-Quants の ID トークンを取得する（デバッグ目的）

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  print(token)
  ```

注意点:
- AI 系（news_nlp / regime_detector）は OpenAI API キーが必要です。キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- ETL / J-Quants クライアントは J-Quants の API レート制限に従う実装（内部で待機）になっています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル・ディレクトリ構成（src 配下）:

- src/kabusys/
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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
    - ...（ファクター計算・探索）

トップレベルでは package の __all__ に ["data", "strategy", "execution", "monitoring"] が定義されています（strategy / execution / monitoring は本スニペットに含まれていないモジュールも想定）。

---

## 実運用上のポイント / 注意事項

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。
  - テストや明示的制御が必要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 読み込み順: OS 環境 > .env.local (override=True) > .env

- ルックアヘッドバイアス対策:
  - AI スコアやファクター計算では内部で datetime.today() を参照しないよう設計されています。必ず target_date を渡して過去データのみ参照する実装です。

- OpenAI 呼び出し:
  - レスポンスの JSON を厳密に期待しつつ、パース失敗や API エラーはフェイルセーフ（0.0 やスキップ）で処理を継続します。

- DuckDB について:
  - 一部の executemany は空リストが許容されないバージョンの回避ロジックを含んでいます。DuckDB バージョンに依存する挙動に注意してください。

---

## 開発・テストのヒント

- 各モジュールでは外部 API 呼び出し点を容易にモックできるよう設計されています（例: news_nlp._call_openai_api を patch してテスト可能）。
- 環境依存の自動読み込みを無効化してユニットテストを実行するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## 参考

ソース内 docstring に各モジュールの設計方針、処理フロー、引数説明が詳細に書かれています。新しいユースケースや拡張を行う際は該当モジュールの docstring をまず参照してください。

---

必要であれば、この README に次の内容を追加します:
- リリース手順 / バージョニングルール
- CI / CD の実行例
- 実運用時の監視・アラート設定例
- 具体的な .env.example（テンプレート）ファイル

どれを追加したいか教えてください。