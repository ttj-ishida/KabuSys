# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義など、戦略実行に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群から構成されています。

- データ取得 (J-Quants API) と ETL（差分取得・保存・品質チェック）
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution 層）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化・合成（features テーブルへの書き込み）
- シグナル生成（features + AI スコア → final_score → BUY/SELL）
- ニュース収集（RSS → raw_news、銘柄抽出）
- マーケットカレンダー管理（JPX カレンダーの取得・営業日判定）
- 監査・実行レイヤーのテーブル群（orders / executions / positions 等）

設計方針の要点:
- ルックアヘッドバイアスの除去（target_date 時点のデータのみ使用）
- DuckDB を用いた冪等なデータ保存（ON CONFLICT / トランザクション）
- 外部依存を最小化（可能な限り標準ライブラリ中心）
- API レート制御・リトライやセキュリティ対策（SSRF、XML注入対策など）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（トークン更新、ページネーション、レート制御、リトライ）
  - 株価・財務・カレンダー取得と DuckDB への保存（冪等）
- data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新ロジック（backfill により API の後出し修正を吸収）
- data.schema
  - DuckDB スキーマの初期化・接続（init_schema / get_connection）
- data.news_collector
  - RSS 収集、前処理、raw_news 保存、記事と銘柄の紐付け
- data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job（夜間バッチ）
- research.factor_research / feature_exploration
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- strategy.feature_engineering
  - ファクター正規化（Zスコア）・ユニバースフィルタ・features テーブルへの書き込み
- strategy.signal_generator
  - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）
  - final_score による BUY/SELL シグナル生成、Bear レジーム抑制、SELL（エグジット）判定
- audit / execution テーブルセット
  - 監査トレーサビリティのためのテーブル定義（signal_events, order_requests, executions 等）

---

## セットアップ手順

前提:
- Python 3.9+ を想定
- DuckDB を利用するためライブラリが必要（duckdb）
- RSS パースに defusedxml を使用

1. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   プロジェクト root に requirements.txt がある想定で:
   ```bash
   pip install -r requirements.txt
   ```
   必要最小パッケージ例（プロジェクトに合わせて調整してください）:
   - duckdb
   - defusedxml

3. 環境変数（.env）を準備
   プロジェクトルートに `.env` / `.env.local` を置けます。自動読み込みはデフォルトで有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知連携用）
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意（デフォルト値あり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API ベース URL（default: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=passw0rd
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   Python から初期化:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
   ```

5. （任意）自動化
   - ETL は日次バッチで実行する想定です。cron / systemd timer などで run_daily_etl を呼び出して下さい。
   - calendar_update_job はカレンダー先読みのため夜間に実行することを推奨します。

---

## 使い方（サンプル）

以下は代表的な利用例です。実際の運用ではログ・例外処理・スケジューラなどを追加してください。

1. DuckDB 初期化と日次 ETL 実行
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

2. 特徴量構築（features テーブルへの書き込み）
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.strategy import build_features

   conn = init_schema("data/kabusys.duckdb")
   n = build_features(conn, date(2025, 3, 1))
   print(f"features upserted: {n}")
   ```

3. シグナル生成
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.strategy import generate_signals

   conn = init_schema("data/kabusys.duckdb")
   total = generate_signals(conn, date(2025, 3, 1), threshold=0.6)
   print(f"signals written: {total}")
   ```

4. ニュース収集ジョブ実行（既知銘柄セットがあれば紐付けも行う）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "6954"}  # 例
   results = run_news_collection(conn, sources=None, known_codes=known_codes)
   print(results)
   ```

5. カレンダー API 更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

---

## 主要 API と注意点

- 設定取得:
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```
  必須環境変数が未設定だと ValueError が発生します。

- 自動 .env ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動読み込みします。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- ETL 実行時の品質チェック:
  - data.pipeline.run_daily_etl は `quality` モジュールによる品質チェックを実行できます（デフォルト有効）。
  - 品質問題は ETLResult.quality_issues に格納され、致命的な品質エラーは has_quality_errors で検出可能です。

- レート制御 / リトライ:
  - J-Quants クライアントは 120 req/min を想定した固定間隔レート制限を行います。また 401 時の自動トークン更新や 408/429/5xx のリトライを実装しています。

- セキュリティ:
  - RSS 取得では SSRF 防止のためホスト/IP 検査、リダイレクト検査、受信サイズ制限、defusedxml による XML パースを行っています。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要モジュール配置:
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント + 保存ロジック
    - schema.py          — DuckDB スキーマ定義・初期化
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - news_collector.py  — RSS 収集 / raw_news 保存 / 銘柄抽出
    - calendar_management.py — JPX カレンダー管理
    - features.py        — zscore_normalize の再エクスポート
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - audit.py           — 監査ログ用テーブル定義
    - execution/         — 発注関連（空パッケージ/将来拡張）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成
    - signal_generator.py    — final_score・signals 生成

（コード内のコメントに設計ドキュメント参照が多数あります: StrategyModel.md, DataPlatform.md 等）

---

## トラブルシューティング

- ValueError: 環境変数がない
  - 必要な環境変数（JQUANTS_REFRESH_TOKEN 等）を .env に設定するか、環境に直接設定してください。

- DuckDB 接続やテーブルがない
  - 最初に init_schema() を実行してテーブルを作成してください。

- J-Quants API エラー（401）
  - モジュールは 401 発生時にリフレッシュトークンで再取得を試みます。リフレッシュトークンが正しいか確認してください。

- RSS 取得でリダイレクト・接続が失敗する
  - 内部ネットワーク（プライベート IP）や不正なスキームはブロックされます。外部公開 URL を使用してください。

---

## 今後の拡張候補（参照）

- execution 層のブローカー連携（kabu API と実際の注文送信）
- 戦略設定・ポートフォリオ最適化モジュール
- テスト用の CLI / 管理用 Web UI
- デプロイ用 Docker イメージ、Kubernetes CronJob テンプレート

---

この README はコード内のモジュール docstring と設計コメントに基づいて作成しています。実際の運用では各モジュール（特に外部 API 呼び出し部・発注部）に対する追加の設定・テスト・監視を強く推奨します。