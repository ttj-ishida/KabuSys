# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
本リポジトリは以下を主な目的として設計されています：J-Quants からのデータ ETL、ニュース収集と LLM を使ったニュースセンチメント評価、ファクター計算・特徴量探索、監査ログ（発注→約定トレーサビリティ）など。

---

## プロジェクト概要

- ETL（J-Quants API → DuckDB）を通じた株価・財務・カレンダー取得と品質チェック
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄別 / マクロ）評価
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索（将来リターン、IC 等）
- 監査ログ（signal → order_request → executions）のためのスキーマ定義・初期化
- 運用向けの設定管理（環境変数 / .env 自動ロード / ログレベル /閾値等）

主要な実装言語: Python  
主要なライブラリ（例）: duckdb, openai, defusedxml

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得 / 保存 / トークン自動リフレッシュ / レート制御）
  - カレンダー管理（営業日判定、次営業日/前営業日取得、calendar_update_job）
  - ニュース収集（RSS パース、前処理、SSRF 対策）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ（監査用テーブルDDL、init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - 銘柄ごとのニュースセンチメント算出（score_news）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
- research/
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

---

## セットアップ手順

前提:
- Python 3.10+（typing union 演算子等が使用されています）
- DuckDB, OpenAI SDK が必要
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン / 作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（ここでは例示）
   requirements.txt がある場合:
   ```bash
   pip install -r requirements.txt
   ```
   ない場合の例:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml を含む）に `.env` / `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で設定すると無効化可能）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news/score_regime のデフォルト）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注等を行う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を行う場合
   - オプション:
     - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例: `.env.example`
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベースディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（典型的な呼び出し例）

以下は Python スクリプトや REPL から利用する例です。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）スコア取得
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（マクロ + MA200）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーン設定が行われます
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), "銘柄のモメンタムを計算しました")
  ```

注意:
- score_news / score_regime は OpenAI API キー（引数 or 環境変数 OPENAI_API_KEY）を必要とします。
- ETL / データ保存は DuckDB スキーマ（raw_prices/raw_financials/market_calendar 等）に依存します。初回はスキーマ生成が必要な場合があります（本リポジトリの別モジュールで提供される想定）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ公開（version）
- config.py — 環境変数 / .env の読み込み・Settings（J-Quants / Kabu / Slack / DB / 監視設定）
- ai/
  - __init__.py
  - news_nlp.py — 銘柄別ニュース NLP スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（is_trading_day / next_trading_day 等）
  - etl.py — ETL 結果型のエクスポート（ETLResult）
  - pipeline.py — 日次 ETL 実装（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — 品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py — 監査ログスキーマ定義 / init_audit_db
  - jquants_client.py — J-Quants API クライアント（fetch/保存/認証/レート制御）
  - news_collector.py — RSS 収集・前処理・SSRF 対策
- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- research/*, ai/*, data/* の各モジュールは DuckDB 接続を引数に取り、Look-ahead bias を避けるよう設計されています（関数は date を明示的に受け取ります）。

---

## 設定と運用上の注意

- 環境変数自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込みします。テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV:
  - 有効値: development / paper_trading / live。live 環境では本番口座や発注処理等に対して追加チェックが必要です。
- ロギング:
  - 環境変数 `LOG_LEVEL` で調整します（デフォルト INFO）。
- OpenAI/外部 API の呼び出しはレートやエラーに対してリトライまたはフォールバック（スコア 0.0）を行う実装になっていますが、プロダクションでの運用時は API コスト・レートリミットに注意してください。
- DuckDB のバージョンに依存する細かな仕様（executemany の空リスト不可等）がコード内で扱われています。DuckDB のバージョン互換性に注意してください。

---

## 貢献・開発メモ

- テスト可能性: OpenAI 呼び出し部分やネットワーク I/O 部分はモック差し替えできるよう設計されています（ユニットテストでの patch を想定）。
- Look-ahead バイアス対策: 日付は明示引数を採用し、内部で date.today()/datetime.today() を参照しない設計方針です。バックテスト時は ETL で取得した historical データを利用してください。
- 安全対策: news_collector は SSRF、XML Bomb、巨大レスポンス対策（サイズ上限）等の防御を組み込んでいます。

---

もし README に追加したい内容（CLI 実行方法、CI/CD、より詳細な DB スキーマ、サンプル .env.example ファイルの自動生成手順 など）があれば教えてください。必要に応じて具体的なコマンド例やテンプレートを追記します。