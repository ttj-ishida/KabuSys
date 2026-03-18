# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants API や RSS 等からデータを取得して ETL → 特徴量生成 → 監査/発注までを想定したモジュール群を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT ...）で保存
- Look-ahead bias 対策としてフェッチ時刻（fetched_at）を記録
- DuckDB 上で SQL ウィンドウ関数を活用して効率的に集計
- 外部依存を最小限にし、テストしやすい設計（引数注入やトランザクション制御等）

---

## 機能一覧

- 環境設定読み込み・検証
  - .env（.env.local）を自動で読み込み（必要に応じて無効化可能）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN）
- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - RSS ニュース収集と正規化・DB保存（SSRF 対策・トラッキングパラメータ除去）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL の統合エントリポイント
- スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - 監査ログ（signal → order_request → execution の追跡）
- 研究 / 特徴量ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ、Zスコア正規化
- カレンダー管理
  - 営業日判定、prev/next_trading_day、カレンダー夜間更新ジョブ
- ニュース処理
  - RSS フェッチ、記事ID生成（URL 正規化 + SHA-256）、記事の銘柄抽出、冪等保存

---

## セットアップ手順

前提
- Python 3.9+（型ヒント・Union 表記等を考慮）
- DuckDB を使用するためネイティブなライブラリが利用されます（pip インストールで導入されます）

1. リポジトリをクローン / ソースを用意

2. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - 必須パッケージの例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml で依存を管理してください。

4. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（ただし、OS 環境変数が優先されます）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   代表的な環境変数（必須は明示）:
   - JQUANTS_REFRESH_TOKEN (必須) -- J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) -- kabu ステーション API パスワード
   - SLACK_BOT_TOKEN (必須) -- Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) -- Slack チャンネル ID
   - KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (任意, default: data/kabusys.duckdb)
   - SQLITE_PATH (任意, default: data/monitoring.db)
   - KABUSYS_ENV (任意, default: development) : development|paper_trading|live
   - LOG_LEVEL (任意, default: INFO)

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマの初期化
   - Python REPL やスクリプトで以下を実行してください（`data/schema.init_schema` を使用）:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルパス or ":memory:"
   ```

   - 監査ログ用スキーマを別 DB に分けたい場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的なコード例）

- 日次 ETL を実行する（J-Quants からデータ取得 → 保存 → 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758","9984"}  # あらかじめ集めておく銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- 研究系 API の利用例（ファクター計算・IC 計算）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
t = date(2024, 1, 31)

momentum = calc_momentum(conn, t)
forwards = calc_forward_returns(conn, t, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC
ic = calc_ic(momentum, forwards, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# Zスコア正規化
normed = zscore_normalize(momentum, columns=["mom_1m","ma200_dev"])
```

- J-Quants からのデータフェッチと保存を個別に利用する
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 主要ディレクトリ構成

以下はパッケージ内の主要モジュールと役割の概略です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラスを提供
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアントと保存関数
    - news_collector.py : RSS 収集・正規化・保存・銘柄抽出
    - schema.py         : DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py       : ETL パイプライン（run_daily_etl 他）
    - etl.py            : ETL ユーティリティの公開インターフェース
    - audit.py          : 監査ログ（order/exec トレース）スキーマ初期化
    - calendar_management.py : マーケットカレンダー管理・営業日判定
    - quality.py        : データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py          : 汎用統計ユーティリティ（zscore_normalize）
    - features.py       : 特徴量ユーティリティの公開インターフェース
  - research/
    - __init__.py
    - feature_exploration.py : 将来リターン、IC、統計サマリ、rank
    - factor_research.py     : Momentum/Volatility/Value の計算
  - strategy/
    - __init__.py
    - （戦略モデル関連を配置する想定）
  - execution/
    - __init__.py
    - （発注 / ブローカ連携・ポジション管理を配置する想定）
  - monitoring/
    - __init__.py
    - （運用監視・Slack 通知等を配置する想定）

---

## 注意事項 / 補足

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を読み込みます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）があります。本クライアントは固定間隔スロットリングと再試行ロジックを備えていますが、運用時は注意してください。
- DuckDB のバージョンによっては一部 SQL 構文（ON CONFLICT / RETURNING / 外部キー挙動等）に差異があるため、利用する DuckDB バージョンに合わせた動作確認を推奨します。
- Slack / kabu API 連携部分は本リポジトリ内にスケルトンが含まれており、実際の通知や発注ロジックは用途に応じて実装してください。

---

もし README に追加したい具体的な使い方（例: 定期バッチの systemd / Airflow 設定、サンプル .env.example、CI 流れ、ユニットテストの実行方法など）があれば、要件を教えてください。それに合わせてサンプルを追記します。