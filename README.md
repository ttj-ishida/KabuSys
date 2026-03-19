# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）  
（内部モジュール: データ取得・ETL・特徴量/ファクター計算・シグナル生成・監査ログ等を含む）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は J-Quants 等の市場データ API を用いて日本株の時系列データ・財務データ・ニュースを収集し、DuckDB に保存・整備し、研究用ファクター計算（research）、特徴量生成（strategy.feature_engineering）、シグナル生成（strategy.signal_generator）を行うための基盤ライブラリです。  
設計上、以下を重視しています:

- ETL の差分更新と冪等性（ON CONFLICT / INSERT DO UPDATE）  
- ルックアヘッドバイアス回避（計算は target_date 時点の観測のみを使用）  
- API レート制御・リトライ・自動トークン更新（J-Quants クライアント）  
- ニュース収集での安全対策（SSRF/サイズ上限/XML 攻撃対策）  
- DuckDB を用いたローカルデータレイク構成（Raw / Processed / Feature / Execution 層）  

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）：日足、財務、マーケットカレンダーの取得、保存（ページネーション／リトライ／レート制御／自動トークン更新）
  - ニュース収集（news_collector）：RSS からの収集、前処理、銘柄抽出、冪等保存
  - DuckDB スキーマ定義・初期化（data.schema）
  - ETL パイプライン（日次 ETL run_daily_etl、差分取得 / backfill 対応）
  - カレンダー管理（calendar_management）：営業日判定・前後営業日取得・カレンダー更新ジョブ
- 研究・特徴量
  - ファクター算出（research.factor_research）：Momentum / Volatility / Value 等
  - 特徴量探索ユーティリティ（research.feature_exploration）：将来リターン計算、IC、統計サマリ
  - Zスコア正規化等の統計ユーティリティ（data.stats）
- 戦略
  - 特徴量作成（strategy.feature_engineering）：ファクター正規化、ユニバースフィルタ、features テーブルへの UPSERT
  - シグナル生成（strategy.signal_generator）：feature と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成、signals テーブルへの書き込み
- 監査・実行レイヤー
  - 監査ログ（data.audit）：シグナル→注文→約定フローのトレース用テーブル定義
  - 実行層（execution）用のスケルトン（発注・エグゼキューション管理は実運用で実装）
- セーフティ機構
  - 各所での入力検証、例外処理、トランザクション（BEGIN/COMMIT/ROLLBACK）による原子性保証
  - ニュース収集での SSRF 対策 / gzip サイズ上限 / defusedxml 利用 など

---

## 動作要件

- Python 3.9+（型注釈で | を使用しているため 3.10+ が望ましい）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィードなど）

（プロジェクトの実際の requirements.txt / pyproject.toml に従ってインストールしてください）

---

## 環境変数 / 設定

KabuSys は .env ファイル（プロジェクトルートの .env / .env.local）または OS 環境変数から設定を読み込みます。.env 自動読み込みはデフォルトで有効です（テスト時などに無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください）。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション（発注API）パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリングDB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

.env のパース仕様は標準的な KEY=VALUE に加え、export プレフィックス、クォートとエスケープ、行内コメント処理をサポートします。

サンプル .env（プロジェクトルートに配置）:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）
   - 開発用にパッケージとしてインストールする場合:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数で設定

5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで init_schema を実行して DB を作成します（デフォルト path は settings.duckdb_path を参照）
     例:
       from kabusys.data.schema import init_schema
       from kabusys.config import settings
       conn = init_schema(settings.duckdb_path)

---

## 使い方（基本例）

以下は代表的な操作の例です。各関数は DuckDB の接続オブジェクト（duckdb.connect が返す接続）を受け取ります。

- DB 初期化（1回だけ実行）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（市場カレンダー・株価・財務の差分取得、品質チェック含む）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日（営業日に自動調整）

- 特徴量構築（features テーブルへの書き込み）
  from kabusys.strategy import build_features
  from datetime import date
  cnt = build_features(conn, date(2024, 3, 15))

- シグナル生成（signals テーブルへの書き込み）
  from kabusys.strategy import generate_signals
  from datetime import date
  n_signals = generate_signals(conn, date(2024, 3, 15), threshold=0.6)

- ニュース収集ジョブ（RSS 取得 -> raw_news 保存 -> news_symbols 紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)

- カレンダー更新バッチ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

注意点:
- これらの処理はトランザクションで日付単位の置換（DELETE -> INSERT の原子処理）を行うため、繰り返し実行しても冪等性が確保される設計です（ただし外部操作の影響は考慮してください）。
- J-Quants API の呼び出しはレート制御とリトライ処理が組み込まれています。大量バッチを組む際は API 制約に注意してください。

---

## ディレクトリ構成 (主要ファイル)

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定読み込み
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py       — RSS 収集・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義 / init_schema
    - pipeline.py             — ETL パイプライン / run_daily_etl 等
    - calendar_management.py  — 市場カレンダー管理
    - features.py             — zscore_normalize の公開インターフェース
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ用スキーマ
    - (その他: quality モジュール想定)
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Volatility/Value の計算
    - feature_exploration.py  — 将来リターン/IC/統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py  — features 作成
    - signal_generator.py     — final_score 計算と signals 生成
  - execution/
    - __init__.py             — 実行層 (スケルトン)
  - monitoring/              — 監視/通知用（ファイルは含まれている想定）

（上記はリポジトリ内の主要なモジュールです。実際のファイル一覧はプロジェクトのルートを参照してください）

---

## 設計上の注意事項 / 安全性

- ETL・DB書き込みは原子操作（トランザクション）で行いますが、外部要因（ファイル削除等）により例外が発生する可能性があります。例外は上位でハンドリングしてください。
- ニュース収集は外部入力を扱うため、SSRF 対策 / XML パース保護 / レスポンスサイズチェック 等の保護を施していますが、運用環境での追加検査を推奨します。
- J-Quants トークンは環境変数で管理し、ログ等に露出しないように注意してください。
- KABUSYS_ENV によって挙動が変わる（paper_trading / live など）想定があるため、本番環境では設定を慎重に指定してください。

---

## 開発・貢献

- バグ修正や機能追加のプルリクエスト歓迎します。テスト、静的解析、ドキュメントの追加を添えてください。
- 大きな設計変更を行う場合は Issue を立て、事前に設計検討を行ってください。

---

## ライセンス

リポジトリ内の LICENSE ファイルを参照してください（本 README では明記していません）。

---

この README はコードベース（src/kabusys 以下）を参照して作成しました。実際の運用・デプロイ時はプロジェクト内の pyproject.toml / requirements.txt / docs を確認し、CI・監視・バックアップ等の運用設計を行ってください。