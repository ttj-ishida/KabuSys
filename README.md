# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
このドキュメントはローカルでのセットアップ、主要機能、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリはライブラリ・プラットフォームのコア実装を含みます。実際に発注や本番運転を行う際は十分な検証とリスク管理を行ってください。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants 等）、DuckDB を用いたデータ基盤、品質チェック、特徴量生成、研究（factor / IC 計算）、および発注監査用スキーマを備えた自動売買プラットフォーム向けのライブラリ群です。  
設計上のポイント:

- DuckDB を中心としたローカルデータベース（冪等保存、ON CONFLICT 処理）
- J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
- RSS ニュース収集（SSRF対策、トラッキング除去、記事→銘柄紐付け）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究モジュール（ファクター計算、将来リターン・IC・統計サマリ）
- 監査ログ（signal → order → execution のトレーサビリティ）

パッケージ名: kabusys（src/kabusys 配下）

---

## 主な機能一覧

- 環境変数 / .env の自動読み込みと Settings（kabusys.config）
- J-Quants API クライアント（data/jquants_client）
  - レートリミット、リトライ、ページネーション、トークン自動リフレッシュ
  - データ取得 + DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar）
- RSS ニュース収集（data/news_collector）
  - URL 正規化、トラッキング除去、SSRF/サイズ制限、記事ID ハッシュ化、銘柄抽出・保存
- DuckDB スキーマ管理（data/schema）
  - Raw / Processed / Feature / Execution / Audit 用テーブル定義と初期化
- ETL パイプライン（data/pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（data/quality）
  - 欠損、重複、スパイク、日付不整合の検出
- カレンダー管理（data/calendar_management）
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
- 研究モジュール（research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary 等
  - zscore_normalize（data.stats）
- 監査ログ（data.audit）
  - signal_events / order_requests / executions のテーブルと初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.9 以上（typing の新機能や型ヒントを利用）
- Git が使える環境

1. リポジトリをクローン / checkout（既にある前提）
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - 必要なら logging 等の好みのライブラリを追加してください
   - （本リポジトリに requirements.txt があれば pip install -r requirements.txt を使ってください）
4. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数の準備:
- プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（kabusys.config が .git または pyproject.toml からプロジェクトルートを検出して自動読み込み）。
- 自動読み込みを停止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（get_id_token に利用）
- KABU_API_PASSWORD — kabuステーション API 連携用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先のチャンネル ID

オプション / デフォルト:
- KABUSYS_ENV — development / paper_trading / live（省略時 development）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（"1" 等）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

例 (.env):
    JQUANTS_REFRESH_TOKEN=your-refresh-token
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C12345678
    KABU_API_PASSWORD=secret
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development

---

## 使い方（代表的な例）

以下はライブラリ API を直接呼ぶ簡単な例です。実運用ではジョブスケジューラや CLI ラッパーを用意してください。

1) DuckDB スキーマの初期化
- Python REPL / スクリプトで:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
  - ":memory:" を渡すとインメモリ DB を使えます。
  - init_schema はテーブルを冪等に作成します。

2) 日次 ETL の実行（J-Quants からデータ取得→保存→品質チェック）
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    result = run_daily_etl(conn)
    print(result.to_dict())

3) ニュース収集ジョブ（RSS を取得して raw_news に保存）
    from kabusys.data.news_collector import run_news_collection
    conn = get_connection("data/kabusys.duckdb")
    # known_codes に上場銘柄コードセットを渡すと記事→銘柄紐付けを行う
    res = run_news_collection(conn, known_codes={"7203","6758"})
    print(res)

4) J-Quants API 経由の取得・保存（単体）
    from kabusys.data import jquants_client as jq
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
    saved = jq.save_daily_quotes(conn, records)
    print(f"fetched={len(records)} saved={saved}")

5) 研究・ファクター計算（DuckDB 接続を渡す）
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    conn = get_connection("data/kabusys.duckdb")
    target = date(2024,1,31)
    mom = calc_momentum(conn, target)
    vol = calc_volatility(conn, target)
    val = calc_value(conn, target)
    fwd = calc_forward_returns(conn, target)
    # 例: mom の "ma200_dev" と fwd の "fwd_1d" で IC を計算
    ic = calc_ic(mom, fwd, "ma200_dev", "fwd_1d")
    print("IC:", ic)

6) 品質チェック
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date.today())
    for i in issues:
        print(i)

7) 監査スキーマの初期化（発注監査用）
    from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")

ログ設定や例外処理はアプリ側で適切に行ってください。

---

## 環境変数・設定の挙動（補足）

- kabusys.config は実行時にプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、プロジェクトルート直下の `.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テスト時や CI で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Settings クラス（kabusys.config.settings）経由で設定値へアクセスできます。必須項目が未設定の場合は ValueError を送出します。

---

## 推奨運用フロー（例）

1. init_schema で DB を準備
2. 毎朝（あるいは夜間） run_daily_etl を実行して当日分を取得・検証
3. ニュース収集は定期的に走らせ raw_news / news_symbols を更新
4. 研究チームは features/ research を参照してファクター実験（IC・サマリ等）を行う
5. 発注系は audit スキーマでトレーサビリティを確保し、signal → order → execution の追跡を行う

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/Settings 管理、.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント、取得 + 保存ユーティリティ
    - news_collector.py  — RSS 取得・正規化・保存・銘柄抽出
    - schema.py          — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - features.py        — features の公開インターフェース（zscore 再エクスポート）
    - calendar_management.py — カレンダー更新 / 営業日の判定ユーティリティ
    - audit.py           — 監査ログスキーマ（signal_events, order_requests, executions）
    - etl.py             — ETLResult の公開
    - quality.py         — 品質チェック（欠損/スパイク/重複/日付不整合）
  - research/
    - __init__.py
    - feature_exploration.py — forward returns / IC / summary / rank
    - factor_research.py     — momentum / volatility / value の計算
  - strategy/               — 戦略層（空 __init__ が存在、実装はここに追加）
  - execution/              — 発注実行層（空 __init__ が存在、実装はここに追加）
  - monitoring/             — 監視系（空 __init__）

---

## 開発上の注意点 / セキュリティ

- RSS 取得では SSRF 対策、Content-Length/受信サイズ上限、gzip 解凍後の上限チェックを実装していますが、外部ネットワークへのアクセスには注意してください。
- J-Quants トークン等の機密情報は .env ファイルや CI シークレットで安全に管理してください。決してリポジトリにコミットしないでください。
- DuckDB に保存したデータには機密情報が含まれる可能性があるため、適切なファイル権限を設定してください。
- 発注系（kabuステーション連携や本番 env）を扱う場合は、KABUSYS_ENV を適切に設定し、paper_trading や sandbox のテストを十分に行ってください。

---

## 貢献 / 開発フロー

- 新規機能やバグ修正はブランチを切って Pull Request を作成してください。
- DB スキーマ変更は backward compatibility を考慮し、マイグレーション手順を明確にしてください。
- テストを追加する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って外部環境の自動ロードを無効化すると安定します。

---

この README はコードベースの主要な機能・利用方法の簡易ガイドです。各モジュールの詳細な挙動・パラメータは該当ソース（src/kabusys 以下）内の docstring を参照してください。必要であれば CLI 例や運用手順も追加できます。