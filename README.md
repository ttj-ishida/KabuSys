# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ/内部モジュール群）。

このリポジトリは、J-Quants 等の外部データソースからデータを取得・保存し、
DuckDB を用いて加工・特徴量生成・シグナル生成までを行う基盤的モジュール群を提供します。
戦略層は発注レイヤー（kabuステーション等）と分離され、ルックアヘッドバイアスや冪等性に配慮した設計です。

バージョン: 0.1.0

---

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（株価・財務・市場カレンダー等の取得、ページネーション・レートリミット対応）
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事ID生成）
  - DuckDB 用のスキーマ定義と冪等保存（ON CONFLICT を利用）

- ETL / データパイプライン
  - 差分更新（最終取得日に基づく差分取得、バックフィル対応）
  - 品質チェック（欠損・スパイク等の検出、処理継続方針）

- リサーチ / 特徴量
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（prices_daily / raw_financials を使用）
  - クロスセクション Z スコア正規化ユーティリティ

- 戦略処理
  - 特徴量の正規化・ユニバースフィルタ適用 → features テーブル保存（冪等）
  - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成（signals テーブルに保存）
  - Bear レジーム判定、ストップロス等のエグジットルール実装

- 実行・監査（スキーマ）
  - signals / signal_queue / orders / trades / positions / audit 用テーブル定義
  - 監査ログのためのテーブル（signal_events / order_requests / executions）定義

---

## 要件

- Python 3.10 以上（型注釈に新しい union 型構文（X | Y）を利用）
- 主要依存パッケージ（最低限）
  - duckdb
  - defusedxml

（その他、標準ライブラリで多くを実装しています。必要に応じて logging 等を設定してください。）

pip によるインストール例:
```
python -m pip install "duckdb>=0.6" defusedxml
```

※プロジェクトをパッケージとして扱う場合は `pip install -e .` を想定しています（setup/pyproject がある場合）。

---

## 環境変数（主なもの）

KabuSys は .env / .env.local / 環境変数を自動で読み込みます（プロジェクトルートに .git または pyproject.toml があることが条件）。
自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings._require を参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（オプション機能利用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルト値あり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)

.env の例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python を用意（3.10+）
2. 必要パッケージをインストール
   - 例: `pip install duckdb defusedxml`
3. リポジトリをクローンして、プロジェクトルートに `.env` を作成（.env.example を参考に）
4. DuckDB の初期スキーマを作成
   - Python REPL やスクリプトで次を実行:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # デフォルトパスは .env の DUCKDB_PATH と合わせる
conn.close()
```

これで必要なテーブルが作成されます（既存テーブルはスキップされるため冪等）。

---

## 使い方（代表的な操作例）

以下はライブラリを直接呼び出す最小例です。実運用ではジョブスケジューラ（cron, Airflow 等）やワーカーから呼び出します。

- 日次 ETL（株価・財務・カレンダーの差分取得）:

```python
from datetime import date
import duckdb
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

# DB を初期化して接続（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（省略時 target_date は today）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量のビルド（features テーブルへの書き込み）:

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2026, 3, 1))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへの書き込み）:

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2026, 3, 1), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS 収集 → raw_news / news_symbols 保存）:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効コードセット（例: 全上場銘柄の4桁コード集合）
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)
```

- カレンダー更新（夜間バッチ）:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 開発向けヒント

- 自動で .env を読み込む仕組み:
  - .env（プロジェクトルート）を自動ロード
  - .env.local があれば上書き（優先）
  - テストや特殊環境で自動ロードを止める場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

- ロギング:
  - 各モジュールは logging を使用しています。運用時はハンドラ・フォーマットを設定してください。

- 冪等性:
  - データ保存関数（save_*）やスキーマ初期化は冪等性を考慮して実装されています。複数回実行してもデータ重複が発生しない設計です。

---

## ディレクトリ構成（主要ファイル）

（src 以下を基準）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集 / 前処理 / DB 保存
    - schema.py              — DuckDB スキーマ定義と初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - audit.py               — 監査ログ用テーブル DDL
    - features.py            — データモジュールの公開インターフェース
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features を作る処理（ユニバースフィルタ・正規化）
    - signal_generator.py    — final_score 計算と signals 生成
  - execution/
    - __init__.py            — 発注・実行層（発注API連携はここに追加）
  - monitoring/              — 監視系モジュール（将来的に配置）
  - その他モジュール多数（ETL・品質チェック等）

注: 上記は現在の主要モジュール構成の抜粋です。詳細は各ファイルの docstring を参照してください。

---

## よくある運用フロー（例）

1. 初回: `init_schema()` で DB を作成
2. 定常: 毎朝 / 夜間に `run_daily_etl()` を実行 → 欠損・スパイクを検知
3. 特徴量生成: ETL 後に `build_features()` を実行（date 単位で冪等）
4. シグナル生成: `generate_signals()` を実行して signals を作成
5. 実行層: signals を読み取り、発注要求を signal_queue に入れ、ブローカーAPI へ送信（execution 層実装）
6. 監査: order_requests / executions テーブルでトレーサビリティを保持

---

## 参考・注意点

- ルックアヘッドバイアス対策:
  - 全モジュールは target_date 時点までのデータのみを使用するよう設計されています（ETL/feature/signal 等）。
- セキュリティ:
  - RSS 取得では SSRF 対策・gzip サイズチェック・XML パースに defusedxml を利用しています。
  - J-Quants クライアントはトークン自動更新と再試行ロジックを備えています。
- テスト:
  - モジュールは外部依存（HTTP, DB）を注入可能に作られているため、モックを用いたユニットテストが書きやすくなっています。

---

もし README に追加したい具体的な使い方（cron 設定例、docker-compose、CI ワークフロー、サンプル .env.example など）があれば教えてください。必要に応じて追記・例を作成します。