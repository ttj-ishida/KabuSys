# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、DuckDB スキーマなどを含むモジュール群で構成されています。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB を中心としたローカル DB（ファイルまたはインメモリ）
- 冪等（idempotent）な DB 操作（ON CONFLICT / トランザクション）
- 外部 API 呼び出しは専用クライアント経由でレート制御・リトライを実装
- 研究（research）層と実運用（strategy/execution）層を分離

---

## 機能一覧

- data/
  - J-Quants API クライアント（jquants_client）
    - 日足データ・財務データ・マーケットカレンダー取得
    - レートリミット・リトライ・トークン自動更新対応
  - News Collector（news_collector）
    - RSS 収集、前処理、記事ID生成、銘柄抽出、DB 保存
    - SSRF 対策・XML ハンドリング（defusedxml）
  - DuckDB スキーマ定義と初期化（schema）
  - ETL パイプライン（pipeline）
  - 汎用統計ユーティリティ（stats）
- research/
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary）
- strategy/
  - 特徴量合成（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）
- backtest/
  - ポートフォリオシミュレータ（simulator）
  - バックテストエンジン（engine.run_backtest）
  - 評価指標（metrics）
  - CLI エントリポイント（backtest.run）
- execution/（発注関連の拡張ポイント用ディレクトリ）
- config.py
  - 環境変数管理（.env 自動読み込み、必須チェック、環境判定）

---

## 前提条件

- Python 3.10 以上（型ヒントに `|` を使用しているため）
- 依存パッケージ（最低限）:
  - duckdb
  - defusedxml

推奨：仮想環境（venv / pyenv）を利用してください。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを入手）

2. 仮想環境作成・有効化（例）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - ソースを開発モードでインストールできる場合:
     ```
     pip install -e .
     ```
     （プロジェクトに setup/pyproject があれば利用）

4. 環境変数設定
   - ルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知チャネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用途 SQLite（デフォルト: data/monitoring.db）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-....
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python から直接:
     ```
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```
   - これにより必要なテーブルがすべて作成されます（冪等）。

---

## 使い方（代表的な操作例）

- DuckDB 接続を作る:
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema('data/kabusys.duckdb')  # 初回のみ
  # 既存 DB に接続する場合:
  # conn = get_connection('data/kabusys.duckdb')
  ```

- J-Quants から日足を取得して保存:
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  print('saved', saved)
  conn.close()
  ```

- ニュース収集ジョブ（RSS -> raw_news + news_symbols）:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  # known_codes: 銘柄コード集合（抽出用）
  res = run_news_collection(conn, known_codes={'7203','6758'})
  print(res)
  conn.close()
  ```

- 特徴量生成（features テーブルの作成 / 上書き）:
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  cnt = build_features(conn, target_date=date(2024,3,15))
  print('features upserted:', cnt)
  conn.close()
  ```

- シグナル生成（signals テーブルの作成 / 上書き）:
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  total = generate_signals(conn, target_date=date(2024,3,15))
  print('signals written:', total)
  conn.close()
  ```

- バックテスト（Python API）:
  ```python
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

---

## 環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 使用時)
- SLACK_BOT_TOKEN (必須 使用時)
- SLACK_CHANNEL_ID (必須 使用時)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 をセットすると .env 自動読み込みを無効化)

config.Settings クラスを通じてプログラム内から取得できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py
  - execution/
    - __init__.py
  - monitoring/ (存在を示唆するモジュール一覧に合わせた実装可能領域)
  - backtest.run（モジュールエントリ）

この README に記載の API（関数名・引数・返り値）はソース内 docstring と実装に基づきます。実際の運用では DB の事前準備（prices_daily 等のデータ）や API トークン管理を必ず行ってください。

---

## 運用上の注意

- J-Quants API はレート制限があります。jquants_client は内部で固定間隔スロットリングとリトライを実装していますが、運用時は過剰な同時処理を避けてください。
- DuckDB のファイルを共有ストレージで同時書きすると競合が発生する可能性があります。複数プロセスでの同時書き込みは避けるか設計を明確にしてください。
- features / signals / positions 等は日付単位で置換（DELETE → INSERT）を行うため、過去日付の再計算・差分更新は意図的に行ってください。
- ニュース RSS 取得では外部 URL の検証・SSRF 対策を行っていますが、運用で新しいソースを追加する際は URL と取得頻度に注意してください。

---

この README はコードベースの主要機能と利用方法をまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）がある前提の実装になっているため、追加の設計ドキュメントがある場合はそちらも参照してください。