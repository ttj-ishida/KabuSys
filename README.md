# KabuSys

日本株向けの自動売買基盤（KabuSys）のリポジトリ用 README（日本語）

概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向け共通ライブラリ群です。主な目的は以下：

- J-Quants 等の外部データソースから市場データ・財務データ・ニュースを取得して DuckDB に格納
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量の正規化（Z スコア）および戦略シグナル生成（BUY / SELL）
- ETL パイプライン、マーケットカレンダー管理、ニュース収集、監査ログ等のユーティリティ
- 発注・約定・ポジション管理レイヤ（スキーマと基本構造）

設計上のポイント：
- ルックアヘッドバイアスを避けるため、常に target_date 時点のデータのみ使用
- DuckDB を主要な永続ストアとして想定（軽量で SQL が使える）
- 冪等性（ON CONFLICT / upsert）・トランザクション制御を重視
- 外部依存を最低限にし、テストしやすいよう id_token 等を引数注入可能

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env（および .env.local）から環境変数を自動読込
  - 必須設定の取得（JQUANTS_REFRESH_TOKEN 等）を提供
  - KABUSYS_ENV（development / paper_trading / live）やログレベルの検証

- kabusys.data
  - schema: DuckDB のスキーマ定義と初期化（init_schema / get_connection）
  - jquants_client: J-Quants API クライアント（レート制御 / リトライ / トークン自動リフレッシュ / 保存ユーティリティ）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・正規化・raw_news への保存、銘柄抽出
  - calendar_management: 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 発注から約定までの監査テーブル DDL（トレース用）

- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等

- kabusys.strategy
  - feature_engineering.build_features: research の生ファクターを統合・Zスコア正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を算出、signals テーブルに BUY/SELL を書き込む

- kabusys.execution（基盤用空パッケージ、発注実装を想定）
- 監視・Slack 通知用設定（環境変数経由）

---

## セットアップ手順

前提
- Python 3.10 以上（ソース内で PEP 604 の型記法などを使用）
- システムに DuckDB が必要（Python パッケージ duckdb を利用）
- RSS XML の安全パースに defusedxml を利用

推奨手順（UNIX 環境の例）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （プロジェクトに setup/requirements ファイルがあればそちらを使用してください。
    パッケージ化している場合は `pip install -e .` を使います）

3. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須項目（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...

   - 省略可能:
     - KABUSYS_ENV=development|paper_trading|live  （default: development）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （default: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env ロードを無効化）
     - KABUSYS API ベースURL: KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（default: data/kabusys.duckdb）
     - SQLITE_PATH（default: data/monitoring.db）

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

   - メモリ DB を使いたいときは `init_schema(":memory:")` を指定できます。

---

## 使い方（主要な例）

以下はライブラリを直接利用する簡単なコード例です。実運用ではエラーハンドリング・ログ設定を適切に行ってください。

1) 日次 ETL（市場カレンダー/株価/財務 の差分取得 + 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

2) 特徴量構築（research の生ファクターを取り込み features テーブルへ）
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

3) シグナル生成（features 読み込み → signals テーブルへ）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

4) ニュース収集ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes: 有効な銘柄コードセット（抽出用）
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

5) J-Quants API からのデータ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token から取得
rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(rows))
```

注意:
- 各関数は DuckDB 接続を引数に取るか、init_schema / get_connection で接続を取得します。
- ETL や保存関数は冪等に動作するよう設計されています（ON CONFLICT / upsert）。

---

## 設計・運用に関する補足

- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれか。live フラグは is_live により判定可能。
- ログレベルは LOG_LEVEL で指定。デフォルトは INFO。
- .env の自動ロード順序: OS 環境 > .env.local > .env。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- データベースファイルパスのデフォルト:
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視等）: data/monitoring.db
- ニュース収集時は SSRF 対策・サイズ制限・XML 脆弱性対策が組み込まれています（_is_private_host / defusedxml / MAX_RESPONSE_BYTES など）。
- J-Quants クライアントはレート制限（120 req/min）とリトライ（指数バックオフ、401 のトークン自動更新）に対応しています。

---

## ディレクトリ構成（主なファイル）

プロジェクトの主要ファイル/モジュール（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他 data 層ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (パッケージ想定: README に記載のモニタリング機能と連携)
  - その他ユーティリティモジュール

（上記は本リポジトリに含まれる主要なモジュール構成です。各モジュールに詳細な docstring と設計方針が記載されています。）

---

## 開発・貢献

- コード内の docstring に使用方法と設計の指針が詳細に記載されています。まずは各モジュールの docstring を参照してください。
- テストや CI、パッケージ化（setup.cfg/pyproject.toml）がある場合はそれに従ってください（本 README はコードベースの説明にフォーカスしています）。

---

以上。追加してほしいサンプルやセクション（例: REST API 連携、実際の発注フローの実装例、運用チェックリスト 等）があれば教えてください。README の内容を拡張して具体的な手順やサンプルコードを追加します。