# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームライブラリです。  
DuckDB をストレージに用い、J-Quants API から市場データや財務データ・JPX カレンダーを取得し、ETL / 品質チェック / 特徴量計算 / ニュース収集 / 監査ログなどの機能を提供します。

主な設計方針
- DuckDB ベースでローカルにデータを保持（冪等な INSERT/UPDATE）
- Research（バックテスト・因子探索）は外部発注や本番 API にアクセスしない
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新付き
- ニュース収集は SSRF 対策・トラッキング除去・サイズ制限等の安全対策を実装

バージョン: 0.1.0

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出、無効化可能）
  - 必須設定の取得・検証（`kabusys.config.settings`）
- Data（DuckDB 周り）
  - スキーマ定義 & 初期化（raw / processed / feature / execution 層）
  - DuckDB 接続ハンドラ
  - ETL パイプライン（価格・財務・カレンダーの差分取得と保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - カレンダー管理（営業日の判定、next/prev/trading days）
  - 監査ログ（シグナル→発注→約定 をトレースする監査スキーマ）
- Data 接続クライアント
  - J-Quants API クライアント（ページネーション、レートリミット、リトライ、トークン自動更新）
- News
  - RSS フィード取得・前処理・正規化・DB 保存（SSRF 防止 / サイズ制限 / トラッキング除去）
  - 銘柄コード抽出と news_symbols への紐付け
- Research（因子計算）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z-score 正規化ユーティリティ
- Strategy / Execution / Monitoring：基本パッケージ構成（エントリポイントを整理済み）

---

## 前提（Prerequisites）

- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - defusedxml

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクトをパッケージとして扱う場合は pyproject.toml / setup があれば:
```
pip install -e .
```

---

## 環境変数（代表例）

自動で `.env` / `.env.local` がプロジェクトルートからロードされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。必須項目は Settings で require されます。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABUS_API_BASE_URL : kabuAPI の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV : execution 環境 (development|paper_trading|live)
- LOG_LEVEL : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   ```
   git clone <repo_url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに pyproject / requirements.txt があればそれを利用）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定
   - 自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで次を実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を使う場合:
     ```python
     from kabusys.data.audit import init_audit_db
     aconn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要ユースケース）

以下は代表的な利用例です。

- ETL（日次パイプライン）を実行する
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を与えなければ今日（営業日に調整）まで処理
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # sources: {source_name: rss_url} を渡せます。known_codes は銘柄抽出用のコード集合。
  res = run_news_collection(conn, known_codes={"7203","6758","9984"})
  print(res)  # ソースごとの新規保存件数
  ```

- J-Quants からデータを取得して保存する（lower-level）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 因子 / 研究用ユーティリティ
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  from kabusys.data.stats import zscore_normalize
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  t = date(2024, 2, 1)

  mom = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)

  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

  # z-score 正規化
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 注意事項 / セーフティ設計

- J-Quants クライアントは 120 req/min のレート制限に準拠するため内部でスロットリングしています。
- HTTP エラー（408/429/5xx）に対してリトライ（指数バックオフ）を行います。401 はリフレッシュトークンで自動更新して 1 回リトライします。
- NewsCollector は SSRF 対策（リダイレクト検査・プライベート IP 拒否）、受信サイズ制限、gzip 解凍後サイズ検査、XML パース安全化（defusedxml）などを実装しています。
- DuckDB への保存はできるだけ冪等（ON CONFLICT）で行うように設計されています。
- デフォルトで .env を自動読み込みしますが、テストなどで不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## ディレクトリ構成（主要ファイル）

(リポジトリ内の `src/kabusys` 配下を抜粋)

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（fetch/save）
    - news_collector.py                 — RSS ニュース収集 / 保存 / 銘柄抽出
    - schema.py                         — DuckDB スキーマ定義 & init_schema
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - features.py                       — 特徴量ユーティリティ（公開インターフェース）
    - calendar_management.py            — マーケットカレンダー管理
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログスキーマ & 初期化
    - etl.py                            — ETL 型の再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py            — 将来リターン / IC / 統計サマリ等
    - factor_research.py                — Momentum/Value/Volatility の計算
  - strategy/                            — 戦略層（パッケージ化済み）
  - execution/                           — 発注 / 実行層（パッケージ化済み）
  - monitoring/                          — 監視用モジュール（パッケージ化済み）

---

## 貢献と開発

- 開発環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動読み込みを無効化できます。
- 単体テストや型チェックを追加することで品質向上が図れます（pytest / mypy 等の導入推奨）。
- 新しい ETL ジョブやフィードを追加する際は、冪等性・例外処理・ログ出力・テストを重視してください。

---

以上が README の概要です。必要であれば、README に含める具体的なコマンド例、.env.example ファイル、あるいは CI / デプロイ手順のテンプレートを追加で作成しますか？