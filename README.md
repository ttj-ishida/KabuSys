# KabuSys

KabuSys は日本株の自動売買・研究パイプラインを目的とした Python パッケージです。データ取得（J-Quants）、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテストまで一貫して扱えるモジュール群を備えています。

---

## 概要

- 名称: KabuSys
- 説明: 日本株アルファ探索からポートフォリオ構築、バックテスト、データ取得・ニュース収集までを含む自動売買研究基盤。
- 設計方針:
  - DuckDB を用いた時系列データ管理と分析
  - ルックアヘッドバイアス防止（target_date ベースの処理）
  - 冪等な DB 書き込み（ON CONFLICT 等）
  - テスト・研究用途と実運用（paper/live）を想定した設定分離

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント (`kabusys.data.jquants_client`)：日足・財務・カレンダー等の取得、DuckDB への保存機能
  - ニュース収集 (`kabusys.data.news_collector`)：RSS 取得、記事正規化、raw_news 保存、銘柄抽出（SSRF 対策、gzip 上限等）
- 研究（research）
  - ファクター計算 (`kabusys.research.factor_research`)：モメンタム、ボラティリティ、バリュー等
  - ファクター探索・解析 (`kabusys.research.feature_exploration`)：将来リターン、IC、統計サマリー等
- 特徴量・シグナル生成（strategy）
  - 特徴量構築 (`kabusys.strategy.feature_engineering`)：Z スコア正規化・ユニバースフィルタ
  - シグナル生成 (`kabusys.strategy.signal_generator`)：複数ファクター + AI スコア統合、BUY/SELL 判定、signals テーブル書き込み
- ポートフォリオ（portfolio）
  - 候補選定・配分 (`portfolio_builder`)
  - ポジションサイズ計算・単元丸め (`position_sizing`)
  - セクター上限・レジーム乗数 (`risk_adjustment`)
- バックテスト（backtest）
  - シミュレータ (`simulator`)：擬似約定、ポートフォリオ履歴・約定記録保持
  - エンジン (`engine`)：バックテストループ、シグナルの読み込み → 約定 → マーク・トゥ・マーケットの流れ
  - メトリクス計算 (`metrics`)：CAGR, Sharpe, MaxDD, 勝率等
  - CLI ラッパー (`backtest.run`)：コマンドラインからバックテスト実行
- 実行・監視層（パッケージ構造上は存在。将来的な拡張）

---

## 必要な環境・依存

- Python 3.10 以上（型ヒントの「|」等を使用）
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml
  - （環境に応じて）他に HTTP など標準ライブラリを利用

※プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - もし pyproject.toml / requirements.txt があればそれを使う:
     - pip install -r requirements.txt
     - または pip install -e .（プロジェクトがビルド可能な場合）
   - 最低限: duckdb と defusedxml
     - pip install duckdb defusedxml

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くことで自動読み込みされます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...        # J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD=...            # kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN=...              # Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID=...             # Slack チャンネル ID（必須）
   - 任意／デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=INFO                           (default: INFO)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1         (自動 .env ロードを無効化)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主な例）

- バックテスト（CLI）
  - コマンド:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - 主なオプション:
    - --cash 初期資金（JPY）
    - --slippage スリッページ率
    - --commission 手数料率
    - --allocation-method equal|score|risk_based
    - --max-positions 最大保有銘柄数
    - --lot-size 単元株数（デフォルト 100）
  - 出力: コンソールにバックテスト結果（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, TotalTrades）を表示。

- 特徴量構築（プログラム的呼び出し）
  - 例（DuckDB 接続が init_schema により取得できることを想定）:
    - from kabusys.data.schema import init_schema
    - from kabusys.strategy.feature_engineering import build_features
    - conn = init_schema("path/to/kabusys.duckdb")
    - count = build_features(conn, target_date=date(2024, 1, 31))
    - conn.close()

- シグナル生成（プログラム的呼び出し）
  - from kabusys.strategy.signal_generator import generate_signals
  - generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  - 各ソースごとの新規保存件数が返る。

- J-Quants からのデータ取得（例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - data = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, data)

- プログラム内での構成取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.is_live などが利用可能

---

## 主要モジュールと役割（簡易）

- kabusys.config
  - 環境変数の自動読み込み（.env, .env.local）と Settings クラス
- kabusys.data
  - jquants_client.py: J-Quants API（取得 + DuckDB 保存）
  - news_collector.py: RSS 取得、前処理、raw_news 保存、銘柄抽出
- kabusys.research
  - factor_research.py: 各種定量ファクター計算
  - feature_exploration.py: 将来リターン・IC 等の解析ユーティリティ
- kabusys.strategy
  - feature_engineering.py: features テーブル作成
  - signal_generator.py: features と ai_scores を統合し signals テーブルへ書き込み
- kabusys.portfolio
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定・サイジング・リスク制御
- kabusys.backtest
  - engine.py: バックテスト主ループ
  - simulator.py: 擬似約定・ポートフォリオ管理
  - metrics.py: 評価指標
  - run.py: CLI エントリポイント

---

## ディレクトリ構成

（リポジトリのルートに src/ 配下でパッケージ化されている想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - jquants_client.py
      - news_collector.py
      - (他: schema.py, calendar_management.py 等)
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - strategy/
      - feature_engineering.py
      - signal_generator.py
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - backtest/
      - engine.py
      - simulator.py
      - metrics.py
      - run.py
      - clock.py
      - __init__.py
    - execution/  (将来的な実行層)
    - monitoring/ (モニタリング用 DB 等)
    - portfolio/ ...
  - (その他: pyproject.toml, .git, README.md, .env.example など)

---

## 注意事項 / 運用上のヒント

- Look-ahead バイアスに注意
  - 多くの関数は target_date 時点で利用可能なデータだけを使用している設計です。データ投入タイミングとバックテスト用 DB の整合性に注意してください。
- 環境変数の自動読み込み
  - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます。テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベル / 実行モード
  - KABUSYS_ENV で development / paper_trading / live を切り替えられます。settings.is_live などで判定可能です。
- スキーマ
  - 本プロジェクトは DuckDB のスキーマを前提に設計されています。`kabusys.data.schema.init_schema` 等で DB を初期化・接続することを想定しています（schema.py を参照してください）。

---

もし README に含めてほしい「より詳細な設定例」「CI の設定」「デプロイ手順」等があれば教えてください。README の英語版や簡易チュートリアル（サンプルデータでの実行手順）も追加できます。