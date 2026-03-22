# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データ基盤・バックテストフレームワークです。DuckDB をデータストアとして用い、J-Quants API や RSS ニュースを取り込み、ファクター計算・シグナル生成・バックテストまで一貫して実行できる設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 簡単な使い方（例）
- 環境変数
- ディレクトリ構成

---

プロジェクト概要
- 日本株の時系列データ・財務データ・ニュースを取得して DuckDB に格納し、
  ファクター生成（research）、特徴量エンジニアリング（strategy）、シグナル生成（strategy）、
  ポートフォリオシミュレーション（backtest）を行うパイプラインを提供します。
- 自動収集・差分更新（ETL）、品質チェック、バックテスト、模擬約定シミュレーション、
  ニュース収集と銘柄紐付けなどの機能を備えています。
- 設計上、ルックアヘッドバイアスを避けるため「target_date 時点で利用可能なデータのみ」を使う方針です。

---

機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（差分取得・ページネーション・自動トークン更新・レート制御）
  - RSS ニュース収集（SSRF 対策・トラッキングパラメータ除去・記事ID生成）
  - DuckDB スキーマ定義と初期化（init_schema）
- データ処理 / ETL
  - 差分 ETL（市場カレンダー・価格・財務データ等の差分取得を想定）
  - 品質チェック（quality モジュール想定）
- 研究 / ファクター
  - モメンタム・ボラティリティ・バリュー等のファクター計算（research/factor_research）
  - ファクター探索（IC, forward returns, 統計サマリー）
- 特徴量エンジニアリング（strategy/feature_engineering）
  - raw ファクターの正規化（Z スコア）、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（strategy/signal_generator）
  - features + ai_scores を統合して final_score を算出し BUY/SELL シグナル生成
  - Bear レジーム時の BUY 抑制、エグジット条件（ストップロス等）
- バックテスト（backtest）
  - run_backtest: 本番 DB からインメモリにコピーして日次ループでシミュレーション
  - ポートフォリオシミュレータ（スリッページ / 手数料モデル）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- その他ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - ニュースの銘柄抽出・DB 保存処理

---

必要条件
- Python 3.10 以上（| 型・型ヒントを使用しているため）
- 主な依存ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワーク経由で J-Quants / RSS にアクセスするためのインターネット接続
- 実運用では kabuステーション API（発注）や Slack 等の外部サービスの設定が必要

（インストール時に requirements.txt を用意している場合はそちらを利用してください）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他のライブラリもインストールしてください）

3. 環境変数を設定
   - プロジェクトルートに .env を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必要な環境変数例は後述の「環境変数」参照。

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトから:
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
   - これで必要なテーブルが作成されます（冪等）。

5. （任意）テスト用インメモリ DB
   - init_schema(":memory:") を使うとメモリ内 DB で動作確認できます。

---

使い方（例）
- Backtest CLI
  - 全体バックテストを CLI から実行できます（DB は事前にデータを用意しておく必要があります）。
  - 例:
    python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- スキーマ初期化（コマンドライン/スクリプト）
  - Python から:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    conn.close()

- データ収集（J-Quants から株価/財務データ）
  - jquants_client.get_id_token / fetch_daily_quotes / fetch_financial_statements を使い、取得後 save_* 関数で DuckDB に保存します。
  - pipeline.run_prices_etl / run_news_collection（news_collector）などの高レベル関数で ETL を実行する想定です。
  - 例（ニュース収集）:
    from kabusys.data.news_collector import run_news_collection
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
    conn.close()

- 特徴量構築とシグナル生成
  - build_features(conn, target_date)
    from kabusys.strategy import build_features
    import duckdb
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    build_features(conn, date(2024, 1, 4))
  - generate_signals(conn, target_date)
    from kabusys.strategy import generate_signals
    generate_signals(conn, date(2024, 1, 4))

- バックテスト API からプログラム実行
  - Python API を使う場合:
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest
    from datetime import date
    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    conn.close()
  - result.history / result.trades / result.metrics に結果が入ります。

- ETL の差分取得（pipeline）
  - kabusys.data.pipeline モジュールに差分更新ロジックがあります。既存 DB の最終取得日から差分を算出して API 取得・保存します。
  - ETL 実行結果は ETLResult 型で返り、品質問題やエラー一覧を含みます。

---

環境変数（主要）
- JQUANTS_REFRESH_TOKEN
  - J-Quants 用のリフレッシュトークン（必須: jquants_client がトークンを取得するため）
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（発注を行う場合に必要）
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN
  - Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID（必要に応じて）
- DUCKDB_PATH
  - デフォルトデータベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV
  - 動作モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動読み込みを無効化（テスト等で利用）

.env の自動ロード
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env があれば自動的に読み込まれます。
- 読み込み順: OS 環境変数 > .env.local > .env
- override の挙動やクォートのパースは config モジュールで実装されています。

推奨される .env の例（簡易）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント
    - news_collector.py               # RSS ニュース収集・保存
    - schema.py                       # DuckDB スキーマ定義・初期化
    - stats.py                        # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                     # ETL パイプライン
  - research/
    - __init__.py
    - factor_research.py              # ファクター計算（momentum/value/volatility）
    - feature_exploration.py          # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py          # features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py             # final_score 計算・シグナル生成
  - backtest/
    - __init__.py
    - engine.py                       # run_backtest 等のメインループ
    - simulator.py                    # PortfolioSimulator / TradeRecord
    - metrics.py                      # バックテストメトリクス計算
    - run.py                          # CLI エントリポイント
    - clock.py                        # SimulatedClock（将来の拡張用）
  - execution/                         # 発注・execution 層（空ファイルあり）
  - monitoring/                        # 監視用コード（未記載）
  - その他モジュール...

補足 / 注意点
- J-Quants の API レート制限やエラー処理（リトライ、トークン更新）を組み込んでいますが、運用時は API 利用規約に従ってください。
- DuckDB のスキーマは init_schema() で定義されており、既存テーブルがあればスキップされるため安全に呼べます。
- features / signals / positions テーブルは日付単位で置換（DELETE → INSERT）する処理が多く、冪等性を意識しています。
- 実際の売買（live）を組み合わせる場合、kabustation への発注部分や Slack 連携などの追加実装・安全対策が必要です。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑止できます。

---

貢献・開発
- バグ報告や機能提案は Issue を立ててください。
- 大きな API 変更を行う場合は関連ドキュメント（StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）を更新してください（本コードにはそれらの仕様を参照するコメントが含まれます）。

---

以上がプロジェクトの README です。必要であれば、README に含めるサンプル .env.example や具体的な ETL 実行スクリプト例、CI 用のテスト手順などを追記できます。どの部分を詳細化しましょうか？