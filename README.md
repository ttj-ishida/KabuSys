KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、バックテスト、ニュース収集までを備えたモジュール群を提供します。

主な目的
- 市場データの差分取得と DuckDB への保存（冪等）
- 研究用ファクター計算・探索（research）
- 戦略用特徴量作成・シグナル生成（strategy）
- バックテストフレームワーク（backtest）
- ニュース収集・銘柄紐付け（news）
- DuckDB スキーマ定義・ユーティリティ（data）

機能一覧
- data/
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
  - pipeline: 差分ETL（prices / financials / calendar など）
  - news_collector: RSS 収集・前処理・DB保存・銘柄抽出（SSRF/サイズ上限対策あり）
  - schema: DuckDB スキーマ初期化・接続
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value などのファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリ
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
  - signal_generator: final_score の計算、BUY/SELL の判定、signals テーブルへの保存
- backtest/
  - engine: run_backtest（本番 DB からインメモリにコピーして日次ループでシミュレーション）
  - simulator: 擬似約定・ポートフォリオ管理（スリッページ・手数料モデル）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, WinRate など）
  - run.py: CLI エントリポイント（バックテスト実行）
- config: 環境変数読み込み（.env/.env.local 自動ロード）, settings オブジェクト
- execution / monitoring: 発注・監視用の拡張ポイント（パッケージ公開インターフェース用）

セットアップ手順（開発環境向け）
1. Python のインストール
   - 推奨: Python 3.10 以上

2. 必要パッケージのインストール（例）
   - duckdb, defusedxml が必須で使われています。その他ライブラリは各機能に応じて追加してください。
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください。）

3. リポジトリルートに .env ファイルを配置
   - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基に自動で .env/.env.local を読み込みます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須: data.jquants_client で API を使う場合）
   - KABU_API_PASSWORD    : kabu ステーション API のパスワード（execution 関連で使用）
   - SLACK_BOT_TOKEN      : Slack 通知用 Bot トークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID     : Slack チャンネル ID（通知先）
   - DUCKDB_PATH          : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH          : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV          : 実行環境 ("development" / "paper_trading" / "live")（default: development）
   - LOG_LEVEL            : ログレベル ("DEBUG","INFO",...)（default: INFO）

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

初期データベースの作成
- DuckDB スキーマを初期化するサンプル:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ
  conn.close()
  ```

基本的な使い方（抜粋）
- バックテスト（CLI）
  - 事前に DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を用意してください。
  - 実行例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb

- 特徴量のビルド（コードから）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 5))
  print("upserted features:", n)
  conn.close()
  ```

- シグナル生成（コードから）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 5))
  print("signals generated:", total)
  conn.close()
  ```

- ETL（データ取得）/ ニュース収集（例）
  - jquants_client を使ってデータを取得し、save_* 関数で保存します。
  - ニュース収集は run_news_collection を使用できます。

  サンプル: RSS 収集と保存
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 銘柄一覧
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

注意点・設計上のポイント
- 設計はルックアヘッドバイアス回避を重視しています。特徴量・シグナル生成は target_date 時点までのデータのみを使用します。
- DuckDB への保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で行うように実装されています。
- J-Quants クライアントはレート制限（120 req/min）に従い、指数バックオフ・トークン自動更新を行います。
- RSS 収集は SSRF 対策、gzip サイズ制限、XML パース安全化（defusedxml）などセキュリティ対策を行っています。
- config.Settings は .env/.env.local を自動読み込みします。OS 環境変数が優先され、.env.local は .env を上書きします。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能です。

ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
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
    - metrics.py
    - simulator.py
    - clock.py
    - run.py
  - execution/
    - __init__.py
  - monitoring/
    - (監視関連モジュールを配置予定)

開発・拡張
- 新しい ETL / 解析ジョブは data.pipeline に追加し、既存の save_* 関数や schema を利用してください。
- 戦略の変更は strategy 以下に実装し、generate_signals / build_features の仕様に従ってください（ルックアヘッド回避の原則を守ること）。
- バックテストエンジンは DB を改変しないようインメモリコピーを作成します。run_backtest 呼び出し時は読み取り専用の conn を渡してください。

ライセンス・貢献
- （ここにプロジェクトのライセンス情報を記載してください）

問い合わせ
- 実運用に用いる際は API トークン管理・運用監視・発注ロジックのテストを十分に行ってください。README の不足点や追加してほしい項目があれば教えてください。