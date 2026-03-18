# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
DuckDB をバックエンドに用いたデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、ファクター計算（研究用）等のユーティリティ群を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- 環境変数 / .env の自動読み込みと設定管理（kabusys.config）
  - 自動的にプロジェクトルートを探索して `.env` / `.env.local` を読み込み
  - 必須設定の取得補助（例: JQUANTS_REFRESH_TOKEN 等）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得
  - レート制御（120 req/min）・リトライ（指数バックオフ）・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ETL（差分更新）パイプライン（kabusys.data.pipeline）
  - 日次ETL: カレンダー取得 → 株価差分取得（バックフィル）→ 財務データ取得 → 品質チェック
  - 品質チェック（欠損、重複、スパイク、日付不整合）を実行
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - raw / processed / feature / execution / audit 層のテーブル定義を含む
  - init_schema / get_connection を提供
- ニュース収集（RSS）モジュール（kabusys.data.news_collector）
  - RSS フィード取得・前処理・記事ID生成（URL正規化→SHA256）・冪等保存
  - SSRF・XML Bomb・受信サイズ上限などセキュリティ対策を実装
  - 記事から銘柄コード抽出・news_symbols 紐付け機能
- ファクター計算・研究ツール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 先行リターン計算、IC（スピアマンρ）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（audit）向けスキーマ（kabusys.data.audit）
  - シグナル→発注要求→約定のトレーサビリティを確保するテーブル群、初期化関数

（strategy、execution、monitoring パッケージはプレースホルダとして存在）

---

## 前提条件

- Python 3.9+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）
- 必要な環境変数（下記参照）

※ 実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係が定義されている想定です。最小限の実行に必要な依存は上記です。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリへ
   - 例: git clone ... && cd your-repo

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

3. 必須パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージを editable インストールする場合）pip install -e .

4. 環境変数を用意
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。
   - 自動ロードはデフォルトで有効。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: `.env`（最低限）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456789
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db

---

## 主な環境変数と設定

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

注意: Settings クラス（kabusys.config.settings）は必須値が未定義の場合に ValueError を発生させます。

---

## 使い方（簡単なコード例）

以下は Python REPL やスクリプトから利用する基本例です。

- DuckDB スキーマ初期化
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")  # :memory: も可

- 日次 ETL 実行（J-Quants から差分取得して保存）
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date は省略で今日
    print(result.to_dict())

- ニュース収集（RSS）ジョブを実行して DB に保存
    from kabusys.data.news_collector import run_news_collection
    # known_codes に有効な銘柄コード集合を渡すと記事→銘柄紐付けを試みる
    res = run_news_collection(conn, known_codes={"7203", "6758"})
    print(res)

- ファクター計算（研究用）
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
    from datetime import date
    target = date(2024, 1, 10)
    mom = calc_momentum(conn, target)
    vol = calc_volatility(conn, target)
    val = calc_value(conn, target)
    fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
    ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")  # 例
    summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
    normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- J-Quants から日次株価を直接取得（ページネーション対応）
    from kabusys.data.jquants_client import fetch_daily_quotes
    records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
    print(len(records))

--- 

## 実装上の注意・設計ポイント（簡潔に）

- J-Quants クライアントは 120 req/min のレート制御、リトライ、トークン自動リフレッシュなどを備える（get_id_token, _RateLimiter）。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を使用。
- NewsCollector は SSRF 回避、受信サイズ上限（10MB）、gzip 解凍後のサイズチェック、defusedxml を使った XML パースなどセキュリティ考慮済み。
- ETL は差分更新とバックフィル戦略（デフォルト 3 日）を採用し、品質チェックは Fail-Fast とせず問題を収集して報告する設計。

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - audit.py
  - etl.py
  - quality.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py  (プレースホルダ)
- execution/
  - __init__.py  (プレースホルダ)
- monitoring/
  - __init__.py  (プレースホルダ)

（README に掲載したファイル一覧はコードベース内の主要モジュールを抜粋したものです）

---

## 貢献・拡張のヒント

- strategy や execution の実装を追加して、シグナル→発注フローを実装できます。
- モデルや特徴量の追加は research / data.features モジュールを拡張して行えます。
- CI・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動ロードを無効化すると良いです。
- DuckDB スキーマは init_schema / init_audit_schema を使えば安全に初期化できます。既存データの移行時はバックアップを忘れずに。

---

## ライセンス・連絡先

この README はコードから作成された概要ドキュメントです。実際のライセンスや連絡先はプロジェクトのルート（LICENSE / CONTRIBUTORS 等）を参照してください。

---

必要であれば、README に含めるサンプル .env.example の内容や、CI 用の実行例（GitHub Actions での ETL 実行等）も作成できます。どの情報を追加しますか？