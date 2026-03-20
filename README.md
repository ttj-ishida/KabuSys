# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。市場データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査/実行レイヤのスキーマ定義などを提供します。

主に DuckDB をデータ層に使用し、J-Quants API / RSS / kabuステーション 等と連携して安全にデータを収集・処理するためのユーティリティ群が含まれます。

バージョン: 0.1.0

---

## 主要機能

- データ層
  - DuckDB スキーマ定義と初期化（冪等）
  - raw / processed / feature / execution の多層スキーマ
- データ取得（J-Quants）
  - 日次株価（OHLCV）・四半期財務・マーケットカレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分取得（最終取得日ベース）＋バックフィル
  - 日次 ETL 実行の統合（calendar / prices / financials / 品質チェック）
- 研究・戦略
  - ファクター計算（Momentum / Volatility / Value 等）
  - クロスセクションの Z スコア正規化ユーティリティ
  - 特徴量構築（build_features）とシグナル生成（generate_signals）
    - 最終スコア計算、Bear レジーム検出、BUY/SELL 判定、冪等な signals テーブル書き込み
- ニュース収集
  - RSS フィード取得（SSRF 対策、XML 攻撃対策、トラッキングパラメータ除去）
  - raw_news 保存、記事→銘柄紐付け（news_symbols）
- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、カレンダーの夜間更新ジョブ
- 監査 / 実行（骨組み）
  - 発注/約定/ポジション/監査ログ用のテーブル設計

---

## 前提条件

- Python 3.8+
- DuckDB
- defusedxml

（パッケージは環境や配布方法に応じて requirements.txt / pyproject.toml で管理してください）

推奨インストールパッケージ例:
```bash
python -m pip install duckdb defusedxml
```

---

## インストール（ローカル開発）

1. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 依存をインストール
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトのパッケージ定義があれば:
   # pip install -e .
   ```

---

## 環境変数 / 設定

プロジェクトは環境変数（または `.env`, `.env.local`）を参照して設定します。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

注意:
- 必須変数が未設定の場合、settings を参照すると ValueError が発生します。
- .env ファイルを使用する場合は `.env.example` を参考にしてください（プロジェクトルートに配置）。

---

## セットアップ手順（簡易）

1. DuckDB スキーマを初期化:
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   ":memory:" を指定するとインメモリ DB を使用できます。

2. 必要な環境変数を設定（例: export / set）:
   - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など

3. （任意）.env/.env.local に環境変数を保存しておくと便利。

---

## 使い方（主要 API の例）

以下は代表的な操作のサンプルです。

- 日次 ETL 実行（J-Quants からデータ取得して保存・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）を構築
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals created: {total_signals}")
  ```

- RSS ニュース収集と保存（既定ソース）
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes を指定すると記事→銘柄の紐付けを行う
  known_codes = {"7203", "6758"}  # 例
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダー更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- J-Quants の低レベル操作例
  ```python
  from kabusys.data import jquants_client as jq

  # トークンは settings.jquants_refresh_token を使用して自動取得されます
  daily = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## 設計上のポイント / 注意点

- 冪等性を重視:
  - DuckDB への保存は ON CONFLICT を用いる設計で、再実行可能（idempotent）。
- ルックアヘッドバイアス回避:
  - 特徴量やシグナル生成は target_date 時点の公開情報のみを用いる方針。
  - データ取得時は fetched_at を記録していつ取得可能だったかを追跡可能。
- セキュリティ・堅牢性:
  - RSS の SSRF 対策、defusedxml による XML 攻撃対策、ネットワークリトライとレート制御などを実装。
- 環境（KABUSYS_ENV）によるモード切替:
  - development / paper_trading / live に応じて運用方針を変える想定（本パッケージはフラグのみ提供）。

---

## ディレクトリ構成（主要ファイル）

（project root の src/kabusys 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py         — J-Quants API クライアント & 保存ユーティリティ
      - news_collector.py         — RSS 収集・保存
      - schema.py                 — DuckDB スキーマ定義 & init_schema/get_connection
      - stats.py                  — zscore_normalize 等の統計ユーティリティ
      - pipeline.py               — ETL パイプライン（run_daily_etl など）
      - calendar_management.py    — カレンダー管理（営業日判定・更新ジョブ）
      - audit.py                  — 監査ログ用スキーマ DDL（発注/約定トレース）
      - features.py               — data 層の特徴量ユーティリティ公開インターフェース
    - research/
      - __init__.py
      - factor_research.py        — Momentum/Volatility/Value の計算
      - feature_exploration.py    — IC/forward returns/summary 等（研究用）
    - strategy/
      - __init__.py
      - feature_engineering.py    — features 作成（build_features）
      - signal_generator.py       — signals 作成（generate_signals）
    - execution/                   — 発注/実行層（空のパッケージ／拡張用）
    - monitoring/                  — 監視・メトリクス（拡張用）

---

## 開発・運用のヒント

- 自動 env ロードを無効化したいテスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパス（DUCKDB_PATH）は Settings.duckdb_path から参照されます。CI では ":memory:" を使うと便利です。
- J-Quants API の利用にはリフレッシュトークンが必要です。get_id_token() は settings.jquants_refresh_token をデフォルトで使用します。
- news_collector は既定で Yahoo Finance のビジネス RSS を使用します。カスタムソースを渡して収集可能です。
- ログレベルは LOG_LEVEL 環境変数で制御できます。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献方法を記載してください）

---

この README はコードベースの主要なモジュールと使い方を簡潔にまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）がプロジェクト内にある想定ですので、実運用や拡張を行う際はそれらの設計ドキュメントを参照してください。