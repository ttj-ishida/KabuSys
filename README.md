# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）のリポジトリ README。  
本ドキュメントはコードベース（src/kabusys）に基づく概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・ETL、特徴量計算（ファクター）、シグナル生成、監査ログ・実行管理までを想定したモジュール群です。  
設計上の主な方針は以下の通りです。

- DuckDB をデータ格納に使用し、Raw / Processed / Feature / Execution の多層スキーマを提供
- J-Quants API から市場データ・財務データ・マーケットカレンダーを取得（レート制限・リトライ・トークンリフレッシュ対応）
- RSS ベースのニュース収集と記事→銘柄の紐付け機能
- 研究（research）で定義された生ファクターを正規化して戦略（strategy）へ入力
- シグナル生成ロジックはファクター・AIスコア・レジーム判定などを統合して BUY/SELL を決定
- 発注・約定・ポジション・監査ログのデータモデルを提供（Execution / Audit 層）

本 README はライブラリの導入と主要な使い方の早見を目的としています。

---

## 主な機能一覧

- 環境変数/設定管理
  - .env / .env.local 自動ロード機能（必要に応じて無効化可能）
  - 必須設定の取り扱いとバリデーション（KABUSYS_ENV, LOG_LEVEL 等）
- データ取得（J-Quants クライアント）
  - 日足（OHLCV）・財務・マーケットカレンダー取得（ページネーション対応）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分（バックフィル）ロジック、品質チェック呼び出しフック
- スキーマ管理
  - DuckDB のスキーマ初期化（init_schema）／既存接続取得（get_connection）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats）
- 戦略（strategy）
  - build_features: 生ファクターを正規化し features テーブルへ保存
  - generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存
  - Bear レジーム判定、ストップロス・エグジット判定を含む
- ニュース収集
  - RSS フィード取得（SSRF 対策・受信サイズ制限・XML パース防御）
  - raw_news 保存、記事IDのハッシュ化（冪等）、銘柄抽出・news_symbols への保存
- 監査（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義（トレース可能な UUID 連鎖）

---

## セットアップ手順

※ 実行環境は Python 3.10+ を想定しています（型注釈で | を利用しているため）。

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成と有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール  
   本コードで直接参照されている外部ライブラリは主に以下です（プロジェクトに requirements.txt があればそちらを使用してください）。
   - duckdb
   - defusedxml
   インストール例:
   ```
   pip install duckdb defusedxml
   ```
   （ローカルで開発する場合は packaging 用に setuptools 等が必要になることがあります）

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数を設定  
   必須の環境変数（config.Settings 参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN: Slack 通知を使用する場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   オプション:
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: デフォルト "data/monitoring.db"
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

   注意: パッケージ起動時にプロジェクトルートの `.env` と `.env.local` が自動読み込みされます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

6. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成しスキーマを初期化
   ```

---

## 使い方（代表的な例）

以下はライブラリの主要な機能を使うための最小コード例です。実運用ではログやエラーハンドリング、ジョブスケジューラ等と組み合わせてください。

- DuckDB の初期化（スキーマ作成）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（市場カレンダー取得・株価・財務の差分取得・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"upserted features: {n}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes: 銘柄抽出を行う場合は有効な銘柄コードのセットを渡す
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(results)
  ```

- J-Quants の手動トークン取得（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

ログ出力や環境切替は Settings（kabusys.config.settings）を通じて行われます。KABUSYS_ENV を `live` にすると is_live フラグ等が有効になります。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABUSYS_ENV (任意): "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL (任意): "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト "INFO"）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (任意): Slack 通知用
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH (任意): Monitoring 用 SQLite（デフォルト "data/monitoring.db"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意): 自動 .env 読み込みを無効化する場合に `1` を設定

---

## ディレクトリ構成

主要ファイル・ディレクトリ構成（src/kabusys 以下を抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得・保存）
      - news_collector.py            -- RSS ニュース収集・保存・銘柄抽出
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - stats.py                     -- Z スコア等統計ユーティリティ
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       -- マーケットカレンダー管理ユーティリティ
      - features.py                  -- features の公開ラッパ
      - audit.py                     -- 監査ログ用テーブル定義
      - (その他: quality 等が別ファイルで想定)
    - research/
      - __init__.py
      - factor_research.py           -- モメンタム/ボラティリティ/バリューの計算
      - feature_exploration.py       -- 将来リターン / IC / 統計サマリ
    - strategy/
      - __init__.py
      - feature_engineering.py       -- features テーブル構築
      - signal_generator.py          -- final_score 計算および signals 挿入
    - execution/
      - __init__.py                  -- 発注/実行層（実装分割想定）
    - monitoring/                     -- 監視・アラート関連（別モジュール想定）

各モジュール内に詳細な docstring と設計方針が記載されています。関心がある機能の実装は該当ファイルを参照してください。

---

## 運用上の注意点

- DuckDB へ保存する際は upsert（ON CONFLICT）などで冪等性を保っていますが、アプリ側でもトランザクションやエラー処理を適切に行ってください。
- J-Quants API はレート制限があります（120 req/min）。ライブラリは固定間隔レートリミッタと再試行ロジックを備えていますが、バッチジョブ実行時は並列度に注意してください。
- ニュース収集では RSS パース・HTTP の脆弱性対策（defusedxml、SSRF チェック、受信サイズ上限など）を実装しています。外部ソースを追加する場合は既存の安全対策を意識してください。
- 本ライブラリはアルゴリズムバックテストや運用用途の基盤を提供しますが、実際の発注（マネー）を伴う場合は十分なテスト・監査・リスク管理を行ってください。

---

## 参考（開発者向けメモ）

- 設定値は kabusys.config.settings からアクセスできます。例: `from kabusys.config import settings; settings.jquants_refresh_token`
- ETL の詳細な挙動や戦略ロジックは各ファイル内の docstring（日本語で設計方針が記述）を参照してください。
- tests は本リポジトリに含まれていない場合があります。ユニットテストを追加する際は環境変数の自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用すると便利です。

---

必要に応じて README を拡張します。特に運用スクリプト（systemd / cron / Airflow / Prefect 等）や CI の実行例、詳しい環境変数説明（.env.example）を追加したい場合はその旨を教えてください。