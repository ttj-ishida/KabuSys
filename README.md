# KabuSys

日本株向けのデータプラットフォーム兼リサーチ / 自動売買補助ライブラリです。  
データ取り込み（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、ETL、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の責務を想定したライブラリです。

- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と前処理、記事→銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 ai_score）評価
- ETF（1321）を使った市場レジーム判定（MA200 とマクロニュース合成）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）や特徴量探索ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント:
- ルックアヘッドバイアス回避（内部処理で現在時刻を直接参照しない等）
- 冪等性（DB 保存は ON CONFLICT / DO UPDATE を利用）
- フェイルセーフ（API 失敗時は安全側にフォールバックして継続）
- テスト容易性（API 呼び出し箇所を差し替え可能）

---

## 機能一覧

主なモジュール（概要）:

- kabusys.config
  - .env / 環境変数管理、デフォルト値、必須キー取得ヘルパー
  - 自動ロード: プロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数、トークンリフレッシュ、レート制御）
  - pipeline: 日次 ETL（run_daily_etl）や個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS 収集、前処理、安全対策（SSRF 防止 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログスキーマの初期化・DB 作成（init_audit_schema / init_audit_db）
  - stats: z-score 正規化
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとニュースを集約して OpenAI でセンチメント評価 → ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA200 とマクロニュースを合成して market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提: Python 3.10+ を想定（型ヒントに union 型などを使用）。実環境の Python バージョンに合わせてください。

1. リポジトリをクローン / コピー

2. 仮想環境作成（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージのインストール（最低限の例）
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトに requirements.txt があればそれを使ってください。上記はコード内で参照される主要ライブラリ例です（urllib 等は標準ライブラリ）。

4. パッケージを開発モードでインストール（オプション）
   ```
   pip install -e .
   ```

5. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）: J-Quants リフレッシュトークン
   - OPENAI_API_KEY（OpenAI を使う場合に必要）
   - KABU_API_PASSWORD（kabuステーション API を使う場合）
   - SLACK_BOT_TOKEN（Slack 通知を使う場合）
   - SLACK_CHANNEL_ID
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用 sqlite、デフォルト: data/monitoring.db）
   - PID_FILE_PATH（実行監視用、デフォルト: data/execution.pid）
   - KABUSYS_ENV（development / paper_trading / live）
   - LOG_LEVEL（DEBUG/INFO/...）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

下例は Python スクリプトや REPL から利用するケース。

- DuckDB 接続を作り ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント評価（OpenAI が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  num_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("written:", num_written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- J-Quants から株価を直接取得（ユーティリティ）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=..., date_to=..., id_token=None)  # トークンはモジュールで処理
  save_count = save_daily_quotes(conn, recs)
  ```

注意:
- OpenAI 呼び出しは料金が発生します。API キー・料金体系を確認してください。
- J-Quants API 利用にはトークンが必要です（refresh token を .env に設定）。

---

## 自動 .env 読み込みの挙動

- kabusys.config モジュールはパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、以下順で .env を読み込みます:
  - OS 環境変数（既存のものは保護）
  - .env（override=False）
  - .env.local（override=True、.env を上書き可）
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの集約・OpenAI 呼び出し・ai_scores 書込
    - regime_detector.py     # MA200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETLResult 再エクスポート
    - news_collector.py     # RSS 取得・前処理・保存
    - calendar_management.py# 市場カレンダー / 営業日ユーティリティ
    - quality.py            # 品質チェック
    - stats.py              # zscore_normalize 等
    - audit.py              # 監査ログスキーマ初期化・DB 作成
  - research/
    - __init__.py
    - factor_research.py    # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py# calc_forward_returns, calc_ic, factor_summary, rank
  - ai/, data/, research/  # 上記のサブパッケージ

（実際のリポジトリにより細かいファイルが追加されている場合があります。）

---

## 注意事項 / 運用上のメモ

- OpenAI / J-Quants の API 呼び出しはリトライやバックオフを実装していますが、利用制限やコストに注意してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、該当箇所では空確認を行っています。
- 監査スキーマは削除しない運用を前提としています（ON DELETE RESTRICT）。
- 本ライブラリはバックテストや実運用でのルックアヘッドバイアスを避ける設計になっていますが、呼び出し側でもデータ準備や target_date の扱いに注意してください。

---

## サポート / 開発

- 開発時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを抑止するとテストが安定します。
- OpenAI 呼び出しや外部 API 呼び出し部分は unittest.mock.patch 等で差し替えてテスト可能に実装されています（コード内に差し替え用の参照コメントあり）。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt、あるいは CLI 実行例（cron / systemd 用の起動例や監視の説明）を追記します。追加で欲しい情報があれば教えてください。