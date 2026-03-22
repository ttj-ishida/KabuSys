# KabuSys

日本株向けの自動売買システム用ライブラリ群（研究・データ基盤・戦略・バックテスト・実行層）。  
このリポジトリは、データ収集（J-Quants / RSS）、ETL、特徴量生成、シグナル生成、バックテストシミュレータ、発注/実行レイヤーまでをカバーするモジュールで構成されています。

## 主な概要
- データ取得: J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新対応）
- データ基盤: DuckDB スキーマ定義と永続化ユーティリティ（冪等保存）
- ニュース収集: RSS からの記事収集と銘柄抽出（SSRF 対策、サイズ制限）
- 研究用ユーティリティ: ファクター計算・IC解析・Z スコア正規化など
- 戦略層: 特徴量エンジニアリング（features テーブル生成）とシグナル生成（BUY / SELL）
- バックテスト: 日次シミュレーションエンジン・約定モデル・メトリクス算出。CLI でのバックテスト実行が可能
- 実行層（骨子）: 発注 / ポジション / シグナルキュー に対応するテーブル群を定義

## 機能一覧（抜粋）
- 環境変数読み込み（.env / .env.local の自動読み込み、無効化フラグあり）
- J-Quants API クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系で DuckDB へ冪等保存
  - レートリミット制御、指数バックオフ、401 自動リフレッシュ
- ニュース収集
  - RSS フェッチ（gzip 対応、XML 安全パーサ使用）
  - 記事正規化・ID 生成・raw_news 保存・銘柄抽出・news_symbols 保存
- データスキーマ管理
  - DuckDB のテーブル定義と初期化（init_schema）
- ETL パイプライン（差分更新、バックフィル）
- 研究（research）モジュール
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（クロスセクション正規化）
- 戦略（strategy）
  - build_features(conn, target_date) — features テーブルを作成
  - generate_signals(conn, target_date, ...) — signals テーブルを作成
- バックテスト（backtest）
  - run_backtest(conn, start_date, end_date, ...)（プログラム / CLI）
  - ポートフォリオシミュレータ、メトリクス計算、約定モデル（スリッページ・手数料考慮）

## セットアップ手順（ローカル開発用）
1. Python 3.9+ を用意（typing の記法等を利用しています）
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - （プロジェクトが pip パッケージ化されている場合は `pip install -e .`）
   - ※ 他に logging 等の標準ライブラリを使用しています。必要に応じて追加パッケージを導入してください。
4. DuckDB スキーマ初期化
   - 以下のコマンドで初期スキーマを作成できます（例: data/kabusys.duckdb を作成）。
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
5. 環境変数の設定
   - プロジェクトルートに `.env` もしくは `.env.local` を配置することで自動読み込みされます（初期化時に .git/pyproject.toml を起点に探索）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

### 推奨する環境変数（例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

未設定の必須環境変数にアクセスすると ValueError が発生します（settings を介して取得）。

## 使い方（主要なユースケース例）

- DuckDB の初期化（スキーマ作成）
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- J-Quants からデータ取得 & 保存（サンプル）
  - Python スクリプト内で:
    - from kabusys.data.schema import init_schema
      from kabusys.data import jquants_client as jq
      conn = init_schema('data/kabusys.duckdb')
      records = jq.fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
      jq.save_daily_quotes(conn, records)
      conn.close()

- ニュース収集ジョブ（RSS）と保存
  - from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema('data/kabusys.duckdb')
    known_codes = {"7203","6758", ...}  # 有効な銘柄コード集合（任意）
    run_news_collection(conn, sources=None, known_codes=known_codes)
    conn.close()

- 特徴量生成（features）
  - from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features
    conn = init_schema('data/kabusys.duckdb')
    build_features(conn, target_date=date(2024,1,10))
    conn.close()

- シグナル生成
  - from kabusys.data.schema import init_schema
    from kabusys.strategy import generate_signals
    conn = init_schema('data/kabusys.duckdb')
    generate_signals(conn, target_date=date(2024,1,10), threshold=0.6)
    conn.close()

- バックテスト（CLI）
  - 必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）が populated されている DB を指定して実行:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
  - オプションで --cash / --slippage / --commission / --max-position-pct を指定可能

- バックテスト（プログラム的に）
  - from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest
    conn = init_schema('data/kabusys.duckdb')
    res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    print(res.metrics)

注意:
- run_backtest は本番 DB から必要なデータをインメモリ DB にコピーして実行するため、本番データを汚染しません。
- シグナル生成や feature の計算はルックアヘッドバイアスを避ける設計になっています（target_date 以前のデータのみ参照）。

## 主要モジュール・ディレクトリ構成
（プロジェクトの src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py      -- RSS ニュース収集・前処理・DB保存
    - schema.py              -- DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py               -- zscore_normalize 等の統計ユーティリティ
    - pipeline.py            -- ETL 差分更新・パイプライン処理
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_volatility / calc_value
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py -- build_features（features テーブル作成）
    - signal_generator.py    -- generate_signals（signals テーブル作成）
  - backtest/
    - __init__.py
    - engine.py              -- run_backtest（メインバックテストロジック）
    - simulator.py           -- PortfolioSimulator / 約定ロジック / マーク・トゥ・マーケット
    - metrics.py             -- バックテスト評価指標の計算
    - run.py                 -- CLI エントリポイント
    - clock.py               -- SimulatedClock（将来拡張用）
  - execution/               -- 発注/実行層（パッケージ骨子）
  - monitoring/              -- 監視・アラート系（骨子）

（詳しいファイル一覧はリポジトリツリーを参照してください）

## 開発・運用上の注意
- 環境変数は .env/.env.local 経由で自動読み込みされます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト用途）。
- DuckDB スキーマは冪等に作成されます。既存データを上書きしないため、安全に再初期化が可能です（ただし init_schema はテーブル作成のみで既存テーブルを削除しません）。
- J-Quants API の利用には refresh token が必要です（JQUANTS_REFRESH_TOKEN）。API レート制限を厳守する設計になっています。
- ニュース収集では SSRF や XML インジェクション対策を行っていますが、運用時は許可する RSS ソースを限定してください。
- 本ライブラリは「戦略ロジック／約定ルールのテンプレート」を提供します。実運用の際は必ずペーパートレードで検証し、資金管理・ログ・監査・障害対応を整えてください。

## トラブルシューティング
- 必須環境変数が足りない場合:
  - settings のプロパティ（例: settings.jquants_refresh_token）を参照すると ValueError が投げられます。`.env.example` を参考に必要値を設定してください。
- DuckDB に接続できない／ファイルが作成されない:
  - init_schema の引数パスの親ディレクトリが作成されるよう権限を確認してください。
- J-Quants API 呼び出しで 401 が返る:
  - get_id_token が自動リフレッシュを試みますが、リフレッシュトークン（JQUANTS_REFRESH_TOKEN）が無効の場合は更新に失敗します。トークン確認を行ってください。

---

その他、各モジュールの詳細実装や設計仕様（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）はリポジトリ内ドキュメントやモジュールの docstring を参照してください。README に記載されていないユースケースや CLI を追加する場合は、対応する module のエントリポイントを追記してください。