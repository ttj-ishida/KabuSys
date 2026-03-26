# KabuSys

日本株向けの自動売買／バックテスト基盤ライブラリです。  
ファクター計算・特徴量構築・シグナル生成・ポートフォリオ構築・約定シミュレータ・バックテストエンジン、データ収集（J-Quants / RSS）などのコンポーネントを含みます。

バージョン: 0.1.0

## プロジェクト概要
KabuSys は、研究 → バックテスト → 実運用へとつなげるための日本株向けトレーディング基盤です。  
主な設計方針は以下の通りです。

- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）  
- DuckDB を用いたデータ管理とクエリ（軽量かつ高速）  
- 冪等なデータ保存（INSERT ... ON CONFLICT 等）  
- API クライアントのレート制御・リトライ・トークン自動更新  
- バックテストではシンプルなスリッページと手数料モデルを使用した擬似約定

## 主な機能一覧
- データ収集
  - J-Quants API クライアント（株価、財務、上場情報、マーケットカレンダー）
  - RSS ニュース収集＋記事の前処理・銘柄抽出
- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量構築 / シグナル生成
  - features テーブルの構築（ユニバースフィルタ・Z スコア正規化・クリップ）
  - ai_scores と統合して final_score を算出、BUY/SELL シグナル生成
  - Bear レジームでの BUY 抑制、エグジット（ストップロス等）
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額配分 / スコア加重配分 / リスクベース配分
  - セクター集中制限（1セクター上限）
  - ポジションサイズ算出（単元丸め、aggregate cap、部分約定の考慮）
- バックテスト
  - データをインメモリ DuckDB に複製して安全にバックテスト実行
  - PortfolioSimulator による擬似約定（BUY/SELL の処理・履歴保存）
  - 主要メトリクス計算（CAGR、Sharpe、MaxDD、勝率、Payoff）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 設定管理
  - .env ファイルおよび環境変数から設定を読み込み（自動読み込みを無効化可能）

## セットアップ手順（開発環境）
以下は最小限のセットアップ例です。実際の環境では pyproject.toml / requirements.txt に従ってください。

1. Python 環境を用意（推奨: Python 3.10+）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 主要な依存例（プロジェクトには duckdb, defusedxml 等が使われています）:
     - pip install duckdb defusedxml
   - その他、プロジェクトで使用するライブラリがあれば追記してください。

3. パッケージのインストール（開発モード）
   - プロジェクトルートに pyproject.toml / setup.cfg がある場合:
     - pip install -e .
   - 無ければ、PYTHONPATH を設定するか適宜パッケージ化してください。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を含む階層）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（最小の必須項目）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456789

- その他（任意）:
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

## 使い方

### DB スキーマ初期化（想定）
プロジェクトは DuckDB を想定しています。schema 初期化用ユーティリティ（kabusys.data.schema.init_schema）が存在する想定です。例:

    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

（注）init_schema の実装によりテーブル作成・マイグレーションが行われます。

### 特徴量構築（プログラムから）
    from datetime import date
    from kabusys.strategy import build_features
    from kabusys.data.schema import init_schema

    conn = init_schema("data/kabusys.duckdb")
    cnt = build_features(conn, target_date=date(2024, 1, 31))
    print(f"features upserted: {cnt}")
    conn.close()

### シグナル生成（プログラムから）
    from datetime import date
    from kabusys.strategy import generate_signals
    from kabusys.data.schema import init_schema

    conn = init_schema("data/kabusys.duckdb")
    n = generate_signals(conn, target_date=date(2024, 1, 31))
    print(f"signals written: {n}")
    conn.close()

### バックテスト（CLI）
付属の CLI でバックテストを実行できます。例:

    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb \
      --allocation-method risk_based --lot-size 100

主なオプション:
- --start / --end: 開始/終了日（YYYY-MM-DD）
- --cash: 初期資金（円）
- --slippage / --commission: スリッページ率 / 手数料率
- --allocation-method: equal | score | risk_based
- --max-positions, --max-utilization など多数（ヘルプ参照）

### バックテストをコードから呼ぶ
    from kabusys.backtest.engine import run_backtest
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    print(result.metrics)
    conn.close()

### データ収集（J-Quants / RSS）
- J-Quants からの取得:
  - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を使用して取得し、save_* 関数で DuckDB へ保存します。
  - 認証には JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token を参照）。
- RSS ニュース収集:
  - kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection を使用します。
  - defusedxml を使った安全なパース・SSRF ガード等を備えています。

## 環境変数一覧（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

注意: Settings は未設定の必須変数があると ValueError を投げます。`.env.example` を参考に `.env` を用意してください。

自動 .env ロードを無効化する場合:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

## ディレクトリ構成（主要ファイル）
以下は本リポジトリの主なファイル / モジュール構成の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - jquants_client.py            — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py            — RSS ニュース収集・前処理・保存
    - (schema.py 等: DB 初期化 / スキーマが想定される)
  - research/
    - factor_research.py           — Momentum / Volatility / Value 等の計算
    - feature_exploration.py       — IC / 将来リターン / 統計サマリー
  - strategy/
    - feature_engineering.py       — features テーブル構築
    - signal_generator.py          — final_score 計算と signals 生成
  - portfolio/
    - portfolio_builder.py         — 候補選定 / 重み計算
    - position_sizing.py           — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py                    — バックテストの全体実行ロジック
    - simulator.py                 — 擬似約定／ポートフォリオ管理
    - metrics.py                   — バックテストメトリクス計算
    - run.py                       — CLI エントリポイント
  - portfolio/ __init__.py         — 主要 API をエクスポート
  - strategy/ __init__.py
  - research/ __init__.py
  - backtest/ __init__.py

（備考）この README に含まれない他モジュール（data.schema, data.stats, data.calendar_management, monitoring 等）がプロジェクトに含まれている前提です。

## 開発上の注意 / 補足
- 各種処理は「target_date 時点のデータのみ」を用いる設計になっており、バックテストのルックアヘッドを防ぐよう配慮されています。データ取得・ETL の順序に注意してください。
- J-Quants 客のリトライ／レート制御は実装済みですが、運用では API 制限に注意してバッチ設計してください。
- NewsCollector は SSRF や XML 攻撃対策が組み込まれていますが、外部フィード追加時も慎重に扱ってください。
- 実運用（live）モードでの発注フロー・kabuステーション連携は別途 execution 層が必要です（src 内に execution パッケージのプレースホルダがあります）。

---

さらに詳しい仕様（StrategyModel.md、PortfolioConstruction.md、BacktestFramework.md、DataPlatform.md など）は別途ドキュメントを参照してください。README の内容やサンプルが不明瞭な点があれば、どの部分を詳しく書けばよいか教えてください。