# KabuSys

日本株のデータプラットフォームと自動売買（バックテスト／運用）を想定した Python パッケージです。  
DuckDB をデータレイクにして、J-Quants からのデータ取得、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを想定した構成の自動売買基盤です。

- Raw Layer: API や RSS から取得した生データ（株価、財務、ニュース等）
- Processed Layer: 集計・整形済みの市場データ（prices_daily 等）
- Feature Layer: 戦略や AI に供する特徴量（features, ai_scores 等）
- Execution Layer: シグナル、発注、約定、ポジション、監査ログ

主な設計方針:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- DuckDB を中心に冪等性を意識したデータ保存（ON CONFLICT / トランザクション）
- API レート制御・再試行・トークン自動更新などの堅牢化
- 外部ライブラリへの過度な依存を避け、標準ライブラリ中心で記述

---

## 機能一覧

- 環境変数 / .env のロードと設定管理（kabusys.config）
- J-Quants API クライアント（jquants_client）:
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得、保存
  - レートリミット・リトライ・トークンリフレッシュ対応
- ETL パイプライン（data.pipeline）:
  - 差分取得・バックフィル・品質チェックを含む日次 ETL
- DuckDB スキーマ定義・初期化（data.schema）
- ニュース収集（data.news_collector）:
  - RSS 取得、前処理、記事保存、銘柄抽出（SSRF/サイズ制限対策あり）
- カレンダー管理（data.calendar_management）:
  - 営業日判定、next/prev_trading_day、夜間カレンダー更新ジョブ
- 研究用ファクター計算（research.factor_research）:
  - Momentum / Volatility / Value 等のファクター計算
- 特徴量作成・正規化（strategy.feature_engineering）
- シグナル生成（strategy.signal_generator）:
  - ファクター・AI スコアの統合、BUY/SELL シグナル生成、エグジット判定
- 統計ユーティリティ（data.stats）
- 監査ログ（data.audit）: 発注から約定までのトレーサビリティ構築

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションに `X | None` を使用）
- DuckDB（Python パッケージとしてインストール）
- ネットワークアクセス（J-Quants API / RSS）

1. リポジトリをクローンしてインストール（開発モード推奨）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```
   あるいは requirements があれば:
   ```bash
   pip install -r requirements.txt
   ```

2. 環境変数を準備する
   プロジェクトルートに `.env` を置くことで自動読み込みされます（ローカルテスト時は `.env.local` も読み込まれます）。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabu ステーション API パスワード（execution 層で使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

   任意 / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   Python REPL やスクリプトからスキーマを初期化します。

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（代表的な例）

以下はライブラリAPIの利用例です。実運用ではログや例外ハンドリング、ジョブスケジューラ（cron / systemd / Airflow 等）と組み合わせてください。

- 日次 ETL の実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）:

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（build_features）:

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema(settings.duckdb_path)
  n = build_features(conn, target_date=date(2024, 1, 5))
  print(f"features upserted: {n}")
  ```

- シグナル生成（generate_signals）:

  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS）:

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema(settings.duckdb_path)
  # known_codes: 事前に取得した有効銘柄コードの set（抽出に利用）
  # sources: dict (source_name -> rss_url) を渡せる
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新ジョブ（夜間バッチ）:

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")
  ```

---

## ディレクトリ構成

主要なファイル／モジュールは以下の通りです（プロジェクトルートの `src/kabusys/` 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定の読み込み・検証
  - execution/
    - __init__.py                   — 発注・ブローカー統合などの実装ポイント（空の初期化）
  - strategy/
    - __init__.py
    - feature_engineering.py        — ファクター正規化・features テーブルへの保存
    - signal_generator.py           — final_score 計算と signals 生成
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value の計算
    - feature_exploration.py        — 将来リターン計算、IC、統計サマリー
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集・前処理・保存・銘柄抽出
    - calendar_management.py        — マーケットカレンダー管理 / ジョブ
    - audit.py                      — 発注〜約定の監査ログスキーマ
    - features.py                   — features 用エクスポート（zscore 再エクスポート）
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
  - monitoring/                      — 監視・メトリクス関連（将来的に実装）
  - その他ドキュメント（README や設計 MD を想定）

（上記は現在の主要なモジュールの一覧です。各ファイル内に詳細な関数 docstring が記載されています。）

---

## トラブルシューティング / 注意点

- Python バージョン: 3.10 以上を推奨（型表現に union 型を使用）。
- .env 自動読み込み:
  - プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します。
  - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- J-Quants API:
  - レート制限（120 req/min）を守るため内部でスロットリングを行います。大量取得時は時間がかかる点に注意。
  - 401 を受けた場合は refresh token による自動更新を試みます。
- DuckDB のファイルパス:
  - `DUCKDB_PATH` の親ディレクトリは自動作成されますが、書き込み権限に注意してください。
- ニュース収集:
  - RSS の巨大レスポンスや圧縮攻撃を避けるため最大サイズ制限や Gzip 解凍後チェックを行っています。
  - SSRF 対策を複数段で実装していますが、社内運用で許可ドメインを設ける運用を推奨します。
- シグナル生成:
  - Bear レジーム判定や保有ポジションのエグジット条件はコード内にポリシー実装があります。変更する場合は仕様ドキュメント（StrategyModel.md など）に従ってください。

---

## 開発・貢献

- 各モジュールに詳細な docstring と設計注記が書かれています。新機能追加や修正は既存の設計方針を尊重してください（ルックアヘッド防止、冪等性、トランザクションでの原子操作など）。
- テストや CI の導入を推奨します（特に jquants_client の HTTP 部分や news_collector のネットワーク処理はモックによる単体テストが重要です）。

---

以上。README のサンプルとして必要に応じて導入手順や運用フロー、環境の具体例（systemd unit / cron ジョブ / docker-compose）等を追記できます。追記希望があれば目的（開発 / 本番運用 / Docker 化 など）を教えてください。