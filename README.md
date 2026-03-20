# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームと自動売買戦略基盤を提供するライブラリです。J-Quants API 経由で市場データ・財務データ・カレンダー・ニュースを取得し、DuckDB に保存。研究用ファクター計算、特徴量生成、シグナル生成、ETL パイプライン、ニュース収集、監査ログ等の機能を備えます。

主な設計方針：
- ルックアヘッドバイアス回避（各処理は target_date 時点の情報のみ使用）
- 冪等性（DB への保存は ON CONFLICT やトランザクションで安全）
- 外部 API 呼び出しは data 層に限定し、strategy 層は発注 API への依存を持たない
- 単体テストしやすい設計（トークン注入・IO 分離など）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - ニュース収集（RSS）と記事／銘柄紐付け
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution レイヤー）
  - 差分 ETL（市場カレンダー・株価・財務）の自動実行（run_daily_etl）
- 研究/戦略
  - ファクター計算（momentum, volatility, value）
  - Z スコア正規化ユーティリティ
  - 特徴量生成（build_features：正規化・ユニバースフィルタ・features テーブル保存）
  - シグナル生成（generate_signals：ファクター + AIスコア統合、BUY/SELL 生成）
- 運用・補助
  - マーケットカレンダー管理（営業日判定, next/prev/get_trading_days）
  - ニュース収集の SSRF / XML 攻撃対策や記事正規化
  - 監査ログ（signal_events / order_requests / executions）用スキーマ
  - 環境変数管理（.env 自動ロード、必須チェック）

---

## 必要条件

- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリ以外は上記が主な依存）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発インストール（リポジトリ直下で）
pip install -e .
```

（プロジェクトが pyproject.toml/setup.py を提供する想定で pip install -e . が有効です）

---

## 環境変数 / .env

Settings（kabusys.config.Settings）で使用する主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)（デフォルト: INFO）

自動 .env ロード：
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込み順序: OS 環境 > .env.local (> .env)
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして仮想環境を作成・依存をインストール
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

2. 環境変数を設定（.env を作成）
   - 上記の必須変数を .env に記載

3. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # or ":memory:" for in-memory
   conn.close()
   ```

4. 日次 ETL を実行（例）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   conn.close()
   ```

---

## 使い方（主要 API）

以下は代表的な使い方の例です。各関数は duckdb.DuckDBPyConnection を受け取ります。

- DuckDB 初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  if result.has_errors:
      print("ETL 中にエラーが発生しました:", result.errors)
  ```

- 特徴量のビルド（features テーブルに UPSERT）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date(2025, 1, 10))
  print(f"features に登録した銘柄数: {count}")
  ```

- シグナル生成（signals テーブルに書き込む）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date(2025,1,10), threshold=0.6)
  print(f"生成したシグナル数: {total}")
  ```

- ニュース収集ジョブ（RSS から raw_news と news_symbols へ保存）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", "9984"}  # 実運用では全コードセットを渡す
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- マーケットカレンダー操作
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_td = is_trading_day(conn, date(2025,1,1))
  next_td = next_trading_day(conn, date(2025,1,1))
  ```

---

## 注意点 / 運用上のポイント

- J-Quants API:
  - レート制限（120 req/min）に従う実装（内部でスロットリング）
  - 401 時はリフレッシュトークンで自動リフレッシュ（1回）
  - ページネーション対応
- ニュース収集:
  - RSS の XML パースは defusedxml を使用（XML 攻撃対策）
  - SSRF 対策（リダイレクト先検査、プライベートアドレス排除）
  - レスポンスサイズ制限（デフォルト 10 MB）
- DB 保存:
  - save_* 関数は冪等（ON CONFLICT）で安全
  - init_schema は存在チェック済み DDL を実行してスキーマを作成
- 環境:
  - 自動 .env ロードはプロジェクトルート判定に .git または pyproject.toml を用いるため、配布後の実行でも期待通りに動作するよう設計
  - テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化可能

---

## ディレクトリ構成（主なファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数読み込み / Settings
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + save_*）
  - news_collector.py — RSS 取得・前処理・DB 保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — 市場カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
  - audit.py — 監査ログ用 DDL（signal_events, order_requests, executions）
- research/
  - __init__.py
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - factor_research.py — momentum/volatility/value の計算
- strategy/
  - __init__.py (build_features, generate_signals を公開)
  - feature_engineering.py — features テーブル作成（正規化・ユニバースフィルタ）
  - signal_generator.py — final_score 計算と signals への書き込み
- execution/  (発注・実行関連の実装用ディレクトリ)
- monitoring/ (監視・メトリクス関連)

---

## 開発・貢献

- コードはモジュール単位で責務が分離されています。ユニットテストを追加しやすい設計です（トークン注入、ネットワーク呼び出しのモックなど）。
- PR や issue を歓迎します。ドキュメントやテストの追加、バグ修正、機能提案は大歓迎です。

---

もし README に含めてほしい具体的なサンプルスクリプト、CI 設定、あるいは .env.example のテンプレートなどがあれば教えてください。README をさらにプロジェクトの実行手順や運用手順に合わせて調整します。