# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
DuckDB をデータ層に使用し、J-Quants など外部データソースからの ETL、ニュース収集、ファクター計算、品質チェック、監査ログ等のユーティリティ群を提供します。

---

## 主な概要

- 目的: 日本株のデータ収集（株価・財務・カレンダー・ニュース）→ DuckDB に格納 → 特徴量計算・品質チェック → 戦略/発注レイヤへ受け渡すための基盤を提供する。
- 設計方針:
  - DuckDB を中心に冪等（idempotent）な保存ロジックを採用（ON CONFLICT …）。
  - J-Quants API のレート制御・リトライ・トークンリフレッシュ対応。
  - ニュース収集は RSS を安全に扱う（SSRF 対策、XML の安全パース、受信上限）。
  - 研究用（research）モジュールは外部ライブラリに依存せず標準ライブラリのみで実装（pandas 等不要）。
  - 品質チェックは Fail-Fast ではなく問題を列挙する設計。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークン管理）
  - news_collector: RSS 収集・前処理・DuckDB への保存（重複排除、銘柄紐付け）
  - schema: DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化
  - pipeline / etl: 日次 ETL パイプライン（差分取得・ backfill・品質チェック）
  - calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログ（シグナル→発注→約定までのトレーサビリティ）
  - stats / features: Z スコア正規化など共通統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー等
- strategy / execution / monitoring: パッケージプレースホルダ（拡張用）

---

## 必要要件 (主な依存)

- Python 3.9+
- duckdb
- defusedxml

インストール例（プロジェクト環境に応じて適宜）:

```sh
python -m pip install duckdb defusedxml
# または
python -m pip install -e .
```

（プロジェクトで requirements.txt / pyproject.toml を用意している場合はそちらに従ってください。）

---

## セットアップ手順

1. リポジトリをクローン／取得して Python 環境を準備する。

2. 必要パッケージをインストール。

   ```sh
   python -m pip install duckdb defusedxml
   ```

3. 環境変数（または .env ファイル）を設定する。自動で .env/.env.local を読み込む機能があります（プロジェクトルート検出: .git または pyproject.toml を基準）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: .env（プロジェクトルートに配置）

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack (通知用)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス (任意)
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（Settings で required）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

4. DuckDB スキーマを初期化する（例: デフォルトの DUCKDB_PATH を使用）:

   Python スクリプト例:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

   またはコマンドラインから直接実行するユーティリティがあればそちらを利用してください（本コードベースには CLI は明示されていません）。

---

## 使い方（代表的な例）

以下は代表的な使い方のコード例です。実行時は適切に環境変数を設定してください。

- DuckDB の初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成して全テーブルを作成
```

- 日次 ETL を実行する（pipeline.run_daily_etl を使用）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行（RSS の収集・保存・銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- ファクター計算（研究用）

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

# モメンタム計算
factors = calc_momentum(conn, target)

# 将来リターン（翌日・5日・21日）
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# IC 計算（例: mom_1m と fwd_1d の相関）
ic = calc_ic(factors, fwd, "mom_1m", "fwd_1d")
print("IC:", ic)
```

- Zスコア正規化

```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## 主要モジュール・ディレクトリ構成

（リポジトリ内の主要な配置 / src/kabusys を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理 (Settings)
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
      - news_collector.py      — RSS 収集・前処理・保存
      - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - features.py            — 特徴量ユーティリティ（再エクスポート）
      - stats.py               — 統計ユーティリティ（zscore_normalize）
      - quality.py             — データ品質チェック
      - calendar_management.py — 市場カレンダー管理 / 営業日ユーティリティ
      - audit.py               — 監査ログ（signal/order/execution）初期化
      - etl.py                 — ETLResult 型の再エクスポート
    - research/
      - __init__.py
      - feature_exploration.py — 将来リターン・IC・summary 等
      - factor_research.py     — mom/volatility/value ファクター計算
    - strategy/
      - __init__.py            — 戦略レイヤ（拡張用）
    - execution/
      - __init__.py            — 発注レイヤ（拡張用）
    - monitoring/
      - __init__.py            — 監視・メトリクス（拡張用）

---

## 環境変数と設定の詳細

- 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings で参照される主要キー:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

---

## 注意点 / 運用に関する補足

- J-Quants の API レート制限 (120 req/min) や 401 リフレッシュロジック、429 の Retry-After 処理を組み込んでいますが、実運用時は API 利用ルールに従ってください。
- DuckDB へは冪等に保存するコード（ON CONFLICT）を用いていますが、外部からの直接変更やスキーマ差異に注意してください。
- news_collector は SSRF や XML 脆弱性対策（defusedxml）を行っています。外部 RSS を投入する際は想定外のコンテンツに注意してください。
- audit（監査ログ）モジュールは UTC タイムゾーンでの記録を前提としています（SET TimeZone='UTC' を実行）。

---

## 貢献 / 拡張

- strategy、execution、monitoring 等のパッケージは拡張用プレースホルダです。実戦向けの発注ロジックやブローカー接続、監視アラート統合などはここに実装してください。
- 単体テストや CI、CLI ツール（ETL スケジューラ等）は別途追加することを推奨します。

---

README に記載のない詳細な使い方や CLI、デプロイ手順などを追加したい場合は、目的（例: cron で nightly ETL を回す、監査用 DB を別ファイルに分離する、kabuステーションとの実注文連携を行う等）を教えてください。具体的なコード例や運用手順を追加します。