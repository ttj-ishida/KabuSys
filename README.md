# KabuSys

日本株自動売買基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査スキーマ等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は、日本株（JPX）に対する量的自動売買プラットフォームのコア部品を実装した Python パッケージです。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得（差分取得、ページネーション、レート制御、認証自動リフレッシュ）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義と初期化
- 研究向けファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量正規化
- 戦略用シグナル生成（複数ファクターの重み付け合成、BUY/SELL 判定、エグジット条件）
- ニュース（RSS）収集と銘柄抽出、raw_news / news_symbols の保存
- ETL の ETLResult による実行結果管理、品質チェックフレームワークとの連携
- 発注・約定・監査用スキーマ（トレーサビリティ）

設計上の特徴は「ルックアヘッドバイアス回避」「冪等性（ON CONFLICT）」「外部依存最小化（標準ライブラリ主体）」「ネットワーク攻撃対策（SSRF/巨大レスポンス対策）」などです。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants への REST リクエスト（認証自動更新、レート制御、リトライ）
  - fetch/save：日足、財務、カレンダーの取得・DuckDB への保存（冪等）
- data/schema.py
  - DuckDB のスキーマ定義（raw / processed / feature / execution 層）と初期化関数 init_schema()
- data/pipeline.py
  - 日次 ETL 実行 run_daily_etl(): カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
- data/news_collector.py
  - RSS フィード取得、前処理、raw_news への保存、銘柄抽出と紐付け
- data/calendar_management.py
  - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - calendar_update_job(): 夜間カレンダー差分更新
- research/*
  - factor_research: mom/volatility/value 等のファクター計算（prices_daily / raw_financials 参照）
  - feature_exploration: 将来リターン計算、IC 計算、ファクター統計サマリ
- strategy/*
  - feature_engineering.build_features(): ファクター統合・Z スコア正規化・features テーブルへの保存
  - signal_generator.generate_signals(): features と ai_scores を統合して BUY/SELL シグナル生成
- その他
  - data/stats.zscore_normalize(): クロスセクション Z スコア正規化ユーティリティ
  - config.Settings: 環境変数管理（.env 自動読み込み機能あり）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP604 の型表記（A | B）を使用）
- DuckDB（Python パッケージとして duckdb）
- defusedxml（RSS 安全パースに使用）
- （実運用時）J-Quants API のリフレッシュトークン等

基本的な手順例:

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発時）pip install -e . など（setup.py/pyprojectがある場合）
4. データディレクトリ作成（デフォルト DUCKDB は data/kabusys.duckdb）
   - mkdir -p data
5. 環境変数の設定
   - プロジェクトルートに .env を配置するか OS 環境変数を設定してください。
   - 自動 .env 読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
   - 必須環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

サンプル .env（プロジェクトルート）:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
    KABU_API_PASSWORD=your_kabu_password_here
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な例）

1. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB を使用できます。

2. 日次 ETL 実行（J-Quants から差分取得して保存）
   - from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)
     print(result.to_dict())

3. 特徴量構築
   - from kabusys.strategy import build_features
     from datetime import date
     n = build_features(conn, date(2024, 1, 31))
     print("upserted features:", n)

4. シグナル生成
   - from kabusys.strategy import generate_signals
     total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
     print("signals written:", total)

5. ニュース収集
   - from kabusys.data.news_collector import run_news_collection
     results = run_news_collection(conn, known_codes={"7203","6758"})
     print(results)

6. カレンダー更新ジョブ（バッチ）
   - from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)
     print("calendar saved:", saved)

注意点:
- すべての公開関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。接続の作成は kabusys.data.schema.init_schema() または kabusys.data.schema.get_connection() を利用してください。
- run_daily_etl は個々のステップ失敗でも全体を継続して実行し、ETLResult にエラー・品質問題を記録します。
- 自動 .env 読み込みはパッケージ import 時に行われます。テスト時など自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード
- SLACK_BOT_TOKEN: Slack Bot トークン（通知等）
- SLACK_CHANNEL_ID: Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: development | paper_trading | live（default: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）
- DUCKDB_PATH: data/kabusys.duckdb（default）
- SQLITE_PATH: data/monitoring.db（default）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存）
  - news_collector.py      — RSS 収集と保存・銘柄抽出
  - schema.py              — DuckDB スキーマ & init_schema()
  - stats.py               — zscore_normalize 等統計ユーティリティ
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - features.py            — features の公開インターフェース（再エクスポート）
  - calendar_management.py — カレンダー管理（営業日ロジック / calendar_update_job）
  - audit.py               — 監査ログスキーマ
  - execution/             — 発注／実行関連（空パッケージ）
- research/
  - __init__.py
  - factor_research.py     — ファクター計算（mom/volatility/value）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py — features の統合 / 正規化 / 保存
  - signal_generator.py    — final_score 計算と signals テーブル更新
- execution/                — 発注ロジック等拡張領域（パッケージとして用意）

（上記は本リポジトリに含まれる主要なモジュールとその役割の一覧です）

---

## 開発・運用上の注意

- Python バージョン: 3.10 以上推奨（型表記に PEP604 を利用）
- DuckDB の互換性: DuckDB のバージョン差異により一部外部キー / ON DELETE 機能が未サポートの注記あり（schema.py 内コメント参照）。運用時は DuckDB のバージョンを確認してください。
- RSS パースは defusedxml を用いて安全処理を実施しています。外部 HTTP の扱いは SSRF や大容量レスポンスに配慮した実装です。
- J-Quants API のリクエストはレート制御（120 req/min）、リトライ、401 リフレッシュ対応を実装しています。運用時は API 利用規約とレート上限に注意してください。
- 本ライブラリは戦略ロジック（重み・閾値・エグジット条件）のフレームワークを提供しますが、実際の運用ではリスク管理・ポジション管理・ブローカー周りの実装（execution 層）を適切に実装してからライブ運用してください。

---

## 参考（よく使うワンライナー）

- DB 初期化（Python ワンライナー）
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- 日次 ETL 実行（Python ワンライナー）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn=init_schema('data/kabusys.duckdb'); print(run_daily_etl(conn).to_dict())"

---

README は以上です。必要なら、導入スクリプト・例外処理の詳細や CI でのテスト手順、さらに具体的な運用ガイド（バックテストフローや発注層との統合方法）を追記します。どの部分を詳しく追加しますか？