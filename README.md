# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
主にデータ収集（J-Quants）、DuckDB ベースのデータ管理、品質チェック、特徴量計算、リサーチユーティリティを提供します。戦略・発注部分の骨組みも含まれており、研究〜本番運用までのワークフローを想定しています。

## 主要機能
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - 日足（OHLCV）、四半期財務、JPX カレンダーの取得・保存
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン
  - 差分取得/バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、記事→銘柄紐付け
- ファクター計算 / リサーチユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリ
- 汎用統計ユーティリティ（Zスコア正規化など）
- 監査ログ（監査用スキーマ / トレーサビリティ）初期化ユーティリティ

## 動作要件（想定）
- Python 3.10+
- 依存ライブラリ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

pip インストール例（仮）:
pip install duckdb defusedxml

※ 実際の運用では他にログ・Slack 連携等の依存がある可能性があります。

## 環境変数 / 設定
KabuSys は .env / .env.local または OS 環境変数から設定を自動ロードします（プロジェクトルートは .git または pyproject.toml を探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings で参照される環境変数）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 投稿先チャンネル ID（必須）

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のベース URL （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（Monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

.env 例（最低限の必須項目を記載）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## セットアップ手順（概要）
1. Python 3.10+ 環境を用意する（virtualenv / venv を推奨）
2. 必要パッケージをインストールする（duckdb, defusedxml 等）
3. プロジェクトルートに .env を作成し、必要な環境変数を設定
4. DuckDB スキーマを初期化する
   - 例: Python スクリプト内で
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
5. 監査ログ用スキーマを追加する（必要に応じて）
   - 例:
     from kabusys.data import audit
     audit.init_audit_schema(conn)

## 主要な使い方（サンプル）
以下はライブラリ内の公開関数を使った典型的なワークフロー例です。

- DuckDB スキーマ初期化
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL の実行（J-Quants から差分取得 → 保存 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集（RSS）ジョブ
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 有効な銘柄コード集合（抽出に利用）
  res = run_news_collection(conn, sources=None, known_codes=set(["7203", "6758"]))
  print(res)  # {source_name: 新規保存件数}

- J-Quants API を直接使う（ID トークン取得 / データ取得）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- ファクター計算 / リサーチ
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  # conn: DuckDB 接続、target_date: datetime.date
  mom = calc_momentum(conn, target_date)
  vol = calc_volatility(conn, target_date)
  val = calc_value(conn, target_date)
  fwd = calc_forward_returns(conn, target_date, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

- Zスコア正規化（data.stats）
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m"])

## 重要な実装上の注意点
- 環境変数自動読み込み:
  - .env.local は .env を上書きする（.env.local の優先度が高い）
  - プロジェクトルート検出は .git または pyproject.toml を基準に行う
  - 自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- J-Quants クライアント:
  - 固定間隔スロットリング（120 req/min）を実装
  - 401 を受けると自動でトークンリフレッシュして 1 回リトライ
  - 一部エラーで指数バックオフの再試行を行う
- ニュース収集:
  - RSS の XML パースは defusedxml を使用して XML 関連攻撃を抑制
  - SSRF 対策としてリダイレクト先のスキーム/ホスト検証、レスポンスサイズ制限を行う
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で一意化（冪等）
- DuckDB 保存:
  - 多くの save_* 関数で ON CONFLICT DO UPDATE / DO NOTHING を使い冪等性を確保
- 品質チェック:
  - ETL 後に run_all_checks() で欠損・重複・スパイク・日付不整合を検出可能
  - 重大度（error/warning）を持つ QualityIssue を返す

## ディレクトリ構成（主要ファイル）
以下は本リポジトリの主要なモジュール構成です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - news_collector.py             -- RSS ニュース収集・保存
    - schema.py                     -- DuckDB スキーマ定義・init
    - pipeline.py                   -- ETL パイプライン（差分取得・品質チェック）
    - features.py                   -- 特徴量ユーティリティ（再エクスポート）
    - stats.py                      -- Zスコア等統計ユーティリティ
    - calendar_management.py        -- 市場カレンダー管理（営業日判定等）
    - audit.py                      -- 監査ログ用スキーマ初期化
    - etl.py                        -- ETL 結果クラス再エクスポート
    - quality.py                    -- データ品質チェック
  - research/
    - __init__.py                   -- 主要リサーチ関数の再エクスポート
    - feature_exploration.py        -- 将来リターン / IC / サマリー
    - factor_research.py            -- momentum/volatility/value 等の計算
  - strategy/                        -- 戦略関連（骨組み）
  - execution/                       -- 発注・実行関連（骨組み）
  - monitoring/                      -- 監視関連（骨組み）

（上記は現状の主要モジュールのみを抜粋しています）

## ロギング / 実行環境
- 設定: LOG_LEVEL でログレベルを制御（DEBUG/INFO/...）
- KABUSYS_ENV により実行環境を判定（development / paper_trading / live）
  - settings.is_live / is_paper / is_dev で判定可能

## 開発 / 貢献
- コードはモジュールごとに単体テストしやすい設計（依存注入、id_token の注入など）
- 自動化テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして環境依存を排除してください

---

この README はソースコード（src/kabusys/*）に基づいて作成しています。実際の運用時はプロジェクト固有の README やデプロイ手順、Secrets 管理（Vault 等）を整備してください。必要であれば README にサンプル .env.example、docker-compose、CI/CD 設定例などを追加します。希望があれば追記します。