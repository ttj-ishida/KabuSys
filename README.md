# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（軽量プロトタイプ）

このリポジトリは日本株のデータ収集（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログなどを含むデータ基盤・研究用ユーティリティ群を提供します。実際の発注ロジックやブローカー連携は分離されており、研究→バッチ→実運用の各段階で利用できるよう設計されています。

主な用途例:
- J-Quants からの株価・財務・カレンダー取得と DuckDB への保存
- ETL（差分取得・バックフィル）およびデータ品質チェックの実行
- RSS を使ったニュース収集と銘柄紐付け
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算と IC/サマリー分析
- 監査ログ（シグナル→発注→約定トレーサビリティ）用スキーマ初期化

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得・保存（DuckDB）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損値、スパイク検出、重複、日付整合性チェック（QualityIssue を返す）
- ニュース収集
  - RSS フィードの安全な取得（SSRF対策、gzip上限、XML安全パース）、raw_news 保存、銘柄抽出
- スキーマ / DB ユーティリティ
  - DuckDB スキーマ初期化（init_schema）、監査スキーマ初期化（init_audit_schema / init_audit_db）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティなどのファクター計算（prices_daily / raw_financials 前提）
  - 将来リターン計算、IC（Spearman）、ファクター要約（median/mean/std）
  - z-score 正規化ユーティリティ
- カレンダー管理
  - 営業日判定、前後営業日取得、カレンダー更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 用スキーマ、トレーサビリティ設計

---

## セットアップ手順

前提:
- Python 3.9+（typing の書き方に依存）
- DuckDB を利用（Python duckdb パッケージ）
- defusedxml（RSS パースの安全化）

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（例）
   必要なパッケージはプロジェクトに合わせて適宜追加してください。最低限:
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数の用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   主な環境変数（必須は明記）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注等で使用）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DB ディレクトリの作成（必要に応じて）
   DuckDB のファイルを格納する親ディレクトリを作成しておくと良いです（init_schema が自動作成しますが手動でも可）。

---

## 使い方 (主要例)

以下は Python REPL / スクリプトでの基本的な使い方例です。

- スキーマ初期化（DuckDB）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path は環境変数 DUCKDB_PATH を参照
  conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して初期化
  ```

- 日次 ETL 実行（差分取得・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema で作成した DuckDB 接続
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効なコード集合（例: set of "7203" 等）
  stats = run_news_collection(conn, known_codes={"7203","6758"})
  print(stats)  # {source: 新規保存件数, ...}
  ```

- 監査スキーマの初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用: ファクター計算 & IC 計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary, rank
  from kabusys.data.stats import zscore_normalize
  from datetime import date

  target = date(2025, 1, 15)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # 将来リターンを計算して IC を出す（例: mom_1m と fwd_1d の関係）
  fwd = calc_forward_returns(conn, target, horizons=[1])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

  # Z スコア正規化
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- J-Quants クライアント利用（直接データ取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  # id_token は省略可（モジュール内でリフレッシュトークンから取得）
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  ```

---

## 重要な動作・仕様の注意点

- 環境変数自動ロード:
  - パッケージ起点でプロジェクトルート (.git または pyproject.toml を基準) を探索し .env / .env.local を自動で読み込みます。
  - 無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで便利）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。override の挙動・保護キーの扱いについては config モジュールを参照。

- J-Quants クライアント:
  - レート制限 120 req/min を固定間隔スロットリングで守ります。
  - 408/429/5xx 系はリトライ、401 は自動トークンリフレッシュで 1 回リトライします。
  - 取得データに fetched_at を付与して Look-ahead Bias を回避します。

- NewsCollector:
  - RSS の取得は SSRF や XML Bomb 対策（ホストのプライベート判定、defusedxml、受信バイト上限）を実施します。
  - 記事IDは URL 正規化（tracking パラメータ除去）後の SHA-256 の先頭 32 文字で生成します（冪等性）。

- DuckDB スキーマ:
  - init_schema は冪等でテーブル・インデックスを作成します。
  - 監査スキーマは別途 init_audit_schema / init_audit_db により追加できます。
  - 一部外部キー制約や ON DELETE 動作は DuckDB のバージョン特性上制限（コメント参照）があります。

- 環境値バリデーション:
  - KABUSYS_ENV は development / paper_trading / live のいずれかでなければ例外になります。
  - LOG_LEVEL は標準的なログレベルのみ許容します。

---

## ディレクトリ構成

主要ファイル/モジュール一覧（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得 & 保存）
    - news_collector.py               — RSS ニュース収集・保存・銘柄抽出
    - schema.py                       — DuckDB スキーマ定義 / init_schema
    - stats.py                        — 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py                     — ETL パイプライン（差分取得・日次 ETL）
    - features.py                     — features 公開インターフェース（zscore 等）
    - calendar_management.py          — マーケットカレンダー管理（営業日ロジック等）
    - audit.py                        — 監査ログスキーマ・初期化
    - etl.py                          — ETLResult の公開
    - quality.py                      — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py          — 将来リターン・IC・要約等
    - factor_research.py              — モメンタム / ボラティリティ / バリュー計算
  - strategy/                          — 戦略層（実装場所、現在はパッケージ空）
  - execution/                         — 発注/実行層（実装場所、現在はパッケージ空）
  - monitoring/                        — 監視関連（パッケージ空）

（README に書かれた構成はコードベースからの抜粋です。詳細は各モジュールの docstring を参照してください）

---

## 開発・テスト

- 単体テストを追加する場合:
  - config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で抑止できます。
  - jquants_client._urlopen / news_collector._urlopen 等は外部呼び出しをモック可能に設計されています。

---

## ライセンス / 貢献

- 本 README にはライセンス情報は含まれていません。実リポジトリでは LICENSE を用意してください。
- バグ報告・機能提案は Issue を立ててください。プルリクエストは歓迎します。

---

上記はこのコードベースの主要機能と使い方の概要です。各モジュールに詳細な docstring があり、関数単位での使い方・引数仕様が記載されています。初めは schema.init_schema() → run_daily_etl() を順に実行してデータ基盤を整える流れを推奨します。必要であれば README に入れる具体的な CLI / サービス起動方法や追加サンプルを作成します。