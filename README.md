# KabuSys

日本株自動売買プラットフォームのコアライブラリです。市場データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査・実行レイヤ向けのスキーマ等を含むモジュール群を提供します。

主な目的は、J-Quants 等のデータソースから取得した生データを DuckDB に蓄積し、研究→本番（発注）へつなぐための共通基盤を提供することです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主な API の例）
- ディレクトリ構成
- 環境変数（設定）
- 補足（注意事項）

---

## プロジェクト概要

KabuSys は日本株を対象とする自動売買システムのライブラリ群です。主なレイヤは以下の通りです。

- Data layer: J-Quants API クライアント、RSS ニュース収集、DuckDB スキーマ・ETL、品質チェック
- Research layer: ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量探索・IC 計算
- Strategy layer: 特徴量正規化・合成（features テーブル作成）、最終スコア算出と売買シグナル生成（signals テーブル）
- Execution / Audit layer: シグナル／注文／約定／ポジション等のスキーマ、監査ログ設計（UUID トレーサビリティ）
- Config: .env / 環境変数管理（自動ロード機能）

設計上、戦略・研究系の関数は「ルックアヘッドバイアスを防ぐ」ため、target_date 時点のデータのみを使用するように実装されています。また DB への保存は冪等（ON CONFLICT / upsert）を重視しています。

---

## 機能一覧

主な機能（モジュール別）:

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 設定取得ラッパー（settings）
- kabusys.data.jquants_client
  - J-Quants API の認証・取得（トークンリフレッシュ、レート制御、リトライ）
  - 日足 / 財務 / マーケットカレンダーの取得と DuckDB への保存（冪等）
- kabusys.data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）
  - DB 初期化関数 init_schema/get_connection
- kabusys.data.pipeline
  - 日次 ETL（差分取得、保存、品質チェック）
  - 個別 ETL（prices / financials / calendar）
- kabusys.data.news_collector
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出・紐付け
  - SSRF / XML Bomb 等の安全対策を実装
- kabusys.research
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary：ファクター評価用ツール
- kabusys.strategy
  - build_features：raw ファクターを統合・Zスコア正規化して features テーブルに保存
  - generate_signals：features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルに保存
- その他: 統計ユーティリティ（zscore_normalize）やマーケットカレンダー管理等

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子を使用しているため）
- pip が利用可能

1. リポジトリをクローン／配置する（例）
   - git clone <repo>

2. 仮想環境を作成してアクティブ化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 必要パッケージのインストール（最低限）
   - duckdb
   - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （プロジェクトに requirements ファイルがあればそれを使用）

4. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動読み込みされます（.git または pyproject.toml を基準にプロジェクトルートを探索）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（少なくとも ETL/API 利用時に必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB など、デフォルト: data/monitoring.db）

---

## 使い方

以下は主な操作の簡単なサンプルです。実運用ではログ設定・例外処理・スケジューリング等を追加してください。

- DB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 日次 ETL の実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema で取得した接続
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ファクター計算（features テーブルの作成）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  # conn は DuckDB 接続
  n = build_features(conn, target_date=date(2025, 3, 1))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total_signals = generate_signals(conn, target_date=date(2025, 3, 1))
  print(f"signals written: {total_signals}")
  ```

- ニュース収集ジョブ（RSS 取得と保存、銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 有効銘柄コードの集合（抽出フィルタ用）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)
  ```

- マーケットカレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意:
- すべての戦略・研究 API は target_date 時点のデータのみを参照する設計です。将来データを参照しないように呼び出し側で日付を適切に指定してください。
- ETL・API 呼び出し時はネットワークエラーや API レート制限への配慮を行ってください（jquants_client は内部でレート制御とリトライを実装しています）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル／モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — データ系のユーティリティ公開
    - calendar_management.py  — カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                — 監査ログスキーマ
    - stats.py                — 統計ユーティリティ（z-score 等）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py  — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル作成（正規化等）
    - signal_generator.py     — final_score 計算とシグナル生成
  - execution/                — （発注・監視関連の実装が入る想定）
  - monitoring/               — （監視系 DB / ロギング用）

この README はコードベースの主要モジュールを要約したもので、各モジュールの詳細な使い方は該当ファイル中の docstring を参照してください。

---

## 環境変数（主要）

必須（ETL/API 利用時）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     — kabuステーション API のパスワード
- SLACK_BOT_TOKEN       — Slack 通知用トークン
- SLACK_CHANNEL_ID      — Slack チャネル ID

その他
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

.env ファイルのパーサはシェルライクな形式（コメント・クォート・export 対応）をサポートします。

---

## 補足（運用上の注意）

- DuckDB のバージョン差や SQL 方言差に注意してください（外部キー・ON DELETE 挙動などは DuckDB のバージョンによって制約がある旨コメントに記載あり）。
- ニュース収集は外部 RSS を読み込むため SSRF / 大量データ等の対策を実装していますが、実行時は接続先を検証してください。
- システムは研究用（データ計算）と実運用（注文送信）を分離する設計です。実売買を行う場合は十分なリスク管理（paper_trading フラグ・stop loss・レート制御）を行ってください。
- ロギング／監査の設定を適切に行い、作業記録を残すことを推奨します。

---

必要であれば、README に含める具体的なコマンド例、Docker/CI 設定、テスト実行方法、または各モジュールの API リファレンス（関数一覧と引数説明）を追加できます。どの情報を優先して追加しますか？