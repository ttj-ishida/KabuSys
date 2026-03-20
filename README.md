# KabuSys

KabuSys は日本株の自動売買に必要なデータ収集・ETL・特徴量生成・シグナル生成・監査ログを備えたライブラリ群です。DuckDB を内部データベースとして利用し、J-Quants API や RSS ニュースからデータを取得して戦略層へ供給することを目的としています。

本 README はプロジェクトの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

- データ収集:
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを取得（差分取得、ページネーション対応、リトライ・レート制御）。
  - RSS フィードからニュース記事を収集し raw_news に保存（URL 正規化、SSRF 対策、XML 脆弱性対策）。
- ETL / データ基盤:
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）。
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）。
- 研究・特徴量:
  - research 用モジュールで momentum / volatility / value などのファクター算出。
  - クロスセクション Z スコア正規化ユーティリティ。
- 戦略:
  - 特徴量の正規化・マージ → features テーブルへの保存（冪等）。
  - features と AI スコアを統合して final_score を計算し buy/sell シグナルを生成して signals テーブルへ保存（冪等）。
- 監査:
  - シグナルから発注、約定までトレース可能な監査テーブルを定義（order_request_id 等の冪等キーを含む）。

---

## 主な機能一覧

- 環境設定の自動読み込み（.env / .env.local をプロジェクトルートから自動読み込み、必要に応じて無効化可）
- DuckDB スキーマの初期化（init_schema）
- J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
- ETL パイプライン（run_daily_etl）
- ニュース収集（RSS → raw_news、記事IDは正規化 URL の SHA256 ベース）
- ファクター計算（calc_momentum / calc_volatility / calc_value）
- 特徴量構築（build_features）
- シグナル生成（generate_signals）
- カレンダー管理（営業日判定、next/prev_trading_day など）
- 統計ユーティリティ（zscore_normalize、IC / factor summary / rank）

---

## 要求環境・依存関係

- Python 3.10 以上（PEP 604 の型記法などを使用しています）
- 必要な Python パッケージ（主に動作に必須なもの）
  - duckdb
  - defusedxml

（プロジェクト内で別の外部クライアントを使う場合は追加でその SDK が必要になる可能性があります）

例: pip によるインストール
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。自動読み込みが有効であれば、KabuSys 起動時にこれらを読み込みます（必要に応じて環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - オプション：
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）

   例 .env の一部:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトから次を実行して DB を初期化します。
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # またはメモリDB: init_schema(":memory:")
   conn.close()
   ```

---

## 使い方 — 主要な例

下記は代表的な利用例です。すべて DuckDB 接続を渡す形で動作します。

1) 日次 ETL の実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

2) 特徴量の生成（build_features）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from datetime import date
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2026, 1, 31))
print(f"features upserted: {count}")
conn.close()
```

3) シグナル生成（generate_signals）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from datetime import date
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = generate_signals(conn, target_date=date(2026, 1, 31), threshold=0.60)
print(f"signals written: {n}")
conn.close()
```

4) ニュース収集ジョブ（RSS → raw_news、銘柄紐付け含む）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードの集合（例）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

注意:
- 各処理は基本的に「冪等（idempotent）」に設計されています（ON CONFLICT 等で重複を排除）。
- 実運用（live）では settings.is_live を利用してリスク制御や実際の発注フローを切り替えてください。

---

## 環境変数・設定

主な設定は kabusys.config.Settings で取得します。重要な項目は以下の通りです。

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_BASE_URL（kabu API のベース URL、デフォルト: http://localhost:18080/kabusapi）
  - KABU_API_PASSWORD（必須）
- Slack
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
- データベース
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
- システム
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: INFO / DEBUG / ...

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env/.env.local の自動読み込みをスキップします（テスト用）。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要モジュールと役割の要約です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理・設定読み込み（Settings）
  - data/
    - __init__.py
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py
      - ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - calendar_management.py
      - market_calendar 管理・営業日判定関数（is_trading_day / next_trading_day 等）
    - features.py
      - zscore_normalize の再エクスポート
    - stats.py
      - zscore_normalize など統計ユーティリティ
    - audit.py
      - 監査ログ関連テーブル（signal_events / order_requests / executions 等）
    - (その他: quality モジュール等は本スニペットに含まれていないが想定)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
    - feature_exploration.py
      - 将来リターン計算、IC、ファクター統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（raw factor を統合して features テーブルへ）
    - signal_generator.py
      - generate_signals（features と ai_scores を統合して signals を生成）
  - execution/
    - (発注 / execution 層用プレースホルダ)
  - monitoring/
    - (監視用途のモジュールを想定)

---

## 開発上の注意点・設計方針（抜粋）

- ルックアヘッドバイアスを防ぐため、ファクター計算・シグナル生成は target_date 時点で利用可能なデータのみを使う設計。
- DB 保存は可能な限り冪等性を保つ（ON CONFLICT / INSERT ... DO UPDATE）。
- J-Quants API 周りはレートリミット（120 req/min）やリトライ、401 リフレッシュなど堅牢性を重視。
- ニュース収集は SSRF・XMLBomb・gzip bomb 等の攻撃に対する対策を行っている。
- DuckDB を用いたローカル DB を前提とし、初期化・接続は schema.init_schema / get_connection を経由する。

---

## 追加情報・今後の拡張

- execution 層（実際の発注ロジック）や Slack 通知、モニタリングダッシュボードとの連携は別モジュール/サービスとして実装可能です。
- AI スコア（ai_scores テーブル）を生成する NLP モジュールや外部モデル連携を追加すると、news の sentiment を戦略に組み込めます。
- 品質チェック（quality モジュール）や監査ログの可視化ツールは運用での重要性が高いです。

---

README に含めるべき追加情報や、特定の利用例（例: CI 用スクリプト、cron ジョブ設定、Docker 化など）が必要でしたら教えてください。必要に応じてサンプル .env.example や docker-compose の雛形も作成できます。