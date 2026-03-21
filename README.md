# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリです。J-Quants から市場データを取得して DuckDB に保存し、特徴量計算・シグナル生成・ニュース収集・ETL・マーケットカレンダー管理など、戦略実行までの主要機能を備えます。

主な設計方針は「ルックアヘッドバイアスを避ける」「冪等性」「運用での堅牢性（レート制限・リトライ・データ品質チェック）」です。

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ベースのニュース収集（正規化・SSRF対策・トラッキング除去）
- データ永続化
  - DuckDB のスキーマ定義・初期化（raw / processed / feature / execution 層）
  - 生データの冪等保存（ON CONFLICT ベース）
- ETL パイプライン
  - 差分取得・バックフィル・品質チェックを行う日次ETL（run_daily_etl 等）
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 戦略（strategy）
  - 特徴量作成（Z スコア正規化、ユニバースフィルタ適用）
  - シグナル生成（final_score 計算、Bear レジーム抑制、BUY/SELL 出力）
- 実行監査
  - 発注・約定・ポジション管理用のスキーマ（監査ログ）
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize など）
  - マーケットカレンダー操作（営業日判定、次/前営業日取得）
  - News ↔ 銘柄の紐付け（テキストから銘柄コード抽出）

---

## 必要要件（概略）

- Python 3.10+
- 主要依存パッケージ（一例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

各プロジェクトで requirements.txt や pyproject.toml を用意してください（このリポジトリ内の具体的なパッケージ定義を参照してください）。

---

## セットアップ手順

1. リポジトリをクローン / コピー

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージのインストール

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれを利用）

   例（最低限）:

   ```bash
   pip install duckdb defusedxml
   ```

   開発インストール:

   ```bash
   pip install -e .
   ```

4. 環境変数の設定

   - .env または環境変数で以下を設定してください（最低限必要な項目はプロジェクト内の config.Settings が参照します）:

     必須（アプリケーション実行で参照される主な環境変数）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合のボットトークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID

     任意 / デフォルトあり
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

   - 自動 .env ロードを無効化する場合（テストなど）は環境変数をセット:

     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   - .env ファイルがプロジェクトルート（.git または pyproject.toml を基準）にあれば自動で読み込まれます（.env → .env.local の順で上書き）。

5. DuckDB スキーマの初期化

   サンプル Python:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

   - ":memory:" を指定するとインメモリ DB を使用できます。

---

## 使い方（基本的な実行例）

以下は主要ワークフローの簡単な例です。詳細は各モジュールの docstring を参照してください。

- 日次 ETL（市場カレンダー・株価・財務の差分取得 + 品質チェック）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（feature layer への書き込み）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")
  ```

- シグナル生成（features と ai_scores を使って signals テーブルに出力）

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9433"}  # 既知の銘柄コードセットを渡すと紐付けを行う
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新（夜間バッチ）

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema(":memory:")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

補足:
- J-Quants クライアントはレート制限・リトライ・トークン自動更新を実装しています。get_id_token / fetch_* / save_* API を組み合わせて ETL を構築してください。
- 各関数は docstring に API 仕様（引数・戻り値・例外）を記載しています。

---

## 環境変数（まとめ）

主な環境変数（settings で使用されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (発注連携時に必須)
- KABU_API_BASE_URL (任意、デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須（Slack通知を使う場合）)
- SLACK_CHANNEL_ID (必須（Slack通知を使う場合）)
- DUCKDB_PATH (任意、デフォルト data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下のモジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                          — DuckDB スキーマ定義と初期化
    - jquants_client.py                  — J-Quants API クライアント（取得 / 保存）
    - pipeline.py                        — ETL パイプライン（run_daily_etl 等）
    - news_collector.py                  — RSS ニュース取得・保存・銘柄抽出
    - calendar_management.py             — マーケットカレンダー管理
    - features.py                        — data.stats の再エクスポート
    - stats.py                           — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                           — 監査ログスキーマ（発注→約定トレース用）
  - research/
    - __init__.py
    - factor_research.py                 — ファクター計算（momentum / volatility / value）
    - feature_exploration.py             — 将来リターン / IC / サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py             — 特徴量作成 / 正規化 / ユニバースフィルタ
    - signal_generator.py                — final_score 計算とシグナル生成
  - execution/                           — 発注関連（空パッケージ、拡張箇所）
  - monitoring/                          — 監視・メトリクス周り（拡張箇所）

各モジュールは docstring で設計方針や使用方法・前提（参照する DB テーブル等）を詳述しています。

---

## 運用メモ / 注意点

- ルックアヘッドバイアス対策として、各計算は target_date 時点で利用可能なデータのみを使用する設計です。外部データ呼び出しのタイミングには注意してください。
- DuckDB DDL は冪等（IF NOT EXISTS）なので複数回初期化しても安全です。
- ニュース収集では SSRF 対策・サイズ上限・XML パース防御を実装していますが、外部フィードの信頼性には注意してください。
- 発注・約定の連携は本コードベース内でスキーマ・監査機能を提供しますが、実際のブローカー接続・失敗処理は実装・検証が必要です（特に live 環境）。
- 設定ミス（欠落した必須環境変数）は Settings._require により ValueError が発生します。CI/運用前に必須変数を確実に設定してください。

---

## 貢献 / 拡張

- execution 層（ブローカードライバ実装）や監視用のアダプタ、GUI/ダッシュボード、戦略のパラメータ最適化ジョブなどが拡張ポイントです。
- テスト: 各モジュールは外部依存（HTTP/DB）を注入可能に設計されているため、モックを使った単体テストが容易です（例: _urlopen モック、id_token 注入）。

---

README の内容や実行例で不明点があれば、どの機能の使い方（例: ETL の詳細フロー、シグナルパラメータの調整、news のソース追加など）についてさらに説明します。