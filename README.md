# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J-Quants API からのデータ取得、DuckDB ベースのデータスキーマ、特徴量生成・シグナル生成、ニュース収集、マーケットカレンダー管理、ETL パイプライン等を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を明確に分離した日本株自動売買システム用のライブラリ群です。

- データ層: J-Quants からの生データ取得（株価・財務・カレンダー）、DuckDB による永続化（raw / processed / feature / execution 層）。
- ETL: 差分更新・バックフィル・品質チェックを備えた日次 ETL パイプライン。
- リサーチ: 将来リターン計算、IC（情報係数）・ファクター統計などの研究用ユーティリティ。
- 戦略: ファクターの正規化・合成（feature_engineering）および正規化済み特徴量＋AIスコア統合によるシグナル生成（signal_generator）。
- ニュース: RSS 取得・前処理・記事保存と銘柄抽出（news_collector）。
- カレンダー管理: JPX マーケットカレンダーの取得と営業日判定。
- 監査・実行ログ: 発注／約定／ポジションなどの監査テーブル群。

設計上のポイント:
- ルックアヘッドバイアスを避けるため「target_date 時点のデータのみ」を用いる設計。
- DuckDB を中心とした冪等（idempotent）な保存（ON CONFLICT を利用）。
- 外部 API 呼び出し等は data 層で集中管理し、strategy 層は発注 API へ依存しない。

---

## 主な機能一覧

- J-Quants API クライアント（レート制限・リトライ・自動トークンリフレッシュ対応）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
- データスキーマ初期化 / 接続
  - init_schema, get_connection（DuckDB）
- ETL パイプライン
  - run_daily_etl（カレンダー・株価・財務の差分更新 + 品質チェック）
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
- ニュース収集
  - fetch_rss, save_raw_news, run_news_collection（SSRF 対策・XML セーフパース・トラッキング除去）
  - 銘柄抽出（テキストから 4 桁の銘柄コード抽出）
- リサーチ / ファクター計算
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- 特徴量エンジニアリング
  - build_features（Z スコア正規化・ユニバースフィルタ・日次 UPSERT）
- シグナル生成
  - generate_signals（複数コンポーネントの重み付け合算、Bear レジーム考慮、BUY/SELL 判定）
- マーケットカレンダー管理
  - calendar_update_job, is_trading_day, next_trading_day, prev_trading_day, get_trading_days
- 監査（audit）テーブル群の初期化

---

## 要件

- Python 3.10 以上（型ヒントに | 演算子を使用）
- 必須外部パッケージ（最小）
  - duckdb
  - defusedxml
- （運用時）J-Quants API のアクセス用トークン等の環境変数（下記参照）。

プロジェクトの依存は環境や配布方法に応じて requirements.txt / pyproject.toml を用いて管理してください。

---

## 環境変数（必須 / 任意）

このパッケージは .env（プロジェクトルート）や OS 環境変数を読み込みます（自動読み込みはデフォルトで有効）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings で _require によって取得されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注層で使用）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知を利用する場合）
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）
- KABUSYS_API_BASE_URL / KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

.env のパースは shell 風の形式に対応（`export KEY=val`、クォート、コメント処理など）。プロジェクトルートの `.git` または `pyproject.toml` を基に自動検出します。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）
   - pip install -e .  （パッケージとして編集インストールする場合）

4. 環境変数設定
   - プロジェクトルートに `.env` を作成して上記必須変数を設定するか、OS 環境変数として設定してください。

5. DuckDB スキーマ初期化
   - Python コンソールやスクリプトで以下を実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # デフォルトパスと一致
     ```

---

## 使い方（主要な API とサンプル）

以下は典型的な利用パターンの例です。実運用では各呼び出しをジョブ（cron / Airflow / dbt 等）として組み合わせます。

- DuckDB を初期化して接続取得
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー取得 → 株価差分 → 財務差分 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date(2025, 1, 10))
  print(f"built features: {count}")
  ```

- シグナル生成（features と ai_scores を参照して signals テーブルへ書き込み）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  n_signals = generate_signals(conn, target_date=date(2025, 1, 10))
  print(f"signals written: {n_signals}")
  ```

- ニュース収集（RSS から raw_news へ保存、既知銘柄との紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄リスト
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(res)
  ```

- マーケットカレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)
  ```

- J-Quants のデータを直接フェッチして保存する（テストや個別更新）
  ```python
  from kabusys.data import jquants_client as jq
  # 例: 直近の株価を取得して保存
  recs = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,10))
  saved = jq.save_daily_quotes(conn, recs)
  ```

---

## ディレクトリ構成

主要なファイル/モジュールを抜粋しています（src レイアウト）。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント（取得・保存）
      - news_collector.py       — RSS ニュース収集・前処理・保存
      - schema.py               — DuckDB スキーマ定義と init_schema
      - stats.py                — 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py             — ETL パイプライン（run_daily_etl 等）
      - features.py             — data 層の特徴量ユーティリティ公開
      - calendar_management.py  — JPX カレンダー管理 / 更新ジョブ
      - audit.py                — 監査ログ（signal_events / order_requests / executions 等）
      - (その他)                — quality 等（品質チェックモジュールがある前提）
    - research/
      - __init__.py
      - factor_research.py      — ファクター計算（momentum / value / volatility）
      - feature_exploration.py  — 将来リターン・IC・統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py  — features テーブル作成（正規化・ユニバース）
      - signal_generator.py     — final_score 計算と BUY/SELL シグナル生成
    - execution/                — 発注 / execution 層（パッケージ化済み、実装は別にある想定）
    - monitoring/               — 監視・メトリクス（空の __all__ 等）

この README の内容はコード内の docstring / モジュールコメントに基づき要約しています。各モジュールの詳細は該当ファイルの docstring を参照してください。

---

## 運用上の注意点

- DuckDB のファイルパスは設定 `DUCKDB_PATH` で変更可能。複数プロセスから同一ファイルへ同時書き込みする場合は運用設計（ロックや単一 ETL ホスト）に注意してください。
- J-Quants のレート制限（120 req/min）に対応する RateLimiter が組み込まれています。大量の銘柄を短期間にフェッチする際は API 制限に注意してください。
- ニュース取得は外部 HTTP を行うため、SSRF や大容量レスポンスに対する防御（ホストチェック、サイズ上限、gzip 解凍後サイズ検査）を備えていますが、運用環境のネットワークポリシーと合わせて確認してください。
- 実口座での運用は法的・リスク面の検討が必要です。`KABUSYS_ENV` を適切に設定（paper_trading / live）してください。
- .env の自動ロードはソースルート検出に .git もしくは pyproject.toml を使います。パッケージ配布後に挙動を変えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境変数を注入してください。

---

もし README に追加したい「具体的な実行スクリプト」「CI 設定」「サンプル .env.example」や「テスト実行方法」などの情報があれば教えてください。必要に応じて追記・テンプレート化します。