# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータ基盤・リサーチ・戦略実行を想定したライブラリ群です。DuckDB をデータレイクとして利用し、J-Quants API からのデータ取得、ETL、品質検査、ファクター計算、ニュース収集、監査ログなど一連の機能を提供します。本リポジトリはライブラリとして利用し、アプリケーション（バッチ/監視/実行コンポーネント）を組み合わせて運用する設計です。

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（必須/任意）
- 使い方（簡易コード例）
- ディレクトリ構成と主要モジュール説明
- 開発メモ・注意点

---

## プロジェクト概要
KabuSys は以下の層をサポートする Python パッケージです。
- Data layer: J-Quants からの株価・財務・市場カレンダー・ニュース等の取得と DuckDB への保存（冪等保存）
- ETL: 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- Research: ファクター計算（モメンタム、ボラティリティ、バリュー等）と評価ユーティリティ（IC、サマリー、Zスコア正規化）
- News collector: RSS からのニュース収集、記事正規化、銘柄抽出、DB 登録
- Audit: 発注〜約定までのトレース用監査スキーマ
- Execution/Strategy/Monitoring: パッケージ構造は用意されており、戦略・発注ロジック・監視機能を組み込めるようになっています

設計方針として「外部 API 呼び出しを限定して DuckDB と純粋なロジックで完結する」「冪等性・トレーサビリティ・SSRF 等セキュリティ考慮」「テスト容易性を意識したトークン注入／自動リフレッシュ」などが盛り込まれています。

---

## 主な機能
- J-Quants API クライアント（レートリミット管理、リトライ、トークン自動更新）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（日次差分取得、カレンダー先読み、品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ファクター評価ツール（将来リターン計算、IC 計算、統計サマリー、Z スコア正規化）
- RSS ベースのニュース収集（URL 正規化、トラッキング除去、SSRF 対策、記事ID生成、銘柄抽出）
- 監査ログスキーマ（signal → order_request → executions のトレース）

---

## 前提条件
- Python 3.10 以上（型注釈に Union | 形式を使用）
- 以下主要ライブラリ（pip でインストール）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）
- J-Quants / Slack / kabu API などの認証情報（環境変数で指定）

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトとして配布される場合は pyproject.toml / requirements.txt に従ってください）

3. リポジトリをインストール（開発インストール例）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（と必要なら `.env.local`）を作成してください。
   - 自動で .env をロードする機能があり、優先順位は:
     OS 環境変数 > .env.local > .env
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマ初期化（例）
   - Python コンソールやスクリプトで初期化します（デフォルト DB パスは settings.duckdb_path）。
   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

6. 監査ログ用 DB 初期化（必要に応じて）
   - from kabusys.data import audit
     conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数（主なもの）

必須（実行する機能に応じて）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（fetch API 用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必要であれば）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（"1" 等）
- KABUSYS の DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB 等: data/monitoring.db）

注意: Settings クラスは必須項目未設定時に ValueError を投げます。`.env.example` を参考にして作成してください。

---

## 使い方（簡単なコード例）

- DuckDB スキーマ初期化
  - from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants トークンは settings から自動取得）
  - from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # デフォルトは本日を対象
    print(result.to_dict())

- ニュース収集ジョブ（RSS）
  - from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import init_schema
    conn = init_schema(":memory:")  # テスト用
    # known_codes: 銘柄抽出に利用するコード集合（任意）
    known_codes = {"7203", "6758", "9984"}
    stats = run_news_collection(conn, known_codes=known_codes)
    print(stats)

- ファクター計算（例: モメンタム）
  - from kabusys.research.factor_research import calc_momentum
    conn = schema.get_connection("data/kabusys.duckdb")
    recs = calc_momentum(conn, date(2024, 1, 31))
    # z-score 正規化
    from kabusys.data.stats import zscore_normalize
    normalized = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

- 将来リターンと IC 計算
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
    fwd = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
    ic = calc_ic(factor_records=recs, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
    print(ic)

これらはライブラリ API の一例です。詳細は各モジュールの docstring（コード内コメント）を参照してください。

---

## ディレクトリ構成（主要ファイルと説明）
以下は src/kabusys 配下の主なモジュールです（抜粋）。

- kabusys/
  - __init__.py  — パッケージ定義（バージョン等）
  - config.py    — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（レート制御、リトライ、保存ユーティリティ）
    - news_collector.py      — RSS 取得・正規化・DB 保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・init（raw/processed/feature/execution）
    - pipeline.py            — ETL パイプライン（差分取得 / 品質チェック）
    - features.py            — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — 市場カレンダーの判定・更新ジョブ
    - audit.py               — 監査ログスキーマ（signal / order_request / executions）
    - stats.py               — 統計ユーティリティ（Z スコア正規化）
    - etl.py                 — ETL 結果クラス再エクスポート
    - quality.py             — データ品質チェック群
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算・IC・ファクターサマリー等
  - strategy/                — 戦略関連（パッケージ骨組み）
  - execution/               — 発注 / ブローカー連携（骨組み）
  - monitoring/              — 監視・アラート（骨組み）

各モジュールは docstring に設計意図や制約が記載されているため、内部実装や振る舞いを理解する際に参照してください。

---

## 開発メモ・注意点
- J-Quants API 利用制限: デフォルトで 120 req/min を想定し、内部でスロットリングとリトライを実装しています。大量データ一括取得の際は注意してください。
- DuckDB の SQL 文実行にはパラメータバインド（?）を使用しています（SQL インジェクション対策）。
- ニュース収集では SSRF 対策（スキーム検査、ホストのプライベート判定、リダイレクト検査）や受信サイズ制限を備えています。
- Z スコア正規化や IC 計算は外部ライブラリを使わず標準ライブラリで実装されています。大規模データでのパフォーマンスや数値安定性は運用に合わせ検証してください。
- 本パッケージ自体は「フレームワーク/ライブラリ」であり、実際の自動売買を行う場合は発注ロジック、リスク管理、監視、ロギング、オペレーション手順を別途実装し厳密にテストしてください。
- 実運用（live）環境では settings.is_live を参照して発注系の有効/無効を判定するなど安全対策を組み込んでください。

---

もし README に追加したいサンプルスクリプト（cron ジョブ例、Dockerfile、CI 用のテストコマンドなど）があれば要件を教えてください。サンプルやコマンド例を追記します。