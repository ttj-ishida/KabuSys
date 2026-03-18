# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS を使ったデータ収集、DuckDB ベースのスキーマ、ETL パイプライン、ファクター計算・リサーチ用ユーティリティ、品質チェック、監査ログ機能などを提供します。

> 現バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤と研究（Research）ツール群をまとめたライブラリです。主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダー等の取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いた三層（Raw / Processed / Feature）スキーマの提供と初期化
- ETL（差分取得・保存・品質チェック）パイプライン
- RSS ベースのニュース収集と銘柄抽出
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ（Zスコア、IC計算 等）
- 監査ログ（Signal → Order → Execution のトレース）用スキーマ
- カレンダー管理・営業日判定、データ品質チェックの実装

設計の重点は「冪等性」「トレーサビリティ」「現実的な運用を考慮した堅牢性（SSRF対策、gzipサイズ制限、DBトランザクション管理等）」です。

---

## 機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch/保存関数: 日足、財務、カレンダー）
  - レート制限（120 req/min 固定間隔）、リトライ、401 の自動トークンリフレッシュ
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）
- ETL
  - 差分更新（最終取得日の把握 → 必要な範囲のみ取得）
  - バックフィル（API 後出し修正の吸収）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - run_daily_etl による一括実行
- ニュース収集
  - RSS フィード取得（gzip 対応、最大受信バイト制限、SSRF ガード）
  - テキスト前処理、記事 ID（正規化 URL の SHA-256 先頭 32 文字）
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4桁コード）
- リサーチ / 特徴量
  - モメンタム・バリュー・ボラティリティの計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー
- スキーマ管理
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_schema 等で初期化
- カレンダー管理
  - 営業日判定、next/prev 営業日取得、カレンダー更新ジョブ
- 監査ログ
  - signal_events、order_requests、executions など監査用テーブル群
- 監視（monitoring）用の名称空間（将来的な拡張）

---

## セットアップ手順

以下はローカル環境での基本的なセットアップ例です。

1. リポジトリをクローン

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例）

   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   本コードで使用される主要外部依存例:
   - duckdb
   - defusedxml

   requirements.txt がない場合は手動でインストール:

   ```
   pip install duckdb defusedxml
   ```

   （実運用では requests 等を追加するかもしれません。プロジェクトの requirements.txt を参照してください。）

4. 環境変数の設定

   プロジェクトは .env または環境変数を参照します。自動読み込み機能はプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須は明示）:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — allowed: development / paper_trading / live （デフォルト development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化

   Python REPL やスクリプトから:

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

   監査ログ専用 DB を初期化する場合:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（基本例）

以下は主要なユースケースの簡単な使用例です。

- 日次 ETL 実行

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # 初回は init_schema、既存 DB に接続するだけなら get_connection
  conn = init_schema("data/kabusys.duckdb")

  result = run_daily_etl(conn)  # 今日を対象に ETL 実行
  print(result.to_dict())
  ```

- ニュース収集ジョブ

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes を与えると記事と銘柄の紐付けを自動で実行
  known_codes = {"7203", "6758", "9984"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count, ...}
  ```

- ファクター計算 / リサーチ

  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # 将来リターンを計算して IC を求める例
  fwd = calc_forward_returns(conn, target, horizons=[1,5])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

  # Zスコア正規化
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- スキーマ初期化済みかチェックやユーティリティ

  - market_calendar を使った営業日判定、next/prev_trading_day 等は `kabusys.data.calendar_management` に実装されています。
  - 品質チェックは `kabusys.data.quality.run_all_checks(conn, target_date=...)` で実行できます。

---

## ディレクトリ構成（抜粋）

主要なモジュールとファイル構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得＋保存）
    - news_collector.py        — RSS ニュース収集・保存
    - schema.py                — DuckDB スキーマ定義・init_schema
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — 特徴量ユーティリティ（再エクスポート）
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py   — マーケットカレンダー管理
    - etl.py                   — ETL 公開インターフェース（ETLResult）
    - audit.py                 — 監査ログスキーマ初期化
    - quality.py               — 品質チェック
  - research/
    - __init__.py              — 研究用 API 再エクスポート
    - feature_exploration.py   — 将来リターン / IC / サマリー
    - factor_research.py       — モメンタム / バリュー / ボラティリティ計算
  - strategy/                  — （将来的に戦略モデル）
  - execution/                 — （発注／ブローカー連携）
  - monitoring/                — （監視機能の名前空間）

（README の範囲のためファイルを抜粋しています。詳細はソースを参照してください。）

---

## 注意事項 / 設計上のポイント

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動でロードします。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB のファイルパス
  - デフォルト: data/kabusys.duckdb（settings.duckdb_path）
  - 初回は init_schema() を実行してテーブルを作成してください。

- J-Quants API
  - レート制限: 120 req/min を守る実装（固定間隔スロットリング）
  - リトライ: ネットワーク系や 429/408/5xx に対して指数バックオフ（最大 3 回）
  - 401 は refresh token で自動更新して 1 回だけ再試行

- セキュリティ / 安全性
  - RSS 取得は SSRF 対策（リダイレクト先の検査、プライベートIP遮断）やレスポンスサイズ上限（デフォルト 10MB）あり
  - XML パースに defusedxml を使用
  - DB 保存は可能な限り冪等（ON CONFLICT）にしてあるため再実行しても二重登録を抑止

---

## 今後の拡張 / 注意点

- strategy / execution / monitoring 名前空間は用意されていますが、ブローカー接続や実取引ロジックの実装は必要に応じて追加してください。
- 運用時はログ、監視、アクセス管理（API トークンの保管）に十分配慮してください。
- production（live）モードでは想定外の発注を避けるための安全弁（paper_trading での十分なテスト）を推奨します。

---

必要であれば、README に含める更に詳しい CLI 実行例、docker-compose サンプル、requirements.txt の具体的な候補、または各モジュールの API リファレンス（関数一覧・引数詳細）も作成いたします。どの章を拡張しますか？