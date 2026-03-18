# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をコアに、J-Quants API からデータを収集・保存し、品質チェック・特徴量計算・研究用ユーティリティや発注監査スキーマを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API から株価（OHLCV）・財務データ・市場カレンダーを取得して DuckDB に保存する ETL パイプライン
- ニュース（RSS）収集と記事→銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（モメンタム／ボラティリティ／バリュー等）計算および研究用ユーティリティ（Forward Returns / IC / 統計サマリー）
- 監査（signal → order → execution トレース用）用スキーマと初期化ユーティリティ
- Strategy / Execution / Monitoring 用のパッケージ骨格（実装はモジュール化）

設計上の要点:
- DuckDB を主要データストアとして利用（冪等保存、ON CONFLICT を活用）
- 外部依存は最小限（ただし DuckDB、defusedxml は使用）
- Look-ahead-bias を避けるため fetched_at を記録
- API レート制御・リトライ・トークン自動リフレッシュを実装（J-Quants クライアント）

---

## 主な機能一覧

- data.jquants_client
  - fetch/save：日足（OHLCV）、財務データ、マーケットカレンダーの取得・保存
  - レートリミット、リトライ、401時のトークン自動リフレッシュ
- data.schema
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化
  - インデックス定義
- data.pipeline / data.etl
  - 差分更新 ETL（prices / financials / calendar）と品質チェック実行のエントリポイント
- data.news_collector
  - RSS 収集、安全対策（SSRF/サイズ制限/トラッキング除去）と raw_news 保存、銘柄抽出
- data.quality
  - 欠損、スパイク、重複、日付整合性チェック（QualityIssue を返す）
- data.stats / features
  - z-score 正規化などの統計ユーティリティ
- research.factor_research, research.feature_exploration
  - モメンタム・ボラティリティ・バリューのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化ヘルパ

---

## セットアップ手順

前提:
- Python 3.9+（typing の Union 型表記等に合わせてください）
- ネットワーク経由で J-Quants API を利用するためのトークンを保持

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （パッケージ管理ファイル requirements.txt があればそれを使用してください。）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および開発用 `.env.local`）を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   主要な環境変数（必須・任意）:

   - 必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 環境 (development | paper_trading | live). デフォルト: development
     - LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL). デフォルト: INFO

   注意: `.env` に機密情報を含める場合は Git へコミットしないこと（.gitignore へ登録）。

5. データベース初期化
   - Python REPL またはスクリプトから DuckDB スキーマを初期化します:

     >>> from kabusys.data.schema import init_schema
     >>> conn = init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を使う場合:
     >>> from kabusys.data.audit import init_audit_db
     >>> ac = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（代表例）

以下は簡単な利用例です。スクリプトやジョブとして組み込めます。

1) DuckDB スキーマ初期化（1回だけ）
   - スクリプト例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
   - 例:
     from datetime import date
     import duckdb
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_daily_etl

     conn = init_schema("data/kabusys.duckdb")
     result = run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

   run_daily_etl は内部で J-Quants クライアントを呼び、取得 → 保存 → 品質チェックを順に実行します。ETLResult に結果・検出された品質問題・エラーが格納されます。

3) ニュース収集ジョブ実行
   - 例:
     from kabusys.data.news_collector import run_news_collection
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     known_codes = {"7203", "6758", "9984"}  # あらかじめ取得済みの有効銘柄コード集合
     results = run_news_collection(conn, known_codes=known_codes)
     print(results)

4) 研究用ファクター計算（research モジュール）
   - 例:
     import duckdb
     from datetime import date
     from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

     conn = duckdb.connect("data/kabusys.duckdb")
     t = date(2024, 1, 31)
     mom = calc_momentum(conn, t)
     vol = calc_volatility(conn, t)
     val = calc_value(conn, t)
     fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
     ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
     print(ic)

5) J-Quants から日足データを直接取得して保存
   - 例:
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     from kabusys.config import settings
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = save_daily_quotes(conn, records)
     print(f"saved={saved}")

---

## 設定・運用上の注意

- 環境変数の自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）から `.env` / `.env.local` を自動読み込みします。
  - テストなどで自動読み込みを抑制する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - Settings クラスは必須値の未設定時に ValueError を投げます。

- KABUSYS_ENV:
  - "development", "paper_trading", "live" のいずれかを設定してください（大文字小文字は問わず validation あり）。

- データ整合性:
  - ETL と品質チェックは独立に例外処理されます。品質チェックで問題が検出されても ETL は続行されます（呼び出し元が結果に応じて停止判定を行う想定）。

- セキュリティ:
  - .env に含まれるトークン・パスワードは漏洩しないように管理してください。
  - news_collector は SSRF 対策や応答サイズ制限、XML パースに defusedxml を使用していますが、運用上の追加検査を推奨します。

---

## ディレクトリ構成

（重要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                     -- 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py           -- J-Quants API クライアント + 保存
      news_collector.py           -- RSS 収集・正規化・保存
      schema.py                   -- DuckDB スキーマ定義・init_schema
      pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
      etl.py                      -- ETL 公開インターフェース
      quality.py                  -- データ品質チェック
      stats.py                    -- 統計ユーティリティ（zscore_normalize 等）
      features.py                 -- 特徴量ユーティリティ公開
      calendar_management.py      -- 市場カレンダー管理・ジョブ
      audit.py                    -- 監査ログスキーマ（signal/order/execution）
      ...（その他ユーティリティ）
    research/
      __init__.py
      factor_research.py          -- モメンタム/ボラティリティ/バリュー計算
      feature_exploration.py      -- 将来リターン／IC／サマリー等
    strategy/
      __init__.py                 -- 戦略レイヤー（骨組み）
    execution/
      __init__.py                 -- 発注/約定/ポジション管理（骨組み）
    monitoring/
      __init__.py                 -- 監視用モジュール（骨組み）

---

## 開発・貢献

- 新しい ETL チェックやファクターを追加する場合は、unit テストを用意し品質チェックモジュールへ統合してください。
- DB スキーマの変更は後方互換性に注意（既存テーブルの ALTER を伴う場合は移行手順を設計してください）。

---

## ライセンス / 注意事項

- ここに示したコードは参考実装です。実運用で使用する場合は、追加のテスト、監査、セキュリティ対策、エラーハンドリングの強化を行ってください。
- J-Quants / kabuステーション の利用規約・API 制限に従って使用してください。

---

README に記載の使い方や環境変数で不明点があれば、実行したいユースケース（ETL の一括実行、単一ジョブ、研究用途など）を教えてください。具体的なコマンドやスクリプト例をさらに提供できます。