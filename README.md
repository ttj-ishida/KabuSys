# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB を内部データベースとして利用し、J-Quants API 等から市場データ・財務・ニュースを取得して ETL → 特徴量生成 → シグナル生成までのパイプラインを提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐため「target_date 時点のデータのみ」を用いる実装
- DuckDB を用いた冪等的なデータ保存（ON CONFLICT / トランザクション）
- 外部 API 呼び出しに対するレート制御・リトライ・トークン自動更新
- ニュース収集では SSRF / XML BOM / Gzip bomb 等の安全対策を実装

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 自動読み込み（settings）
- J-Quants API クライアント
  - 日足株価（OHLCV）取得・保存
  - 財務データ取得・保存
  - マーケットカレンダー取得・保存
  - レートリミット・リトライ・トークンリフレッシュ対応
- DuckDB スキーマの初期化 / 接続管理
- ETL パイプライン（差分取得 / バックフィル / 品質チェック呼び出し）
- 特徴量（momentum / volatility / value 等）計算（research モジュール）
- Z スコア正規化ユーティリティ
- 特徴量の整備と features テーブルへの書き込み（strategy.feature_engineering）
- シグナル生成（final_score 計算・BUY/SELL 生成・signals テーブル保存）
- RSS フィードからのニュース収集および raw_news / news_symbols への保存（news_collector）
- マーケットカレンダー管理・営業日ユーティリティ
- 発注・監査・実行ログ用スキーマ（schema / audit）

---

## セットアップ手順

前提
- Python 3.10 以上
- ネットワークアクセス（J-Quants 等）およびローカルに書き込み可能なディレクトリ

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell なら .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール  
   プロジェクトに requirements.txt がない場合は最低限以下を入れてください（例）:
   ```
   pip install duckdb defusedxml
   # プロジェクトとしてインストールする場合
   pip install -e .
   ```
   （実運用では HTTP クライアントやロギング周りの依存を追記してください）

4. 環境変数の準備  
   プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）から自動で `.env` / `.env.local` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
   - SLACK_BOT_TOKEN = <Slack Bot Token>（通知等に使用）
   - SLACK_CHANNEL_ID = <Slack Channel ID>
   - KABU_API_PASSWORD = <kabu API パスワード>
   推奨（デフォルトあり）:
   - KABUSYS_ENV = development | paper_trading | live  (default: development)
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
   - DUCKDB_PATH = data/kabusys.duckdb (default)
   - SQLITE_PATH = data/monitoring.db (default)

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要ユースケース）

以下はライブラリ関数を直接呼ぶ基本例です。用途に合わせてスクリプトやジョブ（cron / Airflow 等）から呼び出してください。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # またはメモリDB
   # conn = schema.init_schema(":memory:")
   ```

2. 日次 ETL を実行（市場カレンダー・株価・財務を取得して保存）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   # conn: DuckDB 接続（init_schema で取得）
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量の構築（features テーブルへ保存）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date.today())
   print("features upserted:", count)
   ```

4. シグナル生成（signals テーブルへ保存）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print("signals written:", total_signals)
   ```

5. ニュース収集ジョブ（RSS → raw_news / news_symbols）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes: 銘柄抽出に使うコード集合（例: all listed codes）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
   print(results)  # {source_name: new_saved_count}
   ```

6. J-Quants からデータを直接取得して保存（単体）
   ```python
   from kabusys.data import jquants_client as jq
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   ```

デバッグやテスト時の小技
- 自動 .env 読み込みを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- テスト用に ID トークンを注入して API 呼び出しをテスト可能（jquants_client の関数は id_token を引数で受け取る）

---

## 推奨運用フロー（簡易）

1. 夜間バッチ（calendar_update_job / run_daily_etl）で市場カレンダー・株価・財務を更新
2. 特徴量構築ジョブ（build_features）を実行して features を更新
3. シグナル生成ジョブ（generate_signals）を実行して signals を更新
4. エグゼキューション層（未実装のbroker接続等）で signals を取り込み発注・約定処理を実行
5. 監査テーブルにイベントを保存してトレーサビリティを保持

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル / モジュール構成を示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py          — RSS 取得・解析・DB保存
    - schema.py                  — DuckDB スキーマ定義と init_schema()
    - stats.py                   — zscore_normalize 等ユーティリティ
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     — market_calendar 管理・営業日ユーティリティ
    - features.py                — data 側の特徴量公開インターフェース
    - audit.py                   — 監査ログ用スキーマ定義（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py         — momentum / volatility / value の計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py     — 生ファクターを正規化・合成して features に保存
    - signal_generator.py        — features + ai_scores から final_score を算出し signals を生成
  - execution/                    — 発注周り（パッケージ構成のみ。実実装は別途）
  - monitoring/                   — 監視・メトリクス（構成想定）
- pyproject.toml / setup.cfg 等（プロジェクトルート想定）
- .env.example（テンプレート想定）

（上記はコード内ドキュメントを元に抜粋した要約です。実ファイル一覧はリポジトリのツリーを参照してください。）

---

## 実装上の注意点 / 備考

- DuckDB のスキーマは init_schema() で冪等的に作成されます。初回起動時は必ず実行してください。
- J-Quants API の rate limit（120 req/min）に合わせた RateLimiter とリトライ実装が組み込まれています。大量バッチを組む場合は十分な間隔設定を行ってください。
- news_collector は外部から取り込む RSS を安全に処理するため、XML 脆弱性・SSRF・受信サイズ制限などの対策が施されていますが、運用時は取得先の管理（ホワイトリスト化等）を行ってください。
- strategy 層は execution 層への直接依存を持たない設計です。発注ロジックは execution 層（broker 接続）で実装して取り込みます。
- settings は .env / .env.local をプロジェクトルートから自動読み込みします。CI やユニットテストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 単体テストを容易にするため、関数の多くは接続オブジェクトや id_token などを引数で受け取れるように設計されています。

---

README に記載したサンプルはライブラリ関数の呼び出し例です。運用環境では例外処理・ロギング・監視・リトライポリシーを適切に組み合わせてジョブ化してください。必要ならば運用手順（cron / systemd / Airflow / Kubernetes CronJob）用のサンプルも用意できます。要望があれば教えてください。