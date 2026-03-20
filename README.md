# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログのためのスキーマ等を含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみ使用）
- DuckDB をデータレイク/処理 DB として採用（冪等保存を重視）
- HTTP 周りの堅牢化（リトライ・レート制御・SSRF 対策など）
- 外部依存を最小化、標準ライブラリ中心で実装

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー、ページネーション対応）
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事ID生成）
- データ保管・スキーマ
  - DuckDB 用スキーマ定義・初期化（raw / processed / feature / execution 層）
  - 冪等保存（ON CONFLICT / INSERT ... DO UPDATE）
- ETL パイプライン
  - 差分取得（最終取得日から差分、バックフィル考慮）、品質チェック統合
  - 日次 ETL 実行エントリポイント
- 研究・特徴量生成
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - Zスコア正規化ユーティリティ
  - 研究用ユーティリティ（将来リターン計算、IC 計算、統計サマリ）
- 戦略
  - 特徴量合成（build_features）
  - シグナル生成（generate_signals）：複数コンポーネントを重み付けして final_score を算出、BUY/SELL を signals テーブルへ冪等書き込み
- カレンダー管理
  - JPX マーケットカレンダーの管理、営業日判定・次/前営業日取得など
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル定義
- セキュリティ・堅牢性
  - API レート制御、リトライ、トークン自動更新、XML 脆弱性対策（defusedxml）、SSRF 対策

---

## 前提・必要環境

- Python 3.9+（typing の新機能を用いているため 3.8 以上でも動作しますが 3.9 以上を推奨）
- duckdb
- defusedxml
- ネットワークアクセス（J-Quants API、RSS ソースなど）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合（プロジェクトルートで）
pip install -e .
```

必要な環境変数（必須は明記）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

自動 .env ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存パッケージをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

3. 環境変数を用意（`.env` をプロジェクトルートに作成）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化（Python REPL やスクリプトで実行）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # conn は duckdb 接続オブジェクト（DuckDBPyConnection）
   ```

---

## 使い方（主要な実行例）

- 設定値を取得する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- スキーマ初期化（既存でも冪等）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- 特徴量を作成（strategy 層）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  conn = get_connection(settings.duckdb_path)
  from datetime import date
  n = build_features(conn, date(2025, 1, 31))
  print(f"upserted features: {n}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  conn = get_connection(settings.duckdb_path)
  from datetime import date
  total = generate_signals(conn, date(2025, 1, 31))
  print(f"generated signals: {total}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  conn = get_connection(settings.duckdb_path)
  # known_codes に有効な銘柄コードセットを渡すと銘柄紐付けを行う
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)
  ```

- カレンダー更新ジョブ（夜間バッチ向け）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

注: これらはライブラリ API を直接呼ぶ例です。運用時はジョブスケジューラ（cron / systemd timer / Airflow 等）やラッパースクリプトを用いて定期実行することを想定しています。

---

## よくあるトラブルシューティング

- 環境変数が足りない:
  - settings プロパティ（例: settings.jquants_refresh_token）が呼ばれると必須変数が未設定の場合 ValueError を送出します。
- DuckDB へ接続できない/ファイル権限:
  - DUCKDB_PATH の親ディレクトリが存在しない場合 init_schema が自動で作成しますが、権限やパス名に注意してください。
- J-Quants API の認証エラー:
  - get_id_token / _request 実装は 401 時に自動リフレッシュを試みますが、リフレッシュトークンが無効だと失敗します。
- RSS フィードが取得できない:
  - fetch_rss は SSRF 防止やレスポンスサイズ制限を行っています。非 http/https スキームや private host による取得は拒否されます。

ログ出力を詳細にしたい場合は環境変数 `LOG_LEVEL=DEBUG` を設定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ベースのニュース収集・前処理・DB保存
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — Zスコア正規化等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day など）
    - audit.py — 監査ログ向けスキーマ（signal_events, order_requests, executions）
    - features.py — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ等（研究用）
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターの統合・正規化 → features テーブル
    - signal_generator.py — features + ai_scores を用いたシグナル生成
  - execution/ — （発注/実行・ブローカー連携用の実装を置く場所）
  - monitoring/ — 監視・アラート関連（SQLite などを利用するモジュールを想定）

---

## 開発・貢献

- テストの追加、品質チェックの拡充、ブローカー固有の execution 層の実装などが今後の主な拡張候補です。
- セキュリティや冪等性に関する重要な仕様はコード中の docstring に記載されています。設計を踏まえた変更をお願いします。

---

必要であれば README にサンプル .env.example、より詳細なモジュール API リファレンス、運用フロー（cron/監視/障害対応）を追加します。どの項目を優先して追加しますか？