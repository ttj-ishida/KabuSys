# KabuSys

日本株向けの自動売買 / データ基盤ユーティリティ群です。  
主に J-Quants からの市場データ取得、DuckDB によるデータ格納・スキーマ管理、データ品質チェック、特徴量計算、ニュース収集、監査ログ（発注〜約定のトレース）などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・カレンダー等データの取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- 取得データの DuckDB への冪等保存（ON CONFLICT 処理）
- ETL パイプライン（差分取得、バックフィル、品質チェック）の実装
- ニュース（RSS）収集と銘柄紐付け
- ファクター（モメンタム／バリュー／ボラティリティ等）計算および研究用ユーティリティ
- 監査ログスキーマ（シグナル→発注→約定のトレース）と初期化ユーティリティ
- マーケットカレンダーの管理（営業日判定など）

設計方針として、本番発注 API への直接アクセスを行わない研究／データ基盤機能は標準ライブラリと DuckDB に依存し、再現性・冪等性・セキュリティ（SSRF 防止等）に配慮して実装されています。

---

## 主な機能一覧

- 環境設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定取得（未設定なら ValueError）

- データ取得・保存
  - J-Quants クライアント（fetch / save / ページネーション / トークン自動リフレッシュ）
  - DuckDB スキーマ初期化（init_schema）
  - ETL パイプライン（run_daily_etl、差分更新、バックフィル）

- データ品質管理
  - 欠損・重複・スパイク・日付整合性チェック（quality.run_all_checks）

- ニュース収集
  - RSS フィード取得（gzip 対応、SSRF 対策、XML パースの安全化）
  - 正規化・記事ID生成（URL 正規化 → SHA-256 ハッシュ）
  - raw_news / news_symbols への冪等保存

- 研究・特徴量
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ

- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・期間内営業日リスト取得・夜間更新ジョブ

- 監査ログ（Audit）
  - signal_events / order_requests / executions などのテーブル定義と初期化ユーティリティ

---

## 必要条件 / 依存関係

- Python 3.10 以上（typing における | 型注記を使用）
- pip-installable なパッケージ:
  - duckdb
  - defusedxml

開発環境での最低依存例:

pip install duckdb defusedxml

（プロジェクトに requirements.txt/pyproject.toml がある場合はそちらを使用してください）

---

## 環境変数

主に以下の環境変数を使用します（`.env` または OS 環境変数）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API を使用する場合のパスワード

任意 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（default: development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)（default: INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml が見つかる場所）にある `.env` と `.env.local` を起動時に自動ロードします。OS 環境変数が優先されます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

設定値取得例:
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)

---

## セットアップ手順（ローカル）

1. Python 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

2. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml や requirements.txt があればそれに従ってください）

3. 環境変数（.env）を用意
   プロジェクトルートに `.env` を作成し、必要なキー（JQUANTS_REFRESH_TOKEN など）を設定します。

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで以下を実行します:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ用 DB を別途用意する場合:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 基本的な使い方（サンプル）

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants から取得して保存・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL（価格・財務・カレンダー）
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2024,1,1))
  print(fetched, saved)

- ニュース収集実行
  from kabusys.data.news_collector import run_news_collection
  res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(res)

- ファクター計算（研究用）
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  mom = calc_momentum(conn, target_date=date(2024,1,1))
  vol = calc_volatility(conn, target_date=date(2024,1,1))
  val = calc_value(conn, target_date=date(2024,1,1))
  fwd = calc_forward_returns(conn, target_date=date(2024,1,1))
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print(ic)

- J-Quants API 直接利用
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  rows = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
  saved = save_daily_quotes(conn, rows)

- マーケットカレンダー操作
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  is_td = is_trading_day(conn, date(2024,1,1))
  nxt = next_trading_day(conn, date(2024,1,1))
  days = get_trading_days(conn, date(2024,1,1), date(2024,1,31))

- 監査スキーマ初期化（既存 conn に追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

---

## 主要モジュール概略 / ディレクトリ構成

（リポジトリの主要ファイル群。実際のファイル数はこの例より多い場合があります）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み、Settings クラス（settings オブジェクト）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py — RSS 取得・前処理・DB 保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - features.py — 特徴量ユーティリティ（再エクスポート）
  - calendar_management.py — market_calendar 管理・営業日判定・更新ジョブ
  - audit.py — 監査ログスキーマ / init_audit_db
  - quality.py — データ品質チェック
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
- strategy/
  - __init__.py （戦略関連はここに拡張）
- execution/
  - __init__.py （発注/約定管理の拡張点）
- monitoring/
  - __init__.py （監視・通知用の拡張点）

---

## 運用上の注意点

- J-Quants の API レート制限（120 req/min）を守るため内部で固定間隔スロットリングを実装しています。大量取得は時間を要します。
- DuckDB による ON CONFLICT 保存を多用しており、ETL は冪等です。ただし外部から直接 DB を編集すると整合性チェックで警告/エラーが出る場合があります。
- ニュース収集は外部 RSS を扱うため SSRF 対策、Content-Length/サイズ制限、gzip 解凍後チェック等の防御を実装しています。独自ソース追加時は注意してください。
- 環境（KABUSYS_ENV）を `live` にすると実運用向けの挙動判定箇所（is_live など）に影響します。発注等を行う拡張を作る際は環境判定を十分に行ってください。
- Python バージョンは 3.10 以上を想定しています。

---

## 開発貢献 / 拡張箇所

- strategy / execution / monitoring ディレクトリは戦略実装、発注ブリッジ、監視ロジックの拡張ポイントです。
- 研究用の notebook／スクリプトを用意して、research モジュールを利用するワークフローを確立するとよいです。
- 単体テスト、統合テスト（外部 API をモック）を整備すると信頼性が向上します。

---

必要であれば、具体的なサンプルスクリプト（ETL バッチ、ニュース収集ジョブ、研究用実行例）や pyproject/requirements のテンプレート、.env.example の雛形も用意できます。どれを追加しますか？