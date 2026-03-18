# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants API などから市場データ・財務データ・ニュースを収集し、DuckDB に格納・整形、品質チェック、特徴量生成、リサーチ用ユーティリティ、監査ログなどを提供します。戦略・発注・監視部分は別モジュール（strategy / execution / monitoring）で構築できる設計になっています。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の明示的チェック

- データ収集（J-Quants）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - 取得データの DuckDB への冪等保存（ON CONFLICT）

- ニュース収集
  - RSS フィード取得、URL 正規化、トラッキング除去、SSRF 対策
  - raw_news / news_symbols への冪等保存、記事→銘柄の紐付け

- ETL パイプライン
  - 差分更新（最終取得日を基に差分のみ取得）
  - バックフィルによる後出し修正吸収
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化ユーティリティ
  - 監査ログ（signal/events/order_requests/executions）用スキーマ、UTC タイムゾーン固定

- リサーチ / 特徴量
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）算出
  - Zスコア正規化などの統計ユーティリティ

- 品質・安全
  - XML・HTTP の安全対策（defusedxml、SSRF 判定、レスポンスサイズ制限）
  - DuckDB に対するトランザクション管理（ETL の一部はトランザクションで実行）

---

## 要求事項（依存パッケージ）

主要な依存例：
- Python 3.10+
- duckdb
- defusedxml

（プロジェクトで使用するその他ライブラリは各環境に応じて追加してください。requirements.txt がある場合はそれを利用してください。）

インストール例（仮に requirements.txt が無い場合）:
```
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb defusedxml
```

---

## 環境変数（主なもの）

必須（Settings によって参照されます）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注等を使う場合）
- SLACK_BOT_TOKEN : Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意/デフォルトあり:
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env 読み込み制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを停止します。

.env ファイルはプロジェクトルート（.git または pyproject.toml の親ディレクトリを探索）から読み込まれます。.env.local は .env の上書きとして読み込まれます（OS 環境変数は保護されます）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化、依存パッケージインストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt   # あれば
   # なければ最低限:
   pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに .env を作成（.env.example を参考に）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - :memory: を渡すとメモリ DB になります（テスト用途）。

5. （任意）監査ログ専用 DB 初期化
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要 API 例）

- 日次 ETL 実行（市場カレンダー・株価・財務データ・品質チェック）
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema(settings.duckdb_path)
  # known_codes: 抽出に使う有効な銘柄コードセット（任意）
  known_codes = {"7203", "6758", "9984"}
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: saved_count, ...}
  ```

- ファクター計算 / リサーチ
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

  conn = init_schema(settings.duckdb_path)
  target = date(2024, 1, 31)
  momentum = calc_momentum(conn, target)
  forwards = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, forwards, factor_col="mom_1m", return_col="fwd_1d")
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- 市場カレンダー判定ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  is_trading = is_trading_day(conn, date(2024, 1, 1))
  next_day = next_trading_day(conn, date(2024, 1, 1))
  ```

- DuckDB スキーマ関連
  - init_schema(db_path) : 全テーブルを作成して接続を返す
  - get_connection(db_path) : 既存 DB に接続（初期化しない）

---

## 注意点 / 運用メモ

- J-Quants API のレート制限（120 req/min）を遵守する実装になっていますが、実運用ではさらにバッチ実行の間隔や同時実行数に注意してください。
- ETL は後出し修正（API 側でデータが更新されるケース）を吸収するためにバックフィルを行います。backfill_days を調整してください。
- news_collector は外部 RSS を扱うため、SSRF や大容量レスポンス対策を施しています。独自ソースを追加する際は URL の検証方針を確認してください。
- production（実口座）での発注機能を扱う際は、KABUSYS_ENV を "live" に設定し、十分なテストとリスク管理（ストップロス、最大ポジション制限等）を導入してください。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュール・ファイルの構成です。

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント + 保存ユーティリティ
      - news_collector.py            -- RSS ニュース収集・保存
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - quality.py                   -- データ品質チェック
      - stats.py                     -- 統計ユーティリティ（zscore_normalize 等）
      - features.py                  -- 特徴量関連インターフェース
      - calendar_management.py       -- マーケットカレンダー管理ユーティリティ
      - audit.py                     -- 監査ログスキーマ（signal/order/execution）
      - etl.py                       -- ETL 公開インターフェース
    - research/
      - __init__.py
      - factor_research.py           -- Momentum/Value/Volatility 等のファクター計算
      - feature_exploration.py       -- 将来リターン / IC / 統計サマリー
    - strategy/                       -- 戦略実装用パッケージ（雛形）
      - __init__.py
    - execution/                      -- 発注・ブローカーラッパー（雛形）
      - __init__.py
    - monitoring/                     -- モニタリング関連（雛形）

上記以外に、ユーティリティや追加のモジュールが含まれます。各モジュールのドキュメントはソースの docstring を参照してください。

---

## 貢献 / 拡張

- strategy / execution / monitoring はプロジェクトの要件に合わせて実装・拡張する想定です。
- 新しいデータソースを追加する場合は data/ 以下にクライアントと保存ロジック（冪等性）を実装してください。
- DuckDB スキーマを拡張する場合は schema.py の DDL とインデックスを更新し、init_schema の順序や依存関係に注意してください。

---

README に記載のない細かい API や実装方針はソースコードの docstring を参照してください。質問や具体的な使用例（ETL スケジュール設定、実口座接続の実装など）があれば、用途に合わせたサンプルコードを作成します。