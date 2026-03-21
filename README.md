# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理を備え、戦略・実行の各層を分離して実装しています。

主な設計方針:
- ルックアヘッドバイアスを避ける（各処理は target_date 時点のデータのみを使用）
- DuckDB を中心としたローカルデータベース（冪等保存・トランザクション）
- API 呼び出しに対するリトライ・レート制限・トークン自動更新を実装
- 外部依存は最小限（標準ライブラリ + duckdb, defusedxml）

バージョン: 0.1.0

---

## 機能一覧

- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ
- DuckDB スキーマ定義 / 初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得・保存・品質チェックを含む日次 ETL）
- 特徴量（factor）計算（momentum / volatility / value 等）
- 特徴量正規化（Z スコア）
- シグナル生成（ファクター + AI スコア統合 → BUY/SELL シグナル）
  - Bear レジーム抑制、ストップロス等のエグジット判定
- ニュース収集（RSS → raw_news、記事正規化、銘柄抽出）
  - SSRF 防止、XML BOM/攻撃対策、受信サイズ制限
- 監査ログ / 監査テーブル（シグナル→発注→約定のトレース）
- 環境変数 / 設定管理（.env 自動ロード機能）

---

## 要求環境 / 依存

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（実行環境に合わせて pyproject.toml / requirements.txt を参照してインストールしてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 依存インストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - pip install -e .    # パッケージを開発インストール（pyproject がある前提）
4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成（自動でロードされます）
   - 必須環境変数（以下参照）を設定してください
   - テストや一時的に自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注に必要な場合）
- SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID

任意 / デフォルト（環境変数が未設定時にフォールバック）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

---

## 初期化 — DuckDB スキーマ作成

DuckDB データベースを初期化して全テーブルを作成します：

Python 例:
```python
from pathlib import Path
from kabusys.data import schema

db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)
# conn は duckdb.DuckDBPyConnection インスタンス
```

注:
- db_path に指定した親ディレクトリが存在しない場合は自動作成されます。
- ":memory:" を渡すとメモリ内 DB を使用します（テスト向け）。

---

## 使い方（主要ユースケース）

以下は代表的な操作例です。各関数はライブラリ API として利用できます。

1) 日次 ETL（株価・財務・カレンダーの差分取得・保存・品質チェック）
```python
from kabusys.data import pipeline, schema
from pathlib import Path

conn = schema.init_schema(Path("data/kabusys.duckdb"))
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

2) 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {n}")
```

3) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date(2024, 1, 31))
print(f"signals written: {count}")
```

4) ニュース収集（RSS）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources: {source_name: rss_url}（省略時はデフォルトが使われる）
res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

5) J-Quants クライアント（直接利用する場合）
```python
from kabusys.data import jquants_client as jq
# id_token は省略可能。内部で settings.jquants_refresh_token を使って取得する。
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 設定・環境変数の自動ロード

- パッケージはプロジェクトルート（.git または pyproject.toml がある親）から .env を自動で読み込みます。
  - 読み込み順序: OS 環境 > .env.local > .env
  - 自動ロードを無効にする場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env のパースはシェル風（export プレフィックス、クォート、コメント、エスケープ等）に対応しています。
- settings オブジェクトからアプリ設定にアクセスできます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## ディレクトリ構成（主要ファイル/モジュール）

プロジェクトは src/kabusys 配下に実装されています。主要モジュール:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py               — DuckDB スキーマ定義・init
    - jquants_client.py       — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py  — 市場カレンダー管理・営業日ユーティリティ
    - audit.py                — 監査ログテーブル定義
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - features.py             — features の公開ラッパー
    - ...（quality, others が想定）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — features 構築ロジック（build_features）
    - signal_generator.py     — シグナル生成ロジック（generate_signals）
  - execution/                — 発注・ブローカー接続（未展開ファイルあり）
  - monitoring/               — 監視/通知用ロジック（別途実装想定）

各モジュールは README 内の API 例で示した関数群を提供します（詳細は各モジュールの docstring を参照）。

---

## ロギング / デバッグ

- 設定: LOG_LEVEL によりログレベルを制御できます（デフォルト INFO）。
- モジュール内で logger = logging.getLogger(__name__) を使っているため、アプリ側で logging.basicConfig/ハンドラを設定して運用してください。

---

## テスト / 開発上の注意

- ライブラリ内では外部 API 呼び出し（ネットワーク）・ファイル I/O を行う箇所があるため、ユニットテストでは該当箇所をモックする設計になっています（例: news_collector._urlopen を差し替え）。
- 自動 .env ロードは便利ですが、CI やテストで明示的な環境設定を行いたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして無効化してください。

---

## 貢献

- バグ修正・改善提案は PR を送ってください。コード内の docstring と DataPlatform/StrategyModel 等の設計ドキュメントに準拠することを推奨します。

---

必要ならば、README を英語版に翻訳したり、各 API のサンプルや運用手順（cron / Airflow などでのスケジューリング、Slack 通知連携、発注フロー）を追記します。どの部分を詳しく説明したいか教えてください。