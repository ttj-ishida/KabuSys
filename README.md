# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータ層に用い、J-Quants API や RSS を取り込み、特徴量計算・品質チェック・ETL・監査ログなどを備えた設計になっています。

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新付き）
- RSS ニュース収集と記事の前処理・銘柄抽出
- DuckDB スキーマ定義および初期化
- ETL パイプライン（差分取得、保存、品質チェック）
- 研究用（Research）モジュール：ファクター計算、将来リターン、IC 計算、統計サマリー
- 監査ログ（発注 → 約定フローのトレーサビリティ）
- ユーティリティ（Zスコア正規化、マーケットカレンダー管理 等）

設計方針として、本番の発注 API には影響しないようにデータ取得・研究処理は読み取り専用で設計されている箇所が多く、安全性（SSRF・XML Bomb 対策等）や冪等性を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション対応、レートリミット、HTTP リトライ、ID トークン自動リフレッシュ）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT）
- data/news_collector.py
  - RSS フィード取得・前処理（URL 正規化・トラッキング除去・SSRF 対策）
  - raw_news 保存、記事と銘柄の紐付け抽出
- data/schema.py / data/audit.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema, init_audit_schema / init_audit_db
- data/pipeline.py
  - 日次 ETL（差分取得・backfill、品質チェックの統合 run_daily_etl）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合の品質チェック（QualityIssue を返す）
- research/factor_research.py / research/feature_exploration.py
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、Spearman IC、ファクター統計サマリー
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）
- config.py
  - .env ファイルと環境変数の読み込み・設定アクセス（自動ロード挙動・必須チェック）

---

## 必要条件

- Python 3.10 以上（コード中での union 型注記などを利用）
- 必要なパッケージ（例）:
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれを使用:
     - pip install -r requirements.txt
     - または pip install -e .

4. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - KABU_API_PASSWORD
   - 任意（デフォルトを使用可能）:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

   - .env / .env.local をプロジェクトルートに置くと自動読み込みされます（自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     >>> from kabusys.data import schema
     >>> conn = schema.init_schema("data/kabusys.duckdb")
     これで必要なテーブルとインデックスが作成されます。

---

## 使い方（主要な例）

- 日次 ETL 実行（J-Quants から株価・財務・カレンダーを差分取得して保存）
  - 例:
    from datetime import date
    import kabusys
    from kabusys.data import schema, pipeline

    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集ジョブ
  - 例:
    from kabusys.data import news_collector, schema
    conn = schema.get_connection("data/kabusys.duckdb")
    # known_codes はニュース本文から抽出する銘柄コードのホワイトリスト
    known_codes = {"7203", "6758", "9432"}
    res = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
    print(res)

- J-Quants API からデータ取得（個別）
  - 例:
    from kabusys.data import jquants_client as jq
    records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    # 取得したデータは save_daily_quotes で DB に保存可能

- ファクター計算・研究用関数
  - 例:
    from kabusys.data import schema
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    conn = schema.get_connection("data/kabusys.duckdb")
    target = date(2024, 1, 31)
    mom = calc_momentum(conn, target)
    vol = calc_volatility(conn, target)
    val = calc_value(conn, target)
    fwd = calc_forward_returns(conn, target)
    # IC 計算例（mom_1m と fwd_1d の Spearman）
    ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
    print(ic)

- Zスコア正規化（クロスセクション）
  - 例:
    from kabusys.data.stats import zscore_normalize
    normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "per"])

- 監査ログ（発注→約定トレーサビリティ）
  - data.audit.init_audit_db(db_path) で監査専用 DB を初期化できます。

ログは standard logging を用いているため、アプリ側で logging.basicConfig(level=...) 等を設定して出力を調整してください。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの構成（src/kabusys 以下）です。追加のモジュールやドキュメントがあるかもしれませんが、ここではコードから抽出した主要な構成を示します。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py            — RSS ニュース収集・前処理・DB 保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - features.py                  — 特徴量ユーティリティ公開
    - calendar_management.py       — マーケットカレンダー管理・ジョブ
    - audit.py                     — 監査ログ（order_requests/executions 等）
    - etl.py                       — ETL 型の公開インターフェース
    - quality.py                   — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value 等の計算
    - feature_exploration.py       — 将来リターン・IC・サマリー
  - strategy/
    - __init__.py                  — 戦略層用（未実装のエントリポイント等）
  - execution/
    - __init__.py                  — 発注／実行管理（拡張ポイント）
  - monitoring/
    - __init__.py                  — 監視・メトリクス（拡張ポイント）

---

## 注意事項・実装上のポイント

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を自動読み込みします。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- セキュリティと堅牢性
  - RSS の取り込みでは defusedxml、SSRF チェック、受信サイズ制限を導入しています。
  - J-Quants クライアントはレート制限・再試行（指数バックオフ）・401 の自動リフレッシュをサポートします。
  - DuckDB への保存は可能な限り冪等操作（ON CONFLICT）を使っています。

- 動作確認
  - J-Quants API を利用する場合は有効なリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必須です。
  - DuckDB のファイルパスは設定（DUCKDB_PATH）で変更できます。デフォルトは data/kabusys.duckdb。

---

## 貢献・拡張ポイント

- strategy / execution / monitoring パッケージは拡張を想定したエントリポイントです。取引ロジックの実装や証券会社 API 統合はここに実装できます。
- 追加の品質チェックや特徴量、AI スコアリングを research / data に追加可能です。
- テスト: ネットワークや外部 API 依存部分はモック可能に設計されているため、ユニットテストの追加が容易です。

---

必要があれば、README に含める具体的な CLI 例や systemd / cron ジョブ設定例、.env.example のテンプレート、さらなる API 使用例（発注フロー、監査ログの書き込み例）なども作成できます。どの章を詳細化したいか教えてください。