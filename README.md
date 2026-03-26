# KabuSys

日本株向けの自動売買システムのライブラリ群です。データ収集（J-Quants / RSS）、特徴量計算、シグナル生成、ポートフォリオ構築、バックテスト、簡易シミュレータなど、研究→運用に必要なモジュールを含みます。

主な設計方針
- ルックアヘッドバイアス回避（時点データのみ使用、fetched_at 記録）
- 冪等性（DuckDB への保存は ON CONFLICT 等で重複を抑制）
- バックテストと本番ロジックの分離（DB を通じたスイッチング）
- シンプルで検証可能な純粋関数群（ポートフォリオ計算等）

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数チェック（settings オブジェクト）

- データ取得・保存
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動更新、ページネーション対応）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - ニュース収集（RSS → raw_news、銘柄抽出・紐付け）

- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ連携

- 特徴量エンジニアリング（strategy.feature_engineering）
  - 研究結果からユニバースフィルタ、正規化、features テーブルへの UPSERT を実行

- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの置換保存

- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）
  - 等配分 / スコア配分（calc_equal_weights, calc_score_weights）
  - リスク調整（セクター上限適用、レジーム乗数）
  - ポジションサイジング（risk_based / equal / score、単元丸め、aggregate cap）

- バックテスト（backtest）
  - データをインメモリ DuckDB にコピーして隔離したバックテストを実行（run_backtest）
  - ポートフォリオシミュレータ（部分約定、スリッページ・手数料モデル、マーク・トゥ・マーケット）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）
  - CLI エントリポイントあり（python -m kabusys.backtest.run）

- ニュース収集・前処理（data.news_collector）
  - RSS の安全な取得（SSRF対策・size制限・gzip対応）
  - 記事ID生成（正規化 URL → SHA-256）、記事保存、銘柄コード抽出

---

## セットアップ手順（開発環境）

以下は基本的な手順例です。実際の依存パッケージは requirements.txt を用意している場合はそちらを参照してください。主に使用している外部パッケージは duckdb, defusedxml などです。

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 仮想環境作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限 duckdb, defusedxml を入れる）
     - pip install duckdb defusedxml

4. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を作成することで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化も可）。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
   - 注意: settings は必須キーを _require() で検査します（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。

5. データベース初期化
   - 本プロジェクトでは DuckDB を使用します。スキーマ初期化用の関数（kabusys.data.schema.init_schema）が参照されています。プロジェクトにスキーマ初期化スクリプトがあればそれを実行してください。
   - 例（仮）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主要な実行例）

- バックテスト（CLI）
  - 事前に DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar 等が用意されている必要があります。
  - 実行例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb

  - 主なオプション: --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --lot-size など

- 特徴量構築（コード呼び出し例）
  - build_features は DuckDB 接続と target_date を受け取り features テーブルへ書き込みます。
    from datetime import date
    from kabusys.strategy import build_features
    conn = init_schema("data/kabusys.duckdb")
    build_features(conn, date(2024, 1, 31))

- シグナル生成（コード呼び出し例）
    from kabusys.strategy import generate_signals
    generate_signals(conn, date(2024, 1, 31), threshold=0.6)

- J-Quants データ取得と保存（例）
    from kabusys.data import jquants_client
    conn = init_schema("data/kabusys.duckdb")
    recs = jquants_client.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    jquants_client.save_daily_quotes(conn, recs)

- ニュース収集（RSS）
    from kabusys.data.news_collector import run_news_collection
    res = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
    # res は各 source ごとの新規保存件数を返す

- バックテストを Python API から呼ぶ（プログラム的に）
    from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    # result.history / result.trades / result.metrics を参照

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

注意: config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動ロードします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py

サブパッケージ:
- data/
  - jquants_client.py
  - news_collector.py
  - (schema.py など DB スキーマ関連モジュールを想定)
- research/
  - factor_research.py
  - feature_exploration.py
- strategy/
  - feature_engineering.py
  - signal_generator.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- backtest/
  - engine.py
  - simulator.py
  - metrics.py
  - run.py
  - clock.py
- execution/ (現状 __init__ のみ。発注・実行ロジックを配置する想定)
- monitoring/ (監視・アラート関連用のプレースホルダ)

各モジュールの役割（簡潔）
- data/*.py: 外部データ取得・ETL と DB への永続化
- research/*.py: ファクター計算・解析ユーティリティ
- strategy/*.py: 特徴量作成・シグナル生成ロジック
- portfolio/*.py: 候補選定・重み付け・サイジング・リスク調整
- backtest/*.py: バックテスト用のデータ準備、シミュレータ、メトリクス

---

## 開発/拡張のヒント

- features / signals / positions テーブルは日付単位で置換（冪等）する実装が多く、バックテストと運用で同じコードが使えるように設計されています。
- J-Quants クライアントは rate limiting / retry / token refresh を組み込んでいるため、ETL バッチから安全に呼べます。
- ニュース収集は SSRF 対策やサイズ上限、XML デコードの安全化を行っています。RSS パースの挙動は実データで必ず検証してください。
- 単元（lot）や銘柄ごとのルール拡張は portfolio.position_sizing の lot_size 引数や将来的な lot_map 拡張を通して取り込める設計です。

---

## 免責・注意事項

- このリポジトリは取引戦略の研究・検証を支援するためのフレームワークです。実運用の前に十分な検証を行ってください。
- 実際の資金投入・API 実行を行うモジュールは十分なテストと安全策（注文上限、ロギング、モニタリング）を実装した上で利用してください。
- ここに記載のコード断片・設定はサンプルであり、実取引に使用する際は自己責任での確認と法令順守をお願いします。

---

必要であれば README にサンプル .env.example や requirements.txt の雛形、スキーマ初期化手順、代表的な SQL スキーマ（テーブル定義）などを追加で作成します。どの情報を補足したいか教えてください。