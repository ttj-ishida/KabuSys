# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（ライブラリとして利用することを想定）。  
このリポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理など、戦略運用に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次の層で構成される自動売買システムのコアライブラリです。

- Data Platform（DuckDB ベース）
  - J-Quants からのデータ取得クライアント
  - ETL パイプライン（差分取得・保存・品質チェック）
  - ニュース収集（RSS）
  - DuckDB スキーマ定義・初期化
- Research / Strategy
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量エンジニアリング（正規化・フィルタ）
  - シグナル生成（final_score に基づく BUY/SELL 判定）
- Execution / Monitoring（発注・監査・ログ等のインフラ用モジュール群を予定）
- 設定管理（.env / 環境変数読み込み、Settings クラス経由）

設計上のポイント：
- DuckDB を中心にデータを永続化（schema モジュールで DDL を定義）
- J-Quants API はレート制限・リトライ・トークンリフレッシュに対応
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）
- 冪等性を重視（ETL 保存は ON CONFLICT / INSERT … DO UPDATE 等で重複回避）
- 外部依存は最小化（標準ライブラリ + 必要最小限のサードパーティ）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local を自動ロード（プロジェクトルート検出）
  - Settings クラスから環境変数を型安全に取得

- データ取得 / 保存（J-Quants クライアント）
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - 市場カレンダー（fetch_market_calendar / save_market_calendar）
  - レート制限、リトライ、トークン自動リフレッシュ対応

- ETL パイプライン
  - 差分取得（backfill サポート）
  - 日次 ETL エントリ（run_daily_etl）
  - 品質チェックフック（quality モジュール経由）

- スキーマ管理（DuckDB）
  - init_schema: 全テーブルを作成・インデックス構築
  - get_connection: 既存 DB へ接続

- 特徴量 / 研究機能
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - Zスコア正規化ユーティリティ（zscore_normalize）
  - 将来リターン / IC / 統計サマリー（research.feature_exploration）

- 特徴量エンジニアリング & シグナル生成
  - build_features(conn, target_date)：features テーブル作成（ユニバースフィルタ、Z スコア、クリップ）
  - generate_signals(conn, target_date, threshold, weights)：final_score 計算→ BUY/SELL シグナル生成→signals テーブル保存
  - Bear レジーム抑制、SELL（ストップロス・スコア低下）判定

- ニュース収集
  - RSS フィード取得（fetch_rss）と前処理（URL 正規化、トラッキング除去、SSRF 防止）
  - raw_news / news_symbols への冪等保存

- 監査ログ / トレーサビリティ（audit モジュール）
  - signal_events / order_requests / executions など監査用テーブル定義

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 型や型ヒントを使用しているため）
- Git

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   本コードベースで明示的に利用されている主要パッケージ：
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   # 開発中はパッケージを編集可能インストールすると便利
   pip install -e .
   ```

   ※ requirements.txt がない場合は上記を個別にインストールしてください。

4. 環境変数 / .env 設定  
   プロジェクトルート（.git または pyproject.toml のある階層）が検出されると
   自動で `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。
   自動ロードを無効にするには：
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

   必須の環境変数（Settings 参照）：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルト値あり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - KABUSYS_DISABLE_AUTO_ENV_LOAD
   - KABUSYS_LOG_LEVEL 等（LOG_LEVEL）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # :memory: も可
   ```

---

## 使い方（簡易サンプル）

以下は代表的なワークフローの例です。

- DuckDB を初期化して日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量を作成してシグナルを生成する
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema(settings.duckdb_path)

  target = date(2024, 1, 4)
  n_features = build_features(conn, target)
  n_signals = generate_signals(conn, target, threshold=0.60)
  print("features:", n_features, "signals:", n_signals)
  ```

- ニュース収集（RSS）を実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に known_codes を用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants 生データを手動で取得して保存する
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

注意点：
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、DB 上の所定テーブルを参照／更新します。
- 日付に関する処理はすべてローカルの date 型（タイムゾーンを含まない）で扱われる設計です。
- 実運用で発注を行う場合は execution 層・ブローカー連携の実装とリスク管理が必要です。

---

## ディレクトリ構成（主要ファイル）

（`src/kabusys/` 配下）

- __init__.py
- config.py
  - Settings クラス、.env 自動ロード、必須環境変数チェック
- data/
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS 取得・前処理・DB 保存
  - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline.py — ETL ジョブ（run_daily_etl、run_prices_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - features.py — zscore_normalize を再エクスポート
  - calendar_management.py — 市場カレンダー管理ユーティリティ
  - audit.py — 監査ログ用テーブル DDL
  - (その他: quality, audit 等の補助モジュール想定)
- research/
  - factor_research.py — calc_momentum, calc_volatility, calc_value
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - __init__.py
- strategy/
  - feature_engineering.py — build_features（ユニバースフィルタ、正規化、features テーブル書き込み）
  - signal_generator.py — generate_signals（final_score 計算、BUY/SELL 判定、signals 書き込み）
  - __init__.py
- execution/
  - (発注・オーダー管理レイヤの実装場所（現状は空または未実装）)
- monitoring/
  - (監視・Alert 関連の実装場所)

上記以外にテスト・ドキュメント・運用スクリプトがあればリポジトリに含まれます。

---

## 環境変数まとめ（主なキー）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

---

## 開発・拡張メモ

- 新しいテーブルを追加する場合は data/schema.py の DDL 配列に追記し、init_schema 経由で反映してください。
- ETL の安定性向上やバックフィル要件がある場合は pipeline.run_* にフラグを追加して運用に合わせてください。
- execution 層（ブローカー接続）実装時は audit.order_requests / executions との整合性・冪等性を重視してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト用の環境変数を明示的に注入することを推奨します。

---

必要であれば、README に例となる .env.example、運用スクリプト（cron / systemd 用のサンプル）、よくあるトラブルシュート（トークンリフレッシュエラー、DuckDB の権限など）を追加します。追加で記載したい内容があれば教えてください。