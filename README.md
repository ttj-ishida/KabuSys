# KabuSys

KabuSys は日本株向けの自動売買システム向けライブラリ／コンポーネント群です。データ収集（J-Quants API）、データ基盤（DuckDB）、ファクター / 特徴量生成、シグナル生成、ニュース収集、監査トレーサビリティなどの機能を提供します。

---

## プロジェクト概要

- 目的：J-Quants 等のデータソースから株価・財務・カレンダー・ニュースを取得して保存し、研究（research）で得た生ファクターを正規化・合成して特徴量（features）を作成、戦略ロジックに基づいて売買シグナルを生成する一連の処理を提供します。発注・実行層（execution）や監視（monitoring）との連携を想定しています。
- データベース：DuckDB をメインに使用（on-disk ファイルまたは :memory:）。一部モニタリング用に SQLite（設定で指定）を想定します。
- 設計方針：
  - 冪等性（INSERT … ON CONFLICT / トランザクション）を重視
  - ルックアヘッドバイアス回避：target_date 時点で利用可能なデータのみで計算
  - 外部依存を最小化（標準ライブラリ + 必要なパッケージ）

---

## 主な機能一覧

- 環境・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック、環境モード / ログレベル検証
- データ取得・保存（kabusys.data.*）
  - J-Quants API クライアント（認証・リトライ・レート制御）
  - 日次株価・財務・マーケットカレンダーの取得と DuckDB への冪等保存
  - RSS ニュース収集（SSRF/サイズ対策、正規化、銘柄抽出）
  - DuckDB スキーマ定義 / 初期化（init_schema）
  - ETL パイプライン（run_daily_etl）: 差分取得、保存、品質チェック
  - カレンダー管理（営業日判定、next/prev 等）
- 研究・特徴量（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - raw ファクターを正規化・フィルタリングして features テーブルへ UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し final_score を算出、BUY / SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム抑制、エグジット条件（ストップロス等）
- ニュース処理（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news へ冪等保存、銘柄抽出と紐付け
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ（監査テーブル定義）

---

## 必要な環境変数（抜粋）

必須（起動・API 呼び出しで必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知に使用するボットトークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

メモ:
- プロジェクトルートにある .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- .env のパースはシェル風の export KEY=val 等に対応しています。

---

## セットアップ手順

1. Python 環境
   - Python 3.10+ を推奨（コードは型ヒントや構文で 3.10+ を想定）
2. 必要パッケージ（最小）
   - duckdb
   - defusedxml
   - （その他：logging 等は標準ライブラリ）
   - 例: pip install duckdb defusedxml
   - 実運用では requirements.txt / pyproject.toml に依存管理を置いてください
3. リポジトリをチェックアウトしてインストール（開発モード）
   - git clone <repo>
   - cd <repo>
   - pip install -e .
4. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 最低限、上記の必須変数を設定してください
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
5. DB 初期化
   - DuckDB スキーマを作成します（ファイルパスを任意に指定可能）
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
6. ログ設定
   - 標準的な logging 設定を行ってください（LOG_LEVEL 環境変数を反映）

---

## 使い方（簡易ガイド）

以下は主要なユースケースの簡単なコード例です。

- DuckDB 初期化（schema 作成）
  - Python:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（J-Quants からの差分取得 → DB 保存 → 品質チェック）
  - Python:
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    # conn は init_schema 等で取得した duckdb 接続
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集ジョブ（RSS を取得して raw_news / news_symbols に保存）
  - Python:
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
    res = run_news_collection(conn, known_codes=known_codes)
    print(res)

- 特徴量（features）作成
  - Python:
    from kabusys.strategy import build_features
    from datetime import date
    cnt = build_features(conn, target_date=date(2025, 1, 31))
    print(f"upserted features: {cnt}")

- シグナル生成
  - Python:
    from kabusys.strategy import generate_signals
    from datetime import date
    total_signals = generate_signals(conn, target_date=date(2025, 1, 31))
    print(f"signals written: {total_signals}")

- J-Quants から日足を個別にフェッチして保存（テスト・デバッグ）
  - Python:
    from kabusys.data import jquants_client as jq
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    recs = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
    saved = jq.save_daily_quotes(conn, recs)
    print(saved)

注意点:
- run_daily_etl 等は内部で例外を捕捉して処理を継続する設計です。結果オブジェクト ETLResult にエラー情報／品質問題が格納されます。
- 本番で発注（execution 層）を行う場合は、KABU API 設定や追加の認証処理が必要です（kabusys.config の設定を参照）。

---

## よく使う API（関数一覧 / 概要）

- kabusys.config.settings — 環境設定のアクセサ（properties）
- kabusys.data.schema.init_schema(db_path) — DuckDB のスキーマを初期化して接続を返す
- kabusys.data.schema.get_connection(db_path) — 既存 DB への接続を返す
- kabusys.data.jquants_client.* — J-Quants API クライアント（fetch_*/save_*）
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL の統合エントリポイント
- kabusys.data.news_collector.run_news_collection(...) — RSS 収集ジョブ
- kabusys.research.calc_momentum / calc_volatility / calc_value — ファクター計算
- kabusys.strategy.build_features(conn, target_date) — features テーブル作成
- kabusys.strategy.generate_signals(conn, target_date, threshold=None, weights=None) — signals 作成

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS ニュース収集 / 保存
    - schema.py — DuckDB スキーマ定義・初期化
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — data.stats の再エクスポート
    - calendar_management.py — マーケットカレンダー管理
    - audit.py — 監査ログ用スキーマ
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - (その他: quality.py 等を想定)
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value のファクター計算
    - feature_exploration.py — IC, forward returns, summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成ロジック
    - signal_generator.py — final_score 計算と signals 生成
  - execution/
    - __init__.py — 発注 / 実行層（拡張ポイント）
  - monitoring/ — 監視・アラート関連（存在を想定）

（README に記載したファイルは主要実装の抜粋です。実際のリポジトリには追加のユーティリティ・モジュールやテストが含まれる可能性があります）

---

## 運用上の注意

- 秘密情報は .env ファイルや CI シークレットで管理してください。リポジトリに直接含めないでください。
- J-Quants のレート制限（120 req/min）を尊重してください（クライアントは RateLimiter を使用）。
- DuckDB のファイルはバックアップ／パーミッションに注意して管理してください。
- 本コードベースは研究用・自動売買補助用のコンポーネント群を提供します。実際の発注・資金管理・リスク管理は運用ポリシーに従って厳格に実装・検証してください。

---

## 貢献・拡張ポイント

- execution 層: 証券会社 API（kabuステーション等）との接続実装、冪等な注文送信 / 約定ハンドリング
- monitoring: リアルタイム監視・アラート（Slack 通知連携等）
- quality モジュール: 品質チェックルールの拡張（スパイク・欠損・整合性）
- テスト: unit/integration テストの充実（外部 API 呼び出しのモック）

---

必要であれば、README にサンプル .env.example、デプロイ手順（cron / Airflow / GitHub Actions での ETL スケジュール）、あるいはさらに詳細な API リファレンスを追記します。どの情報を優先して追加しますか？