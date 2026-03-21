# KabuSys

日本株向けの自動売買プラットフォームのライブラリ実装（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行レイヤーまでを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコアライブラリです。以下のレイヤー・機能を備えます。

- J-Quants API からの株価・財務・カレンダー取得（ページネーション・レート制御・リトライ・トークン自動更新）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution）
- ETL パイプライン（日次差分取得・バックフィル・品質チェック）
- 研究（research）で計算したファクターの正規化・特徴量生成
- 戦略のシグナル生成（複数コンポーネントスコアの統合、BUY/SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け（安全対策：SSRF 回避・XML 脆弱性対策）
- 監査ログ／トレース（シグナル→発注→約定の UUID トレーサビリティ）

設計上、ルックアヘッドバイアスを防ぐ実装、冪等性（ON CONFLICT / トランザクション）を重視しています。

---

## 主な機能一覧

- data/jquants_client: J-Quants API クライアント（取得・保存・リトライ・レート制御）
- data/schema: DuckDB スキーマ初期化・接続
- data/pipeline: 日次 ETL（市場カレンダー / 株価 / 財務）とバックフィル処理
- data/news_collector: RSS 取得、前処理、raw_news 保存、銘柄抽出
- data/calendar_management: 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
- data/audit: 監査ログ用テーブル定義（signal_events / order_requests / executions ...）
- research/factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算
- research/feature_exploration: 将来リターン計算、IC（Spearman ρ）などの解析ヘルパ
- strategy/feature_engineering: 生ファクターを正規化し features テーブルに保存
- strategy/signal_generator: features + ai_scores を統合して BUY/SELL シグナル生成
- utility: data/stats（zscore 正規化）等の共通ユーティリティ
- 設定管理: config.Settings（.env 自動読み込み機能付き）

---

## 必要条件

- Python 3.10+ 推奨（型注釈に | が使われているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

標準ライブラリで実装されている箇所も多いため、上記以外はプロジェクトに応じて追加で必要になる可能性があります。

---

## セットアップ手順（例）

1. リポジトリをクローン／取得する

2. 仮想環境を作成して有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - 実運用で必要なその他パッケージ（例えば Slack クライアント等）があれば適宜追加

4. 環境変数を用意
   - プロジェクトルートに .env または .env.local を作成すると自動で読み込まれます（既定）。  
     自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須項目（後述の「環境変数」参照）を設定してください。

5. DuckDB スキーマ初期化（サンプル）
   - Python REPL やスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # デフォルトパス
     # 既存 DB に接続するには
     # conn = get_connection("data/kabusys.duckdb")
     ```

---

## 環境変数

以下は主要な環境変数（Settings クラスで参照されるもの）。.env ファイルに設定します。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意)
  - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack の投稿先チャンネル ID
- DUCKDB_PATH (任意)
  - デフォルト DB パス（Settings.duckdb_path の既定: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（既定: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 実行環境を 'development' / 'paper_trading' / 'live' のいずれかで設定
- LOG_LEVEL (任意)
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

注意: Settings は自動で .env, .env.local をプロジェクトルートから読み込みます（CWD に依存せず package の __file__ を基点に探索）。

---

## 使い方（主な API・例）

ここでは代表的な操作のコード例を示します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema などで取得済み
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（build_features）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date(2024, 1, 31))
  print(f"built {count} features")
  ```

- シグナル生成（generate_signals）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  n_signals = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"wrote {n_signals} signals")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes: 有効な銘柄コードセットを渡すと銘柄紐付けを行う
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
  print(results)
  ```

- カレンダー更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved {saved} calendar rows")
  ```

ログ出力や例外は各関数内でハンドリングしており、ETL は部分的失敗時も続行して結果を返します（ETLResult.errors 等で確認）。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にモジュール群が配置されています。主要ファイル・ディレクトリは次の通りです。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - schema.py                -- DuckDB スキーマ定義・init_schema
    - pipeline.py              -- ETL パイプライン
    - news_collector.py        -- RSS 収集・保存・銘柄抽出
    - calendar_management.py   -- 市場カレンダー管理
    - audit.py                 -- 監査ログ用テーブル定義
    - stats.py                 -- zscore_normalize 等
    - features.py              -- zscore_normalize 再エクスポート
  - research/
    - __init__.py
    - factor_research.py       -- モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py   -- 将来リターン・IC・要約統計
  - strategy/
    - __init__.py
    - feature_engineering.py   -- ファクター統合・正規化 → features テーブル
    - signal_generator.py      -- final_score 計算 → signals テーブル
  - execution/                 -- 発注 / execution 層（ファイルは後続追加）
  - monitoring/                -- 監視・Slack 等（ファイルは後続追加）

コード内の詳細ドキュメント（docstring）には処理フロー・設計方針・SQL コメント等が含まれており、個々の関数の使い方や副作用（DB テーブル参照／変更）を確認できます。

---

## 注意事項 / 運用上のポイント

- .env 自動読み込み: プロジェクトルート (.git または pyproject.toml があるディレクトリ) の .env / .env.local を自動読み込みします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 冪等性: データ保存関数は ON CONFLICT / トランザクションを用いて冪等に実装されています。
- ルックアヘッドバイアス対策: 特徴量・シグナル生成は target_date 時点のデータのみ参照するよう設計されています。
- セキュリティ: RSS 取得は SSRF 対策（リダイレクト検査・プライベートアドレス拒否）と defusedxml を用いた XML 攻撃対策を実装しています。
- DB バックアップ: DuckDB は単一ファイルなので定期的なバックアップを推奨します。

---

README は主要な利用手順とモジュール概要を記載しています。より詳しい設計ドキュメント（StrategyModel.md / DataPlatform.md / DataSchema.md など）や運用手順があれば併せて参照してください。必要であれば README に追加したいサンプルスクリプトや FAQ を作成します。