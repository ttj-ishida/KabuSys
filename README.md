# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群で構成されています。

---

## 概要（Project Overview）

KabuSys は日本株の自動売買システム構築を支援するライブラリです。  
主に次を目的とします：

- J-Quants API からの株価／財務／カレンダー取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と OpenAI を使ったニュースセンチメントのスコアリング
- マーケットレジーム判定（ETF MA とマクロニュース混成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order → execution のトレーサビリティ）
- kabuステーション連携用設定（実行/検証モードの区別等）

このリポジトリは src/kabusys 以下に Python モジュールとして実装されています。

---

## 機能一覧（Features）

- データ収集・ETL
  - J-Quants から株価（daily_quotes）、財務（statements）、JPX カレンダーを差分取得
  - DuckDB に冪等保存（ON CONFLICT DO UPDATE）
  - ETL の結果を ETLResult として取得
- データ品質チェック
  - 欠損値（OHLC 欠損）、スパイク（前日比閾値）、重複、日付不整合の検出
- ニュース処理・NLP
  - RSS フィードの収集（ssrf 対策、gzip チェック、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメントスコア化（ai_scores）
  - マクロニュースを用いた市場レジーム判定（regime_detector）
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート判定）と Settings API

---

## 必要条件（Prerequisites）

- Python 3.9+（型アノテーションに Path 型等を多用）
- DuckDB（Python パッケージ：duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全対策）
- ネットワークアクセス（J-Quants / OpenAI 等）

パッケージ例（最低限）:
```
pip install duckdb openai defusedxml
```

（プロジェクト側で requirements.txt があればそちらを利用してください）

---

## セットアップ手順（Setup）

1. リポジトリをチェックアウトし、仮想環境を作成・有効化します。

    ```
    python -m venv .venv
    source .venv/bin/activate  # macOS / Linux
    .venv\Scripts\activate     # Windows
    ```

2. 必要パッケージをインストールします（プロジェクトの requirements.txt があればそちらを使用）。

    ```
    pip install duckdb openai defusedxml
    ```

3. 環境変数を設定します。プロジェクトルートに `.env`（または `.env.local`）を置けば自動で読み込まれます（読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

    必須の環境変数（Settings で参照されるもの）:
    - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
    - KABU_API_PASSWORD — kabu ステーション API パスワード
    - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
    - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
    - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

    任意／デフォルト:
    - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
    - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
    - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
    - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

    例 `.env`:
    ```
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C12345678
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    DUCKDB_PATH=data/kabusys.duckdb
    ```

4. DuckDB のデータディレクトリを準備します（必要に応じて）。

    ```
    mkdir -p data
    ```

---

## 使い方（Usage）

以下は主要なユースケースの最小例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

- 日次 ETL を実行する（run_daily_etl）

    ```python
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュースの NLP（score_news）を実行する

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY は環境変数で指定するか、第二引数に api_key を渡す
    count = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {count} codes")
    ```

- 市場レジーム判定（score_regime）

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))
    ```

- 監査ログ用データベースを初期化する

    ```python
    import duckdb
    from kabusys.data.audit import init_audit_db

    # ":memory:" でインメモリ DB、またはパスを指定
    audit_conn = init_audit_db("data/audit.duckdb")
    ```

- カレンダー更新ジョブを単体で実行する

    ```python
    from datetime import date
    import duckdb
    from kabusys.data.calendar_management import calendar_update_job

    conn = duckdb.connect("data/kabusys.duckdb")
    saved = calendar_update_job(conn, lookahead_days=90)
    print("saved", saved)
    ```

注意点：
- AI モジュール（news_nlp, regime_detector）は OpenAI API（gpt-4o-mini）を使用するため、OPENAI_API_KEY の設定が必要です。API 呼び出し失敗時はフェイルセーフで 0.0 スコアにフォールバックする実装になっていますが、API キーが未設定だと ValueError が発生します。
- J-Quants クライアントは JQUANTS_REFRESH_TOKEN を利用して id_token を取得します。

---

## 開発・テスト時の補助

- 自動で .env を読み込む機能を無効にする（テストなど）:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```
- OpenAI や J-Quants への実ネットワーク呼び出しをテストで置き換える場合、モジュール内の _call_openai_api や _urlopen などを unittest.mock.patch で差し替える設計になっています。

---

## 設定可能な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー
- KABU_API_PASSWORD (必須) — kabu API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ユニットログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読込を無効化するフラグ（値を設定すると無効化）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 内の主要なモジュールとその概要です。

- src/kabusys/
  - __init__.py — パッケージエントリ（__version__ 等）
  - config.py — .env / 環境変数の自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの OpenAI による銘柄ごとのセンチメントスコア化
    - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日判定・更新ジョブ
    - pipeline.py — ETL の主要処理（run_daily_etl / run_prices_etl / ...）
    - etl.py — ETLResult の再エクスポート
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ（DDL、初期化ユーティリティ）
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py — RSS フィードの収集・正規化・raw_news 保存ロジック
  - research/
    - __init__.py
    - factor_research.py — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

（各ファイルの README 相当の docstring は内部に詳しく記載されています）

---

## 注意事項 / 補足

- ルックアヘッドバイアス対策が至る所に組み込まれており、内部実装は target_date に対して過去データのみ参照するよう設計されています。バックテスト用途でも使用できますが、データの準備（バックテスト期間以前のデータ取得）には注意してください。
- J-Quants API のレート制限や OpenAI の API 料金に注意してください。実行前に API キーやトークンの権限・利用制限を把握してください。
- news_collector では SSRF / XML Bomb / 大容量応答の保護を実装していますが、運用時は収集ソースの管理を必ず行ってください。

---

必要であれば、README に含めるコマンド例や追加のセットアップ（systemd / Airflow 等での定期実行サンプル）、より詳細な API 使用例（引数、戻り値の例）を追記します。どの情報を追加したいか教えてください。