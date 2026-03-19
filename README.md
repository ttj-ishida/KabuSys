# KabuSys

日本株向け自動売買プラットフォームの基盤ライブラリ（部分実装）。  
データ取得・ETL・データ品質チェック・ファクター計算・ニュース収集・DuckDB スキーマ等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する共通ライブラリ群です。主に次の責務を持ちます。

- J-Quants API からの市場データ・財務データ・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたデータスキーマ定義と冪等な保存ロジック
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- マーケットカレンダー管理（営業日判定など）
- 監査ログ（order/signal/execution トレース）スキーマの提供

設計上のポイント:
- DuckDB をコア DB として使用（初期化・接続関数を提供）
- 外部依存は最小限（ただし DuckDB, defusedxml 等が必要）
- API 利用時のレートリミット・リトライ・トークン更新・ログを重視
- データ品質チェックは Fail-Fast ではなく全件検出して報告

---

## 主な機能一覧

データ取得・保存
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット、リトライ、401 自動リフレッシュ、ページネーション対応

ETL・パイプライン
- 日次 ETL（kabusys.data.pipeline.run_daily_etl）
  - 市場カレンダー、株価、財務データの差分取得と保存
  - バックフィル、営業日調整、品質チェックの統合

データ品質チェック
- 欠損・重複・スパイク・日付不整合の検出（kabusys.data.quality）

ニュース収集
- RSS 収集・前処理・正規化・SSRF 対策（kabusys.data.news_collector）
  - 記事ID を正規化 URL の SHA-256 で生成
  - raw_news / news_symbols 保存（冪等）

スキーマ管理
- DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- 監査ログスキーマの初期化（kabusys.data.audit.init_audit_schema / init_audit_db）

研究・特徴量計算
- ファクター計算（kabusys.research）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
- 統計ユーティリティ（kabusys.data.stats.zscore_normalize）

マーケットカレンダー
- 営業日判定・前後営業日取得・範囲営業日取得（kabusys.data.calendar_management）

設定管理
- .env (および .env.local) 自動読み込みと環境変数経由の設定（kabusys.config.settings）
  - 自動読み込みの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提
- Python 3.10+ を想定（コード型注釈に沿う）
- duckdb, defusedxml が必要（その他は用途に応じて）

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （その他: logging は標準、必要なら requests などを追加）

   （開発用に editable install がある場合）
   - pip install -e .

4. 環境変数（.env）を用意
   プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は上書き優先）。
   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   自動読み込みを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. DuckDB スキーマ初期化（例）
   Python コンソールやスクリプトで:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # または in-memory
   # conn = init_schema(":memory:")
   ```

6. 監査ログ DB 初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（簡易ガイド）

以下は主要ユースケースの最小例です。実運用ではエラー処理やログ設定を行ってください。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセットを用意
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

3) 研究用ファクター計算の呼び出し例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 複数ファクターの Z スコア正規化
records = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

4) J-Quants API から日足を直接取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, recs)
print(saved)
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

必須変数が無い場合、kabusys.config.Settings のプロパティアクセスで ValueError が発生します。

---

## ディレクトリ構成

主要ファイル／ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 -- 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（fetch/save・レート制御）
    - news_collector.py      -- RSS 収集／前処理／保存
    - schema.py              -- DuckDB スキーマ定義と init_schema
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - features.py            -- features 公開インターフェース（zscore 再エクスポート）
    - calendar_management.py -- マーケットカレンダー管理
    - audit.py               -- 監査ログスキーマ初期化
    - etl.py                 -- ETLResult の公開（エイリアス）
    - quality.py             -- データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py -- forward returns / IC / factor_summary / rank
    - factor_research.py     -- momentum/volatility/value の計算
  - strategy/
    - __init__.py            -- （戦略関連を配置するためのパッケージ）
  - execution/
    - __init__.py            -- （発注/約定管理等のパッケージ）
  - monitoring/
    - __init__.py            -- （監視・モニタリング用コード）

（上記は現状のサブモジュール一覧です。strategy/execution/monitoring は将来的な拡張用に空パッケージが用意されています。）

---

## セキュリティ・運用上の注意

- J-Quants API はレート制限があるため、jquants_client は固定間隔スロットリングで制御します。直接の大量リクエストは避けてください。
- news_collector は SSRF 対策・受信サイズ制限・XML パースの安全化（defusedxml）を実装していますが、外部フィードの扱いには注意してください。
- DuckDB に保存されるタイムスタンプは UTC を想定する箇所があります（監査ログで SET TimeZone='UTC' を設定します）。
- 本ライブラリは本番の発注 API へ直接アクセスするモジュールを含みません（design 文書に従った分離を想定）。本番口座での自動売買を行う場合はリスク管理とテストを徹底してください。

---

## 参考 / 次のステップ

- 実運用ではログ設定（ローテーション・監視）や例外監視（Sentry など）を追加してください。
- strategy / execution 層の実装（ポートフォリオ構築・リスク管理・ブローカー連携）を作成して組み合わせてください。
- テスト: settings の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。ユニットテストでは id_token 注入やネットワークコールのモックを推奨します。

---

必要であれば README に使い方のコード例や .env.example、docker-compose 用のサービス定義、あるいはテスト手順の追加を行います。どの情報を追加しますか？