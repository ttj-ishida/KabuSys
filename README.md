# KabuSys — 日本株自動売買システム

軽量でモジュール化された日本株向け自動売買・データプラットフォームのコアライブラリです。  
主にデータ取得（J-Quants）、ETL、データ品質チェック、特徴量生成・研究ユーティリティ、ニュース収集、監査ログスキーマ等を提供します。発注・注文管理・モニタリング層の骨組みも含みます（実際のブローカー連携は別途実装）。

---

## 主な概要

- 言語: Python（型ヒント・新しい Union 構文を使用していますので Python 3.10 以上を推奨）
- 永続ストア: DuckDB をメインに使用（ローカルファイルまたは :memory:）
- 外部 API: J-Quants（株価・財務・マーケットカレンダー取得）
- RSS ベースのニュース収集（XML の安全パースに defusedxml を使用）
- 設定は環境変数または .env ファイルで管理（自動ロード機能あり）

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - 日足（OHLCV）、四半期財務、マーケットカレンダーの取得と DuckDB への冪等保存
- ETL / パイプライン
  - 日次差分 ETL（市場カレンダー取得 → 日足取得 → 財務取得）
  - バックフィル、差分更新、品質チェックの組み合わせ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合（未来日付・非営業日）検出
- ニュース収集
  - RSS フィード取得、HTML圧縮対処、SSRF対策、URL 正規化、記事IDのハッシュ化、DuckDB への冪等保存
  - 記事と銘柄コードの紐付け（テキストから 4 桁銘柄コード抽出）
- 研究・特徴量生成
  - モメンタム/ボラティリティ/バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター要約、Z スコア正規化ユーティリティ
- データスキーマ & 監査
  - DuckDB 向けのスキーマ定義（Raw / Processed / Feature / Execution 層）
  - 監査ログ（signal / order_request / execution 等）の初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10+
- Git（オプション）

1. リポジトリをクローン（または本パッケージを配置）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最小依存: duckdb, defusedxml
   ```
   pip install duckdb defusedxml
   ```
   - 追加で開発・運用に必要なライブラリがあれば適宜インストールしてください。

4. 環境変数の設定
   - 必須（少なくとも ETL の J-Quants を使う場合）:
     - JQUANTS_REFRESH_TOKEN
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - KABU_API_PASSWORD
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | ...)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（OS 環境変数 ＞ .env.local ＞ .env の優先順位）。

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_pass
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方・主要 API

以下は簡単な利用例です。プロダクションではロギングや例外処理、トークン管理を適切に行ってください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリは自動作成
  ```

- 監査用 DB 初期化（独立 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL 実行（J-Quants トークンを環境変数で用意）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブの実行例
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄コードセット（抽出に利用）
  known_codes = {"7203", "6758", "9984"}  # 例
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(res)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2024, 1, 31))
  # Zスコア正規化
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 将来リターンと IC（Information Coefficient）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  # forward = calc_forward_returns(conn, target_date, horizons=[1,5,21])
  # ic = calc_ic(factor_records, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## よくある操作

- .env 自動読み込みを無効化する
  - テストや特殊環境で自動ロードを抑止する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- DuckDB をメモリで使う（テスト）
  ```python
  conn = init_schema(":memory:")
  ```

- ETL の差分取得やバックフィル幅は run_daily_etl の引数で調整可能（backfill_days、calendar_lookahead_days など）

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋した構成）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
    - news_collector.py       — RSS ニュース収集 / 保存
    - schema.py               — DuckDB スキーマ定義 & init_schema
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — 特徴量公開インターフェース
    - calendar_management.py  — 市場カレンダー管理 / 更新ジョブ
    - audit.py                — 監査ログスキーマ初期化
    - etl.py                  — ETL 公開型（ETLResult 再エクスポート）
    - quality.py              — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン / IC / 要約
    - factor_research.py      — 各種ファクター計算（momentum, volatility, value）
  - strategy/                  — 戦略関連（骨組み）
  - execution/                 — 発注/実行関連（骨組み）
  - monitoring/                — 監視関連（骨組み）

---

## 注意点 / 設計上のポイント

- DuckDB へは冪等に保存することを心がけ、INSERT ... ON CONFLICT を多用しています。
- J-Quants の API レート制限（120 req/min）に合わせたレートリミッタとリトライロジックを内蔵しています。
- RSS 収集では SSRF 対策、XML BOM 対策、応答サイズ制限などを実装しています。
- 研究・特徴量計算モジュールは本番口座・発注 API にアクセスしない設計です（データ層のみ参照）。
- env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト時は無効化可能です。

---

必要であれば以下も作成します
- requirements.txt（推奨パッケージ一覧）
- サンプルスクリプト（ETL バッチ / カレンダー更新 / ニュース収集）
- 開発・運用ガイド（デプロイ / cron / Airflow 例）

ご希望があれば追加の README セクションや例を追記します。