# KabuSys

日本株向け自動売買＆データプラットフォームのライブラリ群（KabuSys）。  
DuckDB をデータストアに用い、J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、ETL／品質チェック／特徴量生成／ニュース収集／監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は下記のような用途を想定した Python モジュール群です。

- J-Quants API からの差分データ取得（株価日足、財務）と DuckDB への冪等保存
- JPX マーケットカレンダー管理（祝日・半日・SQ）
- RSS ベースのニュース収集と銘柄抽出
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と評価指標（IC）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- 軽量な ETL パイプライン（run_daily_etl）

設計方針のポイント:
- DuckDB を中心に SQL + Python で効率的に処理
- 冪等（ON CONFLICT DO UPDATE/DO NOTHING）を重視
- 本番発注 API へは研究モジュールがアクセスしない（安全性）
- 外部依存は最小限（標準ライブラリ中心、ただし duckdb, defusedxml を使用）

---

## 主な機能一覧

- データ取得・保存
  - J-Quants から日足（OHLCV）・財務データ・マーケットカレンダーを取得（ページネーション対応、レートリミット/リトライ処理）
  - DuckDB のスキーマ定義と初期化（data.schema.init_schema）
  - 冪等保存用ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar 等）

- ETL / 運用
  - 差分更新とバックフィル対応の ETL（data.pipeline.run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 品質チェック（data.quality.run_all_checks）

- ニュース収集
  - RSS フィード取得・前処理・記事保存（data.news_collector）
  - 銘柄コード抽出（テキストから4桁コードを抽出して news_symbols に紐付け）

- 研究・特徴量
  - モメンタム / ボラティリティ / バリューの計算（research.factor_research）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリー（research.feature_exploration）
  - Z-score 正規化ユーティリティ（data.stats.zscore_normalize）

- マーケットカレンダー管理
  - 営業日判定や前後の営業日取得、夜間カレンダー更新ジョブ（data.calendar_management）

- 監査ログ（Audit）
  - signal_events, order_requests, executions 等の監査用スキーマ初期化（data.audit.init_audit_db / init_audit_schema）

---

## 前提条件

- Python 3.10 以上（型ヒントに | 演算子、match ではないが新しい型記法を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

※標準ライブラリの urllib 等も使用します。必要に応じて仮想環境を用意してください。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

自動的にプロジェクトルート（.git か pyproject.toml が存在するディレクトリ）から `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境（development, paper_trading, live）デフォルト development
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）デフォルト INFO

上記は `kabusys.config.settings` からアクセスできます。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする。
   - 必要パッケージ: duckdb, defusedxml（他にロギング設定やテストフレームワークを好みで追加）

2. .env ファイルを作成する（プロジェクトルートに配置）。
   - .env.example があれば参考に必要な値を設定してください（J-Quants トークン等）。

3. DuckDB スキーマの初期化
   - Python REPL / スクリプトで以下を実行してデータベースとテーブルを作成します:

   例:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

4. 監査ログ DB が別 DB に欲しい場合:
   例:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（代表例）

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェックを一括で実行）
  例:
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL（株価差分）:
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- ニュース収集ジョブの実行:
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードの集合 (例: {"7203","6758",...})
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)

- 研究用のファクター計算（例: モメンタム）
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2025,1,31))

- 将来リターンと IC（例）:
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, date(2025,1,31))
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")

- Zスコア正規化:
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

注意: 上記の関数は DuckDB の特定テーブル（prices_daily / raw_financials / market_calendar 等）を参照します。まず ETL で該当データを取得・保存しておく必要があります。

---

## 初期化スニペット例（まとめ）

1) DB スキーマ初期化
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) 監査ログ初期化（別DB）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

3) ETL 実行
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)
print(res.to_dict())

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py        # J-Quants API クライアント（取得/保存ロジック）
  - news_collector.py       # RSS ニュース収集 / 前処理 / DB 保存
  - schema.py               # DuckDB スキーマ定義・初期化
  - stats.py                # 統計ユーティリティ（zscore_normalize）
  - pipeline.py             # ETL パイプライン（run_daily_etl 等）
  - features.py             # 特徴量ユーティリティ（再エクスポート）
  - calendar_management.py  # マーケットカレンダー管理ユーティリティ
  - audit.py                # 監査ログ（signal/order/execution 用スキーマ）
  - etl.py                  # ETL 関連の公開インターフェース
  - quality.py              # データ品質チェック
- research/
  - __init__.py
  - feature_exploration.py  # 将来リターン / IC / summary 等
  - factor_research.py      # Momentum/Volatility/Value の計算
- strategy/
  - __init__.py            # （戦略関連：未実装/拡張ポイント）
- execution/
  - __init__.py            # （発注・ブローカ連携：拡張ポイント）
- monitoring/
  - __init__.py            # （監視・メトリクス：拡張ポイント）

---

## 開発ノート / 注意点

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込みます。
  - 環境変数による挙動制御: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化できます。

- J-Quants API の取り扱い:
  - レート制限（120 req/min）やリトライ、401 によるトークン自動リフレッシュ等が組み込まれています。
  - 取得データには fetched_at を付与して Look-ahead Bias の管理に役立てます。

- DuckDB スキーマ:
  - ON CONFLICT を用いて冪等保存を行う設計です。
  - 監査用スキーマは init_audit_schema / init_audit_db で別途初期化できます。

- セキュリティ・堅牢性:
  - RSS 処理では SSRF 対策（リダイレクト先検査・プライベートアドレス遮断）、gzip サイズチェック、defusedxml での XML パース防御を行っています。

---

## 拡張ポイント

- strategy / execution / monitoring パッケージは拡張が想定されています。自動発注機能やポジション管理、外部ブローカー向けコネクタを追加することが可能です。
- 特徴量や AI スコアを増やし、signals → order_request → executions の監査連鎖を活用した運用フローを実装できます。

---

ご不明点や README に追加したい実例（CLI の例、Dockerfile サンプル、Unit tests の実行方法など）があれば教えてください。README を用途（開発者向け / 運用向け）に合わせてカスタマイズします。