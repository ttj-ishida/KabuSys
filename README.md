# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ的な実装群）。  
このリポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行レイヤー用のスキーマ/ユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤と戦略ロジックの基礎を提供するライブラリです。  
主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に格納する ETL パイプライン
- 研究フェーズで計算された生ファクターを正規化・合成して features テーブルを作成する特徴量エンジニアリング
- 正規化済みファクターと AI スコアを統合して売買シグナル（BUY/SELL）を生成するシグナルジェネレータ
- RSS からのニュース収集と銘柄紐付け
- DuckDB スキーマ（Raw / Processed / Feature / Execution 層）定義・初期化
- ロギング・環境設定管理・各種ユーティリティ

設計上の特徴：
- ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT やトランザクションで整合性を確保）
- 外部 API 呼び出しは data 層に限定し、strategy 層は発注 API に依存しない

---

## 機能一覧

- 環境設定管理
  - .env/.env.local から自動ロード（無効化可）
  - 必須環境変数取得時のバリデーション

- データ取得（J-Quants）
  - 株価日足、財務情報、マーケットカレンダーのフェッチ（ページネーション・レートリミット・リトライ・自動トークンリフレッシュ対応）
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar など）

- ETL パイプライン
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新・バックフィル機能（最終取得日に基づく差分取得）

- スキーマ管理
  - DuckDB 用の完全なテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema で初期化可能

- 研究・特徴量計算
  - momentum / volatility / value 等のファクター計算
  - Z スコア正規化ユーティリティ（クロスセクション）

- 特徴量エンジニアリング
  - research で計算した生ファクターを正規化・合成し features テーブルへ UPSERT

- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム検知による BUY 抑制、エグジット判定（ストップロス等）
  - signals テーブルへの冪等書き込み

- ニュース収集
  - RSS フィード取得（SSRF対策、gzip上限、XML安全パース）
  - raw_news 保存、記事IDは正規化URLのSHA-256（先頭32文字）
  - テキストから銘柄コード抽出と news_symbols 保存

- カレンダー管理
  - market_calendar の差分更新 / 営業日判定補助（next/prev/get_trading_days 等）

- 監査ログ（Audit）
  - signal → order_request → execution に至る監査テーブル群（UUIDベースのトレーサビリティ）

---

## セットアップ手順

前提: Python 3.9+（typing の一部記法などを使用しています）、ネットワーク接続（J-Quants API 等）

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. インストール
   pip install -e .        # pyproject.toml/セットアップが存在する想定
   pip install duckdb defusedxml

   必要に応じて他の依存ライブラリを pip で追加してください（logging 等は標準ライブラリ）。

4. 環境変数（.env）を準備
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動読み込みされます（起動時に自動で読み込みされます）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的なキー（.env.example を参考にしてください）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルト）
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb   # デフォルト値
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

5. データベース初期化（DuckDB）
   Python REPL またはスクリプトで：
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

   init_schema(":memory:") でインメモリ DB も利用可能です。

---

## 使い方（主要 API と簡単な例）

以下は代表的な利用例のスニペットです。実運用では適切なエラーハンドリング・ジョブスケジューラ（cron / Airflow 等）を使用してください。

- DuckDB 初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 引数 target_date を与えて任意日を処理可能
  print(result.to_dict())

- 特徴量構築（target_date の features を計算して DB に保存）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2025, 1, 10))
  print(f"features upserted: {n}")

- シグナル生成（features + ai_scores → signals テーブル）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2025, 1, 10), threshold=0.6)
  print(f"signals written: {total}")

- ニュース収集ジョブ実行
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 既知銘柄セット（DBから読み出して渡すのが現実的）
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: saved_count, ...}

- カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

- 設定参照
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.env, settings.is_live)

注意点：
- strategy 層の関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、DB のテーブル（prices_daily, features, ai_scores, positions 等）を参照します。事前に ETL とスキーマ初期化を行ってください。
- 実際の発注（execution 層）はこのコードベースに含まれるスキーマ・ユーティリティを想定していますが、証券会社 API への接続は別途実装が必要です。

---

## 環境変数（主な一覧）

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants 用リフレッシュトークン
- SLACK_BOT_TOKEN        — Slack 通知に使用する Bot トークン（通知実装を行う場合）
- SLACK_CHANNEL_ID       — Slack 送信先チャンネルID
- KABU_API_PASSWORD      — kabuステーション API 用パスワード（execution 層使用時）

任意（デフォルトあり）:
- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 sqlite のパス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

.env のパースはシェル風（export KEY=val, クォートやコメント処理など）に対応しています。詳細は kabusys.config モジュール参照。

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py                  — DuckDB スキーマ定義・初期化
    - jquants_client.py          — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - features.py                — features まわりの公開インターフェース
    - news_collector.py          — RSS ニュース取得・保存・銘柄抽出
    - calendar_management.py     — market_calendar 管理と営業日ユーティリティ
    - audit.py                   — 監査ログテーブル定義
    - pipeline.py                — ETL フロー
    - ...（その他データ関連ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py         — momentum/volatility/value のファクター計算
    - feature_exploration.py     — IC, forward returns, summary 等の研究用ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py     — features テーブル生成ロジック
    - signal_generator.py        — signals 生成ロジック
  - execution/                   — 発注・約定・ポジション管理層（プレースホルダ）
  - monitoring/                  — 監視用モジュール（別途実装想定）

その他:
- pyproject.toml / setup.cfg 等（パッケージ管理用、存在を想定）
- .env.example（利用方法を示すサンプル、無ければ config.py の require メッセージ参照）

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリは「DB を中心に据えた設計」を採用しています。ETL → features → signals の順にデータが揃っていることを前提にしています。
- 実際に資金を動かす場合は paper_trading モードで十分なバックテスト・ドライランを行ってください（KABUSYS_ENV 環境変数を使用）。
- J-Quants の API レート制限・リトライ挙動は jquants_client に実装済みですが、運用時は API キーの権限・呼び出し頻度に注意してください。
- ニュース収集では SSRF 対策や XML の安全パース（defusedxml）を行っていますが、追加のセキュリティ要件があれば要拡張してください。
- DuckDB のファイル（デフォルト data/kabusys.duckdb）はバックアップとローテーション戦略を検討してください。

---

## 開発・貢献

- コードはモジュール毎に単体テストを書くことが望ましい（特に日付処理・数値演算・DB トランザクション周り）。
- テスト実行時には自動 .env 読み込みを無効化するか、一時的な .env を用いると安定します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- 新しい API 呼び出しやテーブルを追加する場合、schema.py の DDL とインデックスを更新して init_schema に反映してください。

---

README は以上です。具体的な運用スクリプト（CLI ツールやジョブランナー）や証券会社への発注実装は本リポジトリ外での実装を想定しています。必要があれば各ジョブのサンプル CLI や systemd / cron 設定例、または Airflow DAG のひな形を追加で作成しますか？