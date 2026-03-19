# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータレイクとして利用し、J-Quants からのデータ取り込み（OHLCV、財務、マーケットカレンダー）、RSS ニュース収集、データ品質チェック、研究用途のファクター計算までを含むモジュール群を提供します。

---

## 主要な特徴

- データ取得（J-Quants API）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得（ページネーション・再試行・レート制御付き）
- 永続化（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のスキーマ定義と冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- ニュース収集
  - RSS フィード取得、前処理、記事ID生成（正規化された URL のハッシュ）、DuckDB への冪等保存、銘柄コード抽出
  - SSRF 対策、gzip 制限、XML の安全パース（defusedxml）
- 研究（Research）ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、Zスコア正規化など（外部ライブラリに依存しない実装）
- 監査（Audit）
  - シグナル→発注→約定までのトレーサビリティ用スキーマ、冪等キーなどを用意

---

## 依存関係 (最低限)

- Python 3.10+
- duckdb
- defusedxml

（ネットワーク呼び出しを行うため urllib / stdlib を使用しています。J-Quants API 利用時はインターネットアクセスが必要です）

pip での例:
```
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

kabusys は .env または環境変数から設定値を読み込みます（自動ロードはプロジェクトルートに `.git` または `pyproject.toml` がある場合に行われます）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings で参照されるもの）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabuステーション API
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: （省略可）デフォルト: http://localhost:18080/kabusapi
- Slack
  - SLACK_BOT_TOKEN: Slack Bot Token（必須）
  - SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
- データベースパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- 実行環境
  - KABUSYS_ENV: one of ["development", "paper_trading", "live"]（デフォルト: development）
  - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）

設定値は `from kabusys.config import settings` 経由で利用できます。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定します。必要なキーは上記参照。
   - テスト時に自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化
   - アプリケーションで使用する DuckDB を作成しスキーマを作成します。
   - 例: Python シェルで
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data import audit
     conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     conn.close()
     ```

---

## 使い方（主なユースケース）

以下は代表的な呼び出し例です。CLI は別途用意されていないため Python からモジュールを直接呼び出します。

1. 日次 ETL 実行（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data import pipeline, schema

   conn = schema.init_schema("data/kabusys.duckdb")
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   conn.close()
   ```

2. J-Quants から日足を直接取得して保存（テスト用）
   ```python
   import duckdb
   from kabusys.data import jquants_client as jq

   conn = duckdb.connect(":memory:")
   # 必要なテーブルがあること（init_schema を先に呼ぶのが推奨）
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
   saved = jq.save_daily_quotes(conn, records)
   ```

3. RSS ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)
   conn.close()
   ```

4. 研究用ファクター計算の例
   ```python
   from datetime import date
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
   from kabusys.data import schema
   import duckdb

   conn = schema.get_connection("data/kabusys.duckdb")
   target = date(2024, 1, 31)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)
   fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

   # 例: mom と fwd を使って IC を計算
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   print("IC:", ic)
   ```

5. Zスコア正規化
   ```python
   from kabusys.data.stats import zscore_normalize
   normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
   ```

---

## よく使うモジュール一覧（機能別）

- kabusys.config
  - 環境変数の読み込み / Settings オブジェクト
- kabusys.data.jquants_client
  - fetch_* / save_* : API 取得と DuckDB 保存
- kabusys.data.schema
  - init_schema / get_connection : DuckDB スキーマ初期化・接続
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## 開発時のヒント

- 自動で .env をロードする挙動は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時に便利）。
- DuckDB のスキーマ初期化は冪等です。既存の DB に対して何度実行しても安全にテーブルを作成します。
- J-Quants の API 呼び出しにはレート制限・リトライ・トークン自動リフレッシュのロジックが組み込まれています。
- news_collector は SSRF 防止・XML Bomb 対策・最大受信サイズ制限などセキュリティに留意した実装になっています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

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
    - etl.py
    - quality.py
    - audit.py
    - audit.py (監査スキーマ)
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要な責務はファイル名の通り分離されています（data: ETL/保存/品質、research: ファクター計算、execution/strategy: 発注・戦略関連のプレースホルダなど）。

---

## ライセンス / 貢献

（ここにライセンスや貢献ガイドラインを記載してください）

---

README に含めたい追加情報（CI の設定、Docker イメージ、具体的な運用フロー、より詳細な環境例など）があればお知らせください。必要に応じてサンプル .env.example も作成します。