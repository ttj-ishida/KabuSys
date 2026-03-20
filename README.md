# KabuSys

日本株向けの自動売買（データプラットフォーム + 戦略）基盤ライブラリです。  
DuckDB をデータレイクとして用い、J-Quants API や RSS ニュースを取り込み、特徴量計算→シグナル生成までのワークフローを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ取得・保存（J-Quants API から株価・財務・マーケットカレンダー、RSS ニュース収集）
- DuckDB 上のスキーマ定義と ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究（research）用ファクター計算と解析ユーティリティ（IC、将来リターン、サマリー等）
- 戦略層：特徴量の正規化・生成、最終スコア計算によるシグナル生成
- 監査・実行レイヤーのスキーマ（発注・約定・ポジション）、および実運用に必要なテーブル群
- 環境変数管理・設定読み込みユーティリティ

設計上の特徴:
- DuckDB を主体にして高パフォーマンスでローカル永続化
- API 呼び出しに対するレート制御・リトライ・トークン自動更新等の堅牢化
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）
- 冪等（idempotent）な DB 書き込み（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- 外部依存は最小限（duckdb, defusedxml など）

---

## 主な機能一覧

- 環境設定
  - .env / .env.local 自動ロード（プロジェクトルートの検出）
  - 必須環境変数の検査

- Data（kabusys.data）
  - J-Quants API クライアント（レート制御、リトライ、トークン管理）
  - RSS ベースのニュース収集 (SSRF 対策、トラッキングパラメータ削除、記事 ID に SHA-256)
  - DuckDB スキーマ定義・初期化 (init_schema)
  - ETL パイプライン（差分取得、バックフィル、品質チェック、日次ジョブ）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - 統計ユーティリティ（Z スコア正規化等）
  - 監査用スキーマ（signal_events / order_requests / executions）

- Research（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）計算、ファクター要約統計

- Strategy（kabusys.strategy）
  - 特徴量生成（build_features: raw factor の正規化・ユニバースフィルタ・features テーブルへの UPSERT）
  - シグナル生成（generate_signals: features + ai_scores から final_score を算出し buy/sell シグナルを signals テーブルへ）

- News（kabusys.data.news_collector）
  - RSS フィード取得、XML セーフパース、記事前処理、raw_news 保存、銘柄抽出・紐付け

---

## セットアップ手順

前提:
- Python 3.10 以上（モジュール内での型注釈の | 演算子等を使用）
- Git リポジトリを想定

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   - 最低依存: duckdb, defusedxml
   ```bash
   pip install duckdb defusedxml
   ```
   - 開発用や他の追加パッケージがあれば requirements.txt を用意している場合はそれを利用してください:
   ```bash
   pip install -r requirements.txt
   ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動的にロードされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（基本ワークフロー・例）

以下は典型的なバッチワークフローの例です（Python スクリプトまたは REPL）。

1. DB 接続と日次 ETL 実行（価格・財務・カレンダーの差分取得）
   ```python
   from datetime import date
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())  # ETLResult が返る
   print(result.to_dict())
   ```

2. 特徴量の構築（features テーブルの更新）
   ```python
   from datetime import date
   from kabusys.strategy import build_features

   count = build_features(conn, target_date=date.today())
   print(f"features updated: {count}")
   ```

3. シグナル生成（signals テーブルに BUY/SELL を保存）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals

   n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {n_signals}")
   ```

4. ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄検出に用いる有効なコードのセット（例: prices_daily にあるコード）
   known_codes = {"7203", "6758", "9432"}
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

5. Research（IC や将来リターンの計算）
   ```python
   from datetime import date
   from kabusys.research import calc_forward_returns, calc_ic, factor_summary

   fwd = calc_forward_returns(conn, target_date=date.today(), horizons=[1,5,21])
   # 例: calc IC は factor_records（research で生成したもの）と組合せて使う
   ```

注意点:
- generate_signals / build_features は target_date に基づき、その時点までに「システムが利用可能だった」データのみを参照する設計です（ルックアヘッド回避）。
- ETL はエラー発生時も可能な限り続行し、ETLResult にエラーや品質問題を集約します。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に利用する Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

---

## ディレクトリ構成

リポジトリは PEP 517 準拠のパッケージ構成（src layout）を想定しています。主要ファイルは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（レート制御・リトライ・保存）
    - news_collector.py      — RSS 取得・記事加工・raw_news 保存、銘柄抽出
    - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー更新 & 営業日ヘルパー
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログ用スキーマ DDL（signal_events 等）
    - (他: quality 等が別ファイルにある想定)
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクタ -> 正規化 -> features に保存
    - signal_generator.py    — final_score 計算と signals テーブルへの書き込み
  - execution/
    - __init__.py            — 実行層（発注ラッパー等を置く想定）
  - monitoring/              — 監視用コード（例: slack 通知等、存在する場合）
  - その他ドキュメント・ユーティリティ

---

## 開発・運用時の注意

- DuckDB のバージョン差異（外部キーや ON DELETE の可否）に留意する設計になっています。実行環境の DuckDB バージョンが古い場合は一部振る舞いが異なる可能性があります。
- J-Quants API のレート制限（120 req/min）を尊重するため、jquants_client にスロットリングが組み込まれています。並列化する場合は更なる考慮が必要です。
- ニュース取得では SSRF 対策や XML の安全パース（defusedxml）を利用しています。ただし外部の RSS を多量に取得する場合は追加の運用監視が必要です。
- 本リポジトリのコードはルックアヘッドバイアス回避を重視して実装されています。strategy / research の関数は target_date 時点までのデータのみを参照する点に注意してください。

---

## 貢献・拡張案

- execution 層の証券会社 API ラッパー（kabu API 実装）およびオーダー実行ロジックの実装
- 品質チェックモジュールの追加（quality モジュールを参照）
- CI / ユニットテストの追加（ETL の各ステップをモックして検証）
- モニタリング・アラート（Slack 送信、Prometheus など）

---

必要であれば README にサンプル .env.example やスクリプト例（cron ジョブ、systemd unit、Airflow／Dagster 連携例）を追記します。どの情報を追加したいか教えてください。