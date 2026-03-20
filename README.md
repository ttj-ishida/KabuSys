# KabuSys

日本株向けの自動売買・データプラットフォームコンポーネント群です。  
J-Quants から市場データ・財務データ・カレンダーを取得して DuckDB に蓄積し、研究用ファクターの計算、特徴量の正規化、戦略シグナル生成、ニュース収集、監査ログ用スキーマなどを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（レート制御・リトライ・トークン自動リフレッシュ）
  - 差分取得／バックフィル／品質チェックを備えた日次 ETL パイプライン
- データ格納
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - 冪等性を考慮した保存（ON CONFLICT 相当の更新）
- 研究・特徴量
  - Momentum / Volatility / Value などのファクター計算（prices_daily / raw_financials を参照）
  - クロスセクションの Z スコア正規化ユーティリティ
  - 研究向けの将来リターン、IC（Information Coefficient）計算、統計サマリ
- 戦略
  - 正規化済み特徴量と AI スコアを統合して final_score を計算し、BUY/SELL シグナルを生成（Bear レジーム抑制、エグジット判定等）
- ニュース収集
  - RSS フィードから記事を取得・前処理して raw_news に保存、記事と銘柄コードの紐付け
  - SSRF 対策、gzip サイズ上限、XML パース防御など堅牢性を考慮
- カレンダー管理
  - JPX カレンダーの差分更新と営業日判定ユーティリティ（next_trading_day / prev_trading_day / get_trading_days 等）
- 監査・トレーサビリティ
  - シグナル → 発注 → 約定 に至る監査テーブル群（order_request の冪等キー等）

---

## 前提・要件

- Python >= 3.10（型アノテーションとユニオン演算子 `|` を利用）
- 必要なパッケージ（抜粋）
  - duckdb
  - defusedxml
- J-Quants API のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）
- （運用）kabuステーション API パスワード 等

環境に応じて他のライブラリが必要になることがあります。開発用には pyproject.toml / requirements.txt を用意している想定です。

---

## 環境変数（主要）

このパッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先、必要に応じて上書き）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須・推奨）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例（プロジェクトルートの `.env`）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン（またはソースを配置）してプロジェクトルートへ移動
2. Python 環境を用意（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）
4. 環境変数を設定（.env を作成）
5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - これで data/kabusys.duckdb（または指定パス）が作成され、全テーブルが初期化されます。

---

## 使い方（主要 API と実行例）

以下は代表的な利用フローとコード例です。実行は任意のスクリプトやジョブから呼び出してください。

- ETL（日次パイプライン）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を省略すると今日（営業日に調整）
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection('data/kabusys.duckdb')
  n = build_features(conn, date(2024, 1, 10))
  print(f"built features: {n}")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection('data/kabusys.duckdb')
  total = generate_signals(conn, date(2024, 1, 10))
  print(f"signals generated: {total}")
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection('data/kabusys.duckdb')
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection('data/kabusys.duckdb')
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants クライアントを直接使ってデータ取得（テストやバックフィル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection
  from kabusys.config import settings
  from datetime import date

  conn = get_connection(settings.duckdb_path)
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print(saved)
  ```

---

## 開発時のヒント

- 自動 .env 読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env`/.env.local を自動読み込みします。
  - テストや一時的に無効化したいときは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト向け DB:
  - インメモリ DuckDB を使うには `db_path=":memory:"` を init_schema に渡すと便利です。
- ロギング:
  - settings.log_level で制御します（環境変数 LOG_LEVEL）。
- 実行モード:
  - KABUSYS_ENV により環境（development, paper_trading, live）を切り替え可能。ライブ運用時は保護設定や外部 API の接続先に注意してください。

---

## ディレクトリ構成

src/kabusys 配下の主要ファイルとディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — カレンダー更新・営業日ユーティリティ
    - audit.py               — 監査ログ用スキーマ（signal_events, order_requests 等）
    - features.py            — data API（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features の計算・正規化・保存
    - signal_generator.py    — final_score 計算と signals テーブル生成
  - execution/               — 発注/実行系（現状空のパッケージ）
  - monitoring/              — 監視用コード（未展開）
- pyproject.toml または setup.py（存在すればパッケージインストール用）

---

## 注意点・設計上の制約

- ルックアヘッドバイアス防止のため、各モジュールは target_date 時点の情報のみを参照するよう設計されています。
- DuckDB のバージョン差異による制約（外部キーの ON DELETE 動作など）を想定した実装・コメントがあります。
- J-Quants API のレート制限やリトライロジックは組み込まれていますが、実運用では適宜監視・テストを行ってください。
- 実売買（live）モードでは外部ブローカー接続や実行層の十分な検証が必要です（kabuステーション連携等）。

---

もし README に追加したい内容（例: CI 実行手順、サンプル .env.example、より具体的なデプロイ手順、ユニットテストの実行方法など）があれば教えてください。必要に応じて追記します。