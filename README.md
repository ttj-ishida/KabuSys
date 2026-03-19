# KabuSys

日本株向けの自動売買基盤ライブラリ。データ取得（J-Quants）、ETL、データ品質チェック、特徴量生成、リサーチ（ファクター解析）、ニュース収集、監査ログなどを備え、戦略実装・発注層と連携できるよう設計されたコンポーネント群を提供します。

## 特徴（概要）
- DuckDB を用いたローカルデータレイク（Raw / Processed / Feature / Execution 層）
- J-Quants API クライアント（レート制限・リトライ・トークン自動更新対応）
- ETL パイプライン（日次差分更新・バックフィル・品質チェック組み込み）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース（RSS）収集器（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- ファクター計算・IC評価・統計サマリー（duckdb 接続を受ける研究用ユーティリティ）
- 監査ログ（シグナル→オーダー→約定のトレーサビリティテーブル）
- 設定管理（.env/.env.local の自動読み込み、環境変数経由の設定）

---

## 主な機能一覧
- data/jquants_client.py
  - J-Quants からの株価、財務、マーケットカレンダー取得（ページネーション対応）
  - 取得データの DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）
  - レートリミット、指数バックオフ、401 時トークンリフレッシュ対応
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - 初期化関数 init_schema()
- data/pipeline.py
  - 差分 ETL（株価 / 財務 / カレンダー）の実行、品質チェック実行、ETLResult を返す
- data/quality.py
  - 欠損、重複、スパイク、日付不整合などのチェック
- data/news_collector.py
  - RSS 取得・前処理・記事 ID 生成（正規化 + SHA-256）・DB 保存・銘柄紐付け
  - SSRF 対策、受信サイズ制限、gzip 解凍や XML パースの安全処理
- data/calendar_management.py
  - market_calendar を扱うユーティリティ（営業日判定、前後営業日取得、夜間更新ジョブ）
- data/audit.py
  - シグナル／発注要求／約定を残す監査用テーブル群の初期化ユーティリティ
- research/
  - factor_research.py: momentum / volatility / value などのファクター計算
  - feature_exploration.py: 将来リターン計算、IC（スピアマン）計算、統計サマリー
  - data.stats（zscore_normalize）を使った正規化ユーティリティ
- config.py
  - 環境変数から設定を取得する Settings（自動 .env ロード機能、必須キーチェック）
- その他
  - execution, strategy, monitoring の雛形パッケージ（発注・戦略・監視層と連携）

---

## セットアップ手順

前提
- Python 3.8+（typing の記述等を考慮）
- DuckDB（Python 用パッケージ）
- defusedxml（RSS パースの安全対策）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動ロードされます（config.py が .git または pyproject.toml を探索して root を特定します）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知に使う Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャネル ID（必須）

任意・デフォルト値あり
- KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化するフラグ（"1" 等で有効化）
- KABUSYS のログレベル: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS の DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視系の SQLite パス（デフォルト data/monitoring.db）
- KABUS_API_BASE_URL    : kabuAPI ベース URL（デフォルト http://localhost:18080/kabusapi）

5. DuckDB スキーマ初期化
   - Python から schema.init_schema() を呼びます。例:
     ```
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を作る場合:
     ```
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な例）

- 設定値参照
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live)
  ```

- スキーマ初期化（DuckDB）
  ```
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants から差分取得 → DB 保存 → 品質チェック）
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブを走らせる
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効な銘柄コードのセット（任意）
  res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(res)
  ```

- J-Quants から株価を直接取得して保存
  ```
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- ファクター計算（リサーチ用途）
  ```
  import duckdb
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2025, 1, 31)
  factors = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print(ic)
  ```

- 市場カレンダー操作
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  print(is_trading_day(conn, date.today()))
  print(next_trading_day(conn, date.today()))
  ```

ログや挙動は Settings の `LOG_LEVEL`、`KABUSYS_ENV` に依存します。`KABUSYS_ENV` が `live` のときは実運用向けのフラグが有効になります（発注ロジック等で参照）。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py
  - パッケージメタ（バージョン等）
- config.py
  - 環境変数/設定管理（.env 自動ロード、必須キー検証）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
  - news_collector.py
    - RSS 取得・前処理・DB保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
  - pipeline.py
    - ETL パイプライン（差分取得、保存、品質チェック）
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management.py
    - market_calendar の管理・営業日ロジック・カレンダー更新ジョブ
  - audit.py
    - 監査ログ用テーブル定義と初期化ユーティリティ
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - features.py
    - 特徴量ユーティリティの公開インターフェース
- research/
  - __init__.py
    - 研究用関数の再エクスポート（calc_momentum 等）
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー
  - factor_research.py
    - Momentum / Volatility / Value ファクター計算
- strategy/
  - __init__.py
  - （戦略ロジックを置くためのパッケージ）
- execution/
  - __init__.py
  - （発注・ブローカ連携の実装用パッケージ）
- monitoring/
  - __init__.py
  - （監視・アラート用の実装を配置）

---

## 設計上の注意点・セキュリティ
- J-Quants のレート制限（120 req/min）を尊重するため固定間隔スロットリングを行います。大量取得の際は注意してください。
- news_collector は SSRF や XML BOM 攻撃、gzip bomb などの対策を組み込んでいますが、外部 RSS を扱う際は信頼できるソースに限定することを推奨します。
- DuckDB の ON CONFLICT を多用して冪等性を担保しています。直接 SQL で DB を編集する際は一貫性に注意してください。
- 設定やトークンは .env に保存する場合、リポジトリ管理下に含めない（.gitignore）ようにしてください。

---

## 開発／貢献
- コードはモジュール毎に分離されており、ユニットテスト・モックを作りやすい設計です（例: news_collector._urlopen をモック可能）。
- 変更を加える場合はドキュメント（DataPlatform.md / StrategyModel.md 等、リポジトリにある想定ドキュメント）を参照し、スキーマ変更は互換性に注意して行ってください。

---

README は以上です。追加で「インストール用の requirements.txt の提案」や「具体的な CI/実運用のデプロイ手順（systemd / cron / Kubernetes など）」が必要であれば、用途に合わせて例を作成します。