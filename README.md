# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集などの機能をモジュール化して提供します。

- 現在のバージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要要件
- セットアップ手順
- 環境変数 (.env) と設定
- 使い方（主要ユースケース）
  - DB スキーマ初期化
  - バックテスト実行（CLI）
  - 特徴量のビルド / シグナル生成（Python API）
  - ニュース収集（Python API）
- ディレクトリ構成
- 補足 / 注意事項

---

プロジェクト概要
- KabuSys は日本株の戦略研究から実運用までを支援するための内部ライブラリです。
- データ取得（J-Quants）、データベース管理（DuckDB スキーマ）、ファクター計算・正規化、シグナル生成、バックテストシミュレーション、ニュース収集などを提供します。
- ルックアヘッドバイアスを避ける設計や冪等性（ON CONFLICT / トランザクション）を重視しています。

---

主な機能
- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動更新、ページネーション対応）
  - news_collector: RSS からのニュース収集（SSRF対策、トラッキング除去、記事ID生成、DB保存）
  - schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: ETL 管理（差分更新、バックフィル、品質チェック）
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算 / IC（Information Coefficient） / 統計サマリー
- strategy/
  - feature_engineering: ファクターの結合、フィルタ、Z スコア正規化、features テーブルへの保存
  - signal_generator: features + ai_scores を統合して final_score を計算し、BUY/SELL シグナルを signals テーブルへ挿入
- backtest/
  - engine: DB コピー → 日次ループで generate_signals を使ったシミュレーション
  - simulator: 約定（スリッページ/手数料）、ポートフォリオ状態管理、スナップショット生成
  - metrics: バックテストの主要指標（CAGR, Sharpe, Max DD, Win Rate 等）
  - run: バックテスト CLI エントリポイント
- execution/: 発注層（プレースホルダ）
- monitoring/: 監視／アラート関連（設定のみ）

---

必要要件
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装しています（requests などは不要）。

セットアップの一例
1. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # Unix/macOS
   .venv\Scripts\activate       # Windows
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

3. パッケージを開発モードでインストール（プロジェクトに pyproject/setup があれば）
   ```
   pip install -e .
   ```
   （※ 本リポジトリに pyproject.toml/setup.py がなければ、上の必須パッケージのみで動作する部分が多いです）

---

環境変数（.env）
- 本プロジェクトは .env ファイル（プロジェクトルート）または環境変数を参照します。
- 自動ロード: package import 時にプロジェクトルート（.git または pyproject.toml がある親）から .env → .env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- SLACK_BOT_TOKEN (必須) — Slack 連携用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db

簡単な .env 例（実際のシークレットは置き換えてください）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# オプション
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

使い方（抜粋）

1) DuckDB スキーマ初期化
- Python REPL / スクリプトから:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成/親ディレクトリも自動作成
  conn.close()
  ```

2) バックテスト（CLI）
- 付属のランナーを使ってバックテストを実行できます。DB は事前にデータ（prices_daily, features, ai_scores, market_regime, market_calendar 等）で埋めておく必要があります。
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
- オプション: --slippage, --commission, --max-position-pct

3) 特徴量ビルド（feature_engineering.build_features）
- DuckDB 接続と target_date（日付オブジェクト）を渡して features を計算・保存します。
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, date(2024, 3, 15))
  print(f"upserted {n} features")
  conn.close()
  ```

4) シグナル生成（strategy.signal_generator.generate_signals）
- features / ai_scores / positions を参照して signals テーブルへ BUY/SELL を書き込みます。
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  count = generate_signals(conn, date(2024, 3, 15))
  print(f"written {count} signals")
  conn.close()
  ```

5) ニュース収集（data.news_collector）
- RSS フィードを取得して raw_news + news_symbols を保存する一括ジョブがあります（関数: run_news_collection）。
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

6) ETL（データ取得）
- jquants_client.fetch_* と save_* を組み合わせて ETL を行います。pipeline モジュールは差分取得、バックフィル、品質チェックを補助します（API トークンは環境変数から取得されます）。
- 具体的な ETL ジョブは pipeline.run_prices_etl 等の関数を参照してください。

---

ディレクトリ構成（src/kabusys）
- __init__.py (パッケージ定義)
- config.py — 環境変数/設定管理（.env 自動ロード、設定プロパティ）
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - stats.py
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
  - run.py (CLI)
- execution/ (現状空のパッケージプレースホルダ)
- monitoring/ (監視関連モジュール用プレースホルダ)

※ 上記は src/tree を簡略化した構成です。実際のファイルはコメント・実装細部を含みます。

---

補足 / 注意事項
- J-Quants API クライアントはレート制限（120 req/min）と再試行・トークン自動更新ロジックを内蔵しています。ID トークンはモジュール内でキャッシュされます。
- DuckDB スキーマは外部キーの ON DELETE 動作が DuckDB のバージョンによってサポートに差があることを考慮して実装しています。データ削除時はアプリケーション側で順序を考慮してください（コメント参照）。
- 自動 .env 読み込みは便利ですが、テストや CI で不要な読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 本リポジトリには発注（execution）層の具体的な API 呼び出しや Slack 通知等の実装は最小限です。運用に用いる際は安全性・認証情報管理・監視等の追加実装が必要です。

---

貢献 / 開発
- バグ報告や機能改善提案は PR / Issue で歓迎します。
- テストは各モジュールを孤立して実行できるように設計してください（env 自動ロードを無効化できる仕組みあり）。

---

以上。必要であれば README に「セットアップの自動化（makeコマンド / scripts）」や「例となる .env.example ファイル」を追記できます。どの部分を拡充したいか教えてください。