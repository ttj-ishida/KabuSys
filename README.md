# KabuSys

日本株向けの自動売買/データ基盤ライブラリ（KabuSys）。  
DuckDB をデータストアとし、J‑Quants API から市場データ・財務データ・カレンダーを取得、ETL・データ品質チェック・特徴量計算・ニュース収集・監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するための内部ライブラリ群です。主に以下を目的とします。

- J‑Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB によるデータ保存・スキーマ管理
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS -> raw_news）
- ファクター/特徴量計算（モメンタム、ボラティリティ、バリュー 等）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 研究用ユーティリティ（IC 計算、Z スコア正規化 等）

設計方針として、「本番口座への発注を伴わないデータ処理／研究」「冪等性」「Look‑ahead bias の防止」「外部依存の最小化（標準ライブラリを多用）」が採用されています。

---

## 主な機能一覧

- 環境設定読み込み（.env / 環境変数、自動ロード）
- DuckDB スキーマ定義/初期化（raw / processed / feature / execution / audit 層）
- J‑Quants API クライアント
  - レート制御、再試行、トークン自動リフレッシュ
  - データのページネーション対応
- ETL パイプライン
  - 日次 ETL（カレンダー・株価・財務の差分取得と保存）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS パース（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news 保存、記事 ↔ 銘柄紐付け
- 研究用ファクター計算
  - モメンタム（1/3/6 ヶ月、MA200 乖離）
  - ボラティリティ（ATR）、流動性（出来高/売買代金）など
  - バリュー（PER、ROE）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 統計ユーティリティ（Zスコア正規化 等）
- 監査ログ（signal_events / order_requests / executions）スキーマ

---

## 前提 / 必要要件

- Python 3.10 以上（型ヒントに `X | None` などを使用）
- 依存パッケージ（最低限）:
  - duckdb
  - defusedxml

（プロジェクト配布時は requirements.txt を用意してください。上記はコード解析からの最小推奨セットです。）

---

## セットアップ手順

1. リポジトリをクローンする（既にコードがある前提）。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml

   ※ packaging に requirements.txt がある場合は pip install -r requirements.txt

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。
   - 必須変数（Settings に依存）:
     - JQUANTS_REFRESH_TOKEN=<あなたの J‑Quants リフレッシュトークン>
     - KABU_API_PASSWORD=<kabu ステーション API パスワード>
     - SLACK_BOT_TOKEN=<Slack Bot token>
     - SLACK_CHANNEL_ID=<通知先 Slack チャンネル ID>
   - 任意/デフォルト:
     - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
     - LOG_LEVEL=INFO|DEBUG|...
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   例 .env:
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

   自動で .env を読み込む機能があり、プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データベース初期化
   - DuckDB スキーマを作成:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を使う場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な API と実行例）

以下は Python REPL またはスクリプトからの利用例です。

- DuckDB の初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL の実行（J‑Quants への問い合わせ〜保存／品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 個別 ETL ジョブ
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  run_prices_etl(conn, target_date=date.today())

- J‑Quants API からの生データ取得（テスト/直接利用）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
  save_daily_quotes(conn, records)

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)

- 研究／特徴量計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  momentum = calc_momentum(conn, target_date=date(2024,1,31))
  volatility = calc_volatility(conn, target_date=date(2024,1,31))
  value = calc_value(conn, target_date=date(2024,1,31))

- Z スコア正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(records=momentum, columns=["mom_1m","mom_3m","mom_6m"])

- 将来リターンと IC（Spearman）
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
  ic = calc_ic(factor_records=momentum, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")

- カレンダー周りユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  is_trade = is_trading_day(conn, date(2024,1,31))
  next_trade = next_trading_day(conn, date(2024,1,31))

注意点:
- J‑Quants API クライアントは内部でレート制御（120 req/min）やリトライ、401 時のトークンリフレッシュを行います。id_token を明示的に渡すことも可能です。
- ETL/NEWS の各処理は例外を捕捉して個別に続行する設計です。結果オブジェクト（ETLResult）にエラーや品質問題が蓄積されます。

---

## よく使う環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABU_API_BASE_URL (オプション)
- DUCKDB_PATH (オプション、デフォルト data/kabusys.duckdb)
- SQLITE_PATH (オプション)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env 自動ロード無効)

---

## ディレクトリ構成

（重要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py       — J‑Quants API クライアント + 保存ユーティリティ
    - news_collector.py       — RSS ニュース収集・保存
    - schema.py               — DuckDB スキーマ定義と init_schema()
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — 特徴量ユーティリティ（公開インターフェース）
    - calendar_management.py  — マーケットカレンダー管理
    - audit.py                — 監査ログ（signal/order/execution）スキーマ
    - etl.py                  — ETL インターフェース（ETLResult を再エクスポート）
    - quality.py              — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン・IC・サマリー等
    - factor_research.py      — モメンタム/ボラティリティ/バリュー等の計算
  - strategy/                  — 戦略関連（空の __init__、戦略実装を格納想定）
  - execution/                 — 発注 / ブローカー連携（空の __init__、実装想定）
  - monitoring/                — 監視関連（空の __init__、実装想定）

その他:
- .env / .env.local            — 環境変数（プロジェクトルートに配置）
- data/                       — デフォルトの DB 格納先（DUCKDB_PATH の親ディレクトリ）

---

## 運用上の注意・ベストプラクティス

- 本ライブラリはデータ取得・保存・計算部分を中心に実装されており、実際の注文送信ロジック（証券会社 API 呼び出し）については別実装を想定しています。発注ロジックを実装する際は audit/schema の整合性（order_requests の冪等キー等）を尊重してください。
- ETL は差分更新＋バックフィル（デフォルト 3 日）を行い、API 側の後出し修正をある程度吸収する設計です。
- ニュース収集では SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去などの安全対策を実施していますが、外部フィード追加時は URL の信頼性を確認してください。
- DuckDB スキーマは冪等で何度でも実行できます。運用開始時に一度 init_schema() を呼んでください。
- テストや CI で自動的に .env を読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## コントリビューション / 開発

- 新しい機能や修正を追加する場合、各モジュールの設計方針（ドキュメント文字列）に沿って実装してください。
- 重要: データ取得・保存処理は冪等性を保つ（ON CONFLICT / upsert）こと。監査ログは削除しない前提のため、FK を考慮した設計を心がけてください。
- 単体テストは DuckDB の :memory: 接続を使うと容易です（schema.init_schema(":memory:")）。

---

README に掲載されていない細かな動作やパラメータは各モジュールの docstring を参照してください。必要であれば README にコマンドライン実行スクリプト例や systemd / cron ジョブの設定例も追加します。追加希望があれば教えてください。