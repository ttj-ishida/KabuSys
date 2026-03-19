# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
データ取得・ETL、特徴量生成、ファクター解析、ニュース収集、監査ログ、発注系インターフェースの基盤を提供します。

主な設計方針：
- DuckDB を中心としたローカルデータレイク（Raw / Processed / Feature / Execution レイヤー）
- J-Quants API からのデータ取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- ETL は差分更新・バックフィルを行い冪等性を保証
- 研究（research）モジュールは発注系にアクセスせず、外部ライブラリに依存しない実装を心がける
- ニュース収集は SSRF / XML BOM 等のセキュリティ対策を実装

---

## 機能一覧

- 環境変数・設定管理
  - .env 自動読み込み（プロジェクトルート基準）、必須設定チェック
- データ取得 / 保存（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期）/ マーケットカレンダーの取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ、401 のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、バックフィル、品質チェックの統合ジョブ（run_daily_etl）
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 監査ログ用スキーマ（audit）初期化ユーティリティ
- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比）、主キー重複、日付不整合チェック
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理、記事ID生成（正規化 URL → SHA256）、銘柄抽出、DB保存
  - SSRF / gzip bomb / XML 攻撃対策
- 統計ヘルパ（kabusys.data.stats）
  - クロスセクション Z スコア正規化など
- 研究用ファクター計算（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 発注・戦略・監視などの基盤（strategy / execution / monitoring）用パッケージ構成（実装の拡張ポイント）

---

## 前提条件 / 必須ソフトウェア

- Python 3.10 以上
  - （型ヒントに `X | None` 形式を使用しているため 3.10+ を想定）
- pip, virtualenv（推奨）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

依存はプロジェクトのパッケージ設定（pyproject.toml / requirements.txt）がある場合はそちらに従ってください。

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt ある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - ない場合は最低限:
     ```bash
     pip install duckdb defusedxml
     ```
   - 開発インストール（パッケージ化されている場合）:
     ```bash
     pip install -e .
     ```

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます（既存の OS 環境変数は上書きされません）。テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID : Slack チャネルID（必須）
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
     - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 初期化（DB スキーマ）

DuckDB スキーマを初期化します（ファイルがなければ親ディレクトリを作成します）。

Python から:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env 等から取得されます
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

既存 DB に接続するだけなら:
```python
from kabusys.data.schema import get_connection
conn = get_connection(settings.duckdb_path)
```

---

## 使い方（代表的な利用例）

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行（RSS から raw_news へ保存、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は既知銘柄コードセット（抽出に利用）
known_codes = {"7203", "6758"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

- 研究（ファクター計算・評価）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.config import settings
from kabusys.research import (
    calc_momentum, calc_volatility, calc_value,
    calc_forward_returns, calc_ic, factor_summary, zscore_normalize
)

conn = get_connection(settings.duckdb_path)
target = date(2024, 1, 4)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- J-Quants から単体データを取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection(settings.duckdb_path)
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print("saved:", saved)
```

注意：
- research モジュールは発注APIへアクセスしません（分析専用）。
- jquants_client はレート制限・再試行・401 自動リフレッシュ等を行います。

---

## 開発メモ / 実装上の注意

- .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の INSERT / UPDATE は各 save_* 関数で冪等化（ON CONFLICT）しています。
- news_collector は外部リクエストに対して SSRF・gzip/size・XML の脆弱性対策を実施しています。
- jquants_client のレート制御は固定間隔スロットリング（120 req/min）で行われます。429 の場合は Retry-After を尊重します。
- ETL は Fail-Fast ではなく、品質チェックの結果を返し呼び出し元が判断する設計です。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートに `src/kabusys` を配置するレイアウトを想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - news_collector.py       — RSS 収集・前処理・DB保存
    - schema.py               — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py             — ETL パイプライン（run_daily_etl など）
    - etl.py                  — ETLResult の公開
    - quality.py              — データ品質チェック
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - features.py             — features 公開インターフェース（zscore など）
    - calendar_management.py  — 市場カレンダー管理ユーティリティ
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン / IC / summary / rank
    - factor_research.py      — momentum / volatility / value の計算
  - strategy/
    - __init__.py            — 戦略実装用パッケージ（拡張ポイント）
  - execution/
    - __init__.py            — 発注 / 実行管理用パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視・アラート用パッケージ（拡張ポイント）

---

## 貢献 / 連絡

- バグ・改善提案は Issue を立ててください。  
- コントリビューションの際はユニットテストと docstring の追加をお願いします。

---

この README はコードベースの主要機能と典型的な使い方をまとめたものです。詳細は各モジュールの docstring を参照してください。