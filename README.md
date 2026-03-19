# KabuSys — 日本株自動売買システム

バージョン: 0.1.0

KabuSys は日本株向けのデータ収集・特徴量生成・研究・ETL・監査ログ基盤を備えたライブラリ群です。J-Quants API を用いた市場データ取得、DuckDB を用いたローカルデータベース、RSS ベースのニュース収集、特徴量計算（モメンタム・ボラティリティ・バリュー等）、データ品質チェック、監査ログ用スキーマなど、自動売買システムの中核となる機能を提供します。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得と検証

- データ取得・保存（data）
  - J-Quants API クライアント（ページネーション・レート制御・トークン自動更新・リトライ）
  - DuckDB スキーマの初期化 / 接続
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - 市場カレンダー管理（JPX）
  - RSS ニュース収集・正規化・記事保存・銘柄抽出
  - 監査ログ（signal/order/execution）のスキーマと初期化

- 研究・特徴量（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）計算
  - 統計サマリー、Zスコア正規化ユーティリティ

- データ品質チェック（quality）
  - 欠損・重複・スパイク（急騰/急落）・日付不整合チェック
  - 各チェックは QualityIssue のリストで返却（fail-fast ではなく全件収集）

- ユーティリティ
  - 安全な RSS 取り込み（SSRF対策、Gzip上限チェック、XML攻撃対策）
  - DuckDB 向けの冪等保存（ON CONFLICT で更新）

---

## 要求環境

- Python 3.10+
  - typing の "X | Y" 構文を用いているため Python 3.10 以上が必要です。
- 主な依存ライブラリ（最低限）
  - duckdb
  - defusedxml
（実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存関係を管理してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成（例: venv）

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要なライブラリをインストール

   例（最低限）:

   ```bash
   pip install duckdb defusedxml
   ```

   実運用では jquants 依存や Slack 通知など追加パッケージがある場合があります。

3. 環境変数を設定

   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を置くと自動で読み込まれます（.env.local は .env を上書き）。

   主要な環境変数（例）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 自動 .env 読み込みを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマ初期化

   Python REPL やスクリプトから:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   :memory: でインメモリ DB を使用することも可能です:
   ```python
   conn = init_schema(":memory:")
   ```

---

## 使い方（代表的な例）

以下は基本的な利用フローのサンプルです。

- 日次 ETL を実行して市場データ・財務データ・カレンダーを取得する

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルト: today を対象
  print(result.to_dict())
  ```

- J-Quants から日足を直接フェッチして保存する（テスト用や部分取得）

  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- ニュース収集ジョブを実行する

  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）

  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  factors = calc_momentum(conn, target)
  forwards = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(factors, forwards, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Zスコア正規化

  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(factors, ["mom_1m", "mom_3m"])
  ```

- 監査ログスキーマの初期化（監査専用 DB を分ける場合）

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

---

## ディレクトリ構成

主要ファイルのみ抜粋（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + 保存ロジック
    - news_collector.py                — RSS ニュース収集・保存・銘柄抽出
    - schema.py                        — DuckDB スキーマ定義 / init_schema
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - features.py                      — 特徴量ユーティリティ公開
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py           — 市場カレンダー管理・ジョブ
    - audit.py                          — 監査ログ用スキーマ初期化
    - etl.py                           — ETL 結果型の再エクスポート
    - quality.py                       — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py               — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py           — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須 / 通知実装時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須 / 通知実装時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env.example を作成して上記を設定してください。config.Settings クラス経由で取得され、未設定の場合は例外が発生します（必須項目）。

---

## 注意事項 / トラブルシューティング

- Python バージョン確認: typing の新構文を使用しているため Python 3.10 以上を利用してください。
- 自動 .env 読み込み:
  - パッケージ起点で .git または pyproject.toml を上へ向かって探し、そのディレクトリ配下の `.env` / `.env.local` を読み込みます。テストなどで自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- J-Quants API のレート制限に注意（既にクライアント内で固定間隔スロットリングを導入していますが、上限・運用には注意）。
- RSS 収集では SSRF / XML Bomb / Gzip Bomb などに対する防御措置を行っていますが、運用時の外部URLリストは適切に管理してください。
- DuckDB スキーマに外部キー制約や ON DELETE の実装制約（DuckDB バージョン依存）があります。運用・削除時の挙動はコメントを参照してください。

---

## 拡張 / 実運用でのポイント

- 実運用ではジョブスケジューラ（cron / Airflow / systemd timers 等）で日次 ETL やカレンダー更新ジョブを実行してください。
- 発注・約定の連携には kabuステーションやブローカーの API 実装を追加する必要があります（execution / strategy 層の実装）。
- Slack 等への通知は別モジュールで実装し、Settings からトークン/チャンネルを参照して統合します。
- テスト: DuckDB の :memory: モードやテスト専用の .env を用意して単体テスト・統合テストを行ってください。

---

もし README に追加したい使用例（スクリプト、cron 設定、Dockerfile、CI 設定など）があれば教えてください。必要に応じてサンプル .env.example や簡易デプロイスクリプトも用意します。