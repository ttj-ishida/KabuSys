# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、DuckDBスキーマ、品質チェック、監査ログなど、取引戦略や発注実行の基盤となるモジュール群を提供します。

---

## 概要

KabuSys は、日本株の自動売買システムを構築するための基盤ライブラリです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーデータ取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB ベースの3層（Raw / Processed / Feature）データスキーマの定義と初期化
- ETL（差分更新・バックフィル・品質チェック）パイプライン
- RSS からのニュース収集と銘柄紐付け（セキュアな取得・前処理・冪等保存）
- 監査ログ（シグナル → 発注 → 約定のトレース）用スキーマ
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）

設計上の特徴：
- API レート制御（J-Quants は 120 req/min）と指数バックオフによる堅牢なリトライ
- Look-ahead bias を避けるための fetched_at / UTC 基準時刻保存
- データ保存は冪等（ON CONFLICT ...）を多用
- ニュース収集での SSRF / XML Bomb / 大量レスポンス対策

---

## 機能一覧

- jquants_client
  - 株価日足（OHLCV）、財務（四半期）、マーケットカレンダーの取得
  - 自動トークンリフレッシュ、ページネーション、レート制御、リトライ
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar）

- data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - スキーマ初期化関数 `init_schema(db_path)`

- data.pipeline
  - 日次 ETL（差分取得、バックフィル、品質チェック）のエントリ `run_daily_etl`
  - 個別ジョブ: prices / financials / calendar ETL

- data.news_collector
  - RSS から記事を収集し `raw_news` に保存
  - URL 正規化、トラッキングパラメータ除去、ID（SHA-256）生成
  - SSRF / リダイレクト先検査、gzip サイズ上限、defusedxml による XML 保護
  - 銘柄コード抽出と `news_symbols` への紐付け

- data.calendar_management
  - market_calendar を使った営業日判定、next/prev_trading_day、カレンダー更新ジョブ

- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
  - `run_all_checks` による一括実行

- data.audit
  - 監査ログテーブル（signal_events / order_requests / executions）初期化

- config
  - .env ファイル / 環境変数の自動読み込み（プロジェクトルート検知）
  - `settings` オブジェクト経由で必須設定を取得

---

## セットアップ手順

以下は一般的なセットアップ例です。プロジェクトごとの要件に合わせて調整してください。

1. 必要条件
   - Python 3.9+（型アノテーションで `|` が使われているため）
   - ネットワークアクセス（J-Quants API、RSS 等）
   - 必要パッケージ（例: duckdb, defusedxml）

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意して `pip install -e .` などでインストールしてください。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | ...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python スクリプト or REPL で実行:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   - 監査ログだけ別 DB に分けたい場合:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な API 例）

注意: ここではモジュールの代表的な使い方を示します。

- 設定取得
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を引数で指定可
print(result.to_dict())
```

- 個別 ETL（例: 株価）
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date
conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
saved_count = calendar_update_job(conn)
```

- ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: {'7203','6758',...}）
results = run_news_collection(conn, known_codes={'7203', '6758'})
print(results)
```

- J-Quants トークン取得（内部で自動リフレッシュされますが、直接呼ぶこともできます）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

---

## 動作上の注意 / 設定

- .env 自動読み込み:
  - パッケージはインポート時に .git または pyproject.toml を探索してプロジェクトルートを特定し、`.env` → `.env.local` の順で自動読み込みします。
  - OS 環境変数は優先され、`.env.local` は `.env` を上書きします。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 環境（KABUSYS_ENV）:
  - 有効値: `development`, `paper_trading`, `live`
  - 本番運用時は `live` を使用してください（外部API/発注挙動の制御に利用されます）。

- ロギングレベル:
  - `LOG_LEVEL` で制御（`DEBUG`, `INFO`, ...）。不正な値はエラーになります。

- J-Quants API のレート制御:
  - 内部で固定間隔スロットリング（120 req/min）を実装しています。複数プロセスでの並列リクエストは別途調整が必要です。

- ニュース収集の安全性:
  - リダイレクトや最終URLに対するホスト検査、スキーム制限（http/https のみ）、最大レスポンスサイズチェック、gzip 解凍後の上限検査、defusedxml による XML パース防御を実装しています。

---

## ディレクトリ構成

プロジェクトの主要ファイル・モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存）
      - news_collector.py            -- RSS ニュース収集・保存・銘柄抽出
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       -- 市場カレンダー管理（営業日判定 / 更新ジョブ）
      - quality.py                   -- データ品質チェック
      - audit.py                     -- 監査ログ用スキーマ初期化
    - strategy/
      - __init__.py                  -- 戦略用プレースホルダ
    - execution/
      - __init__.py                  -- 発注 / 実行周りプレースホルダ
    - monitoring/
      - __init__.py                  -- モニタリング関連（プレースホルダ）

上記はコードベースに含まれる主なモジュールです。実際にはさらに細かいユーティリティや拡張モジュールが追加される想定です。

---

## 開発・貢献

- バグ修正・機能追加は Pull Request をお願い致します。  
- サンプルコード・運用スクリプトは個別に追加してください（cron/ワーカー/監視連携等）。

---

## ライセンス / 注意事項

- 本リポジトリはサンプル実装（雛形）として提示されています。実運用する際は API キー・認証情報の管理、エラーハンドリング、発注の安全策（資金管理、スリッページ制御、レート制限）を十分に実装・検証してください。金融商品取引に関する法令遵守も必須です。

---

README に記載した使い方はコードベースに基づく利用例です。具体的な運用フローや追加の設定がある場合は、プロジェクト固有のドキュメントを参照・追加してください。