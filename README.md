# KabuSys

日本株向けの自動売買・データプラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、カレンダー管理、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査ログ、DuckDB スキーマ管理などを一通り備えたモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ基盤（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマ定義 & 初期化
  - 冪等な保存（INSERT ... ON CONFLICT）をサポート
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックの統合実行（run_daily_etl）
- 研究用モジュール（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC、要約統計量の計算
- 戦略層（strategy）
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）：ファクター・AIスコア統合、Bear 判定、BUY/SELL 生成
- ニュース収集
  - RSS 取得・前処理・記事保存・銘柄抽出（SSRF 対策、gzip/サイズ制限、XML の安全パース）
- 監査（audit）
  - シグナル → 発注 → 約定までのトレーサビリティを保存する監査テーブル設計
- ユーティリティ
  - Zスコア正規化、マーケットカレンダーの判定・探索、統計関数など

---

## 動作環境 / 前提

- Python 3.10 以上（typing の | 演算子等を使用）
- 必要なPyPIパッケージ（最低限）:
  - duckdb
  - defusedxml

（運用上の機能によっては別途 slack-sdk などを追加することがあります）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（CONFIG モジュールが .git / pyproject.toml を探索して自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB スキーマ初期化（Python から実行）
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   ```
   - `db_path` に `:memory:` を渡すとインメモリ DB を使用します。

---

## 使い方（主要な API / 実行例）

以下は代表的な使い方例です。コードは Python スクリプトやジョブ内で呼び出します。

- DuckDB 初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 特徴量（features）構築
  ```python
  from datetime import date
  from kabusys.strategy import build_features

  n = build_features(conn, date(2024, 1, 5))
  print(f"features upserted: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals

  total = generate_signals(conn, date(2024, 1, 5))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ実行（既知銘柄コードを渡して銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection

  known_codes = {"7203", "6758", "9432"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants からの日足取得（個別）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

注意点:
- 多くの関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- ETL は冪等性を考慮しており、既存データの上書きや重複排除を行います。
- 環境変数が未設定の場合、Settings のプロパティが ValueError を投げます。

---

## 設定（Settings / 環境変数）

主要設定項目（Settings クラスからの抜粋）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 実行環境
  - KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
  - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

.env.example を参考に .env を作成してください（プロジェクトルートに配置すると自動読み込みされます）。

---

## ディレクトリ構成（main files）

（パッケージルート: src/kabusys/ 以下）

- __init__.py
  - パッケージ初期化、version 等
- config.py
  - 環境変数読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - schema.py — DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - news_collector.py — RSS 取得・記事保存、銘柄抽出、SSRF対策等
  - calendar_management.py — market_calendar の更新・営業日判定ユーティリティ
  - features.py — data.stats の再エクスポート
  - audit.py — 監査ログ（signal_events / order_requests / executions 等）
  - execution/ (将来的な発注層: 発注APIラッパー等)
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value の計算
  - feature_exploration.py — 将来リターン、IC、要約統計量
- strategy/
  - __init__.py (build_features, generate_signals をエクスポート)
  - feature_engineering.py — 特徴量の正規化・features テーブルへの保存
  - signal_generator.py — features と ai_scores を統合して signals を生成
- monitoring/ (監視関連の DB / ロギングなど: 実装が追加される想定)
- その他: 実運用で使うスクリプトやバッチジョブをプロジェクト上位に置くことを想定

---

## 開発・運用上の注意

- look-ahead bias を避ける設計:
  - ファクター/シグナル計算は target_date 時点の利用可能データのみで計算します。
- 冪等性:
  - DB への保存は ON CONFLICT / INSERT ... RETURNING を多用して再実行に耐えるよう設計しています。
- 安全対策:
  - RSS パーサーは defusedxml を使用し、SSRF 対策・受信サイズ制限を実装しています。
- テストや CI:
  - 自動環境変数読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 参考 / 次のステップ

- 実際の運用では監視・リトライ・バックオフ・アラート（Slack 通知等）を組み合わせてジョブを管理してください。
- execution 層（ブローカー連携）の実装／検証はペーパートレード環境で入念に行ってから live 環境へ移行してください（KABUSYS_ENV = paper_trading / live）。
- テーブル定義やビジネスルールは DataSchema.md / StrategyModel.md などの仕様ドキュメントと合わせて運用してください（コード内コメントに参照箇所あり）。

---

もし README に追加したい内容（例: CI 設定、Docker 化手順、具体的な cron / systemd サンプル）があれば教えてください。必要に応じてサンプルを追記します。