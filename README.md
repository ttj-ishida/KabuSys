# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株を対象としたデータパイプライン・研究・監査・発注基盤のプロトタイプ実装です。DuckDB をデータレイクとして使い、J-Quants API や RSS からデータを取得・整形し、特徴量計算・品質チェック・ETL を行えるよう設計されています。

主な設計方針
- DuckDB を中核に置いた 3 層（Raw / Processed / Feature）データモデル
- J-Quants API のレート制御、リトライ、トークン自動更新を備えたクライアント
- RSS ニュース収集での SSRF 対策・サイズ制限・トラッキングパラメータ除去
- ETL は差分更新（バックフィルあり）・品質チェックを一貫して実行
- 監査ログ（order / execution）のための専用スキーマを提供

---

## 機能一覧

- 環境変数管理
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- データ取得（J-Quants）
  - 株価日足（OHLCV）、四半期財務諸表、JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）・リトライ・401 自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）

- ニュース収集
  - RSS フィードから記事を収集、テキスト前処理、SHA-256 ベースの冪等 ID、銘柄コード抽出、DuckDB 保存
  - SSRF 対策・受信サイズ制限・XML の安全なパース

- ETL パイプライン
  - 差分更新（最終取得日から自動算出）、バックフィル、品質チェックの実行
  - 日次 ETL のエントリポイント（run_daily_etl）

- データスキーマ管理
  - DuckDB 用の DDL（raw_prices, prices_daily, raw_financials, features, signals, orders, executions, audit テーブル等）の初期化（init_schema / init_audit_schema）

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマンランク相関）、Z スコア正規化など

---

## セットアップ手順

前提
- Python 3.9+
- ネットワーク接続（J-Quants API、RSS）

1. リポジトリの取得と仮想環境
   - 任意の方法でソースをクローンし、仮想環境を作成します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要なライブラリ例:
     - duckdb
     - defusedxml
   - pip でインストール:
     - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e .）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を作成します。
   - 自動読み込み順序:
     - OS 環境変数 > .env.local > .env
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

   - 例 .env（最小）
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. データベース初期化
   - DuckDB スキーマを作成:
     - Python から:
       from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を作る（任意）:
       from kabusys.data.audit import init_audit_db
       audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な API と実行例）

- DuckDB 接続の取得
  - 初期化（テーブル作成を含む）
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

  - 既存 DB へ接続（初回は init_schema を推奨）
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")

- 日次 ETL 実行
  - run_daily_etl によりカレンダー・株価・財務の差分取得と品質チェックを実行:
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())

- ニュース収集ジョブ
  - RSS から記事取得して DuckDB に保存:
    from kabusys.data.news_collector import run_news_collection
    counts = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
    print(counts)

- J-Quants からの個別取得
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar:
    from kabusys.data.jquants_client import fetch_daily_quotes
    recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))

- 特徴量・研究ユーティリティ
  - モメンタム等の計算（DuckDB 接続と基準日を渡す）
    from datetime import date
    from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
    mom = calc_momentum(conn, date(2024,1,31))
    vol = calc_volatility(conn, date(2024,1,31))
    val = calc_value(conn, date(2024,1,31))
  - 将来リターン・IC 計算:
    from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
    fwd = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
    ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")

- データ品質チェック
  - 個別または一括で実行:
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2024,1,31))
    for i in issues: print(i)

- 環境設定の参照
  - settings 経由でアプリ設定を取得:
    from kabusys.config import settings
    print(settings.duckdb_path, settings.env, settings.is_live)

---

## ディレクトリ構成（主要ファイル）

（リポジトリのルート以下に src/kabusys 配下で実装されています）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース取得・前処理・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — 特徴量の薄い公開インターフェース
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログスキーマ初期化
    - etl.py                 — ETL 公開型インターフェース（ETLResult 再エクスポート）
    - stats.py               — Z スコアなど統計ユーティリティ
    - quality.py             — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / サマリー等
    - factor_research.py     — Momentum/Volatility/Value 計算
  - strategy/                — 戦略層（placeholder / 実装を追加する想定）
  - execution/               — 発注 / 実行管理（placeholder）
  - monitoring/              — 監視用モジュール（placeholder）

---

## 注意点・運用メモ

- .env 自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml）から .env を探し、.env → .env.local の順で読み込みます。OS 環境変数は上書きされません（ただし .env.local は既存の OS 環境変数を上書きしないよう保護されます）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化できます（テスト時に有用）。

- J-Quants API のリクエストはレート制御（120 req/min）に従います。大量取得時は処理時間を考慮してください。

- DuckDB の INSERT / ON CONFLICT を利用して冪等性を担保していますが、外部から DB を直接操作する場合は注意してください。

- NewsCollector は外部 RSS を取得するので、公開環境ではアクセス先の信頼性・頻度に注意してください。

- KABUSYS_ENV は運用モードを切り替えます（development / paper_trading / live）。live モードでは実取引に関連する安全チェックを追加する想定です（実装はプロジェクトに依存します）。

---

## 貢献 / 拡張

- strategy / execution / monitoring ディレクトリはエントリポイントのみが用意されています。戦略実装、発注連携（証券会社 API）、監視アラートを追加してフルスタックに拡張できます。
- テスト: 各モジュールは依存注入（例: id_token、conn、_urlopen のモック化）に配慮して設計されています。ユニットテストを追加して安全性を高めてください。

---

README は以上です。必要であれば、README に含める具体的なコマンド例（Dockerfile / systemd ジョブ / CI ワークフロー等）や .env.example の雛形、よくあるトラブルシューティングを追加できます。どの部分を詳しく書き足しましょうか？