# KabuSys

KabuSys は日本株向けの自動売買システムのライブラリ／ツール群です。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集などのコンポーネントを備え、研究（research）→ 本番（execution）までのワークフローをサポートします。

主な設計方針：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- idempotent（冪等）な DB 書き込み
- API レート制御・リトライ・トークン自動更新
- DuckDB を中心にデータを保持・処理

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユースケース）
- ディレクトリ構成（主要ファイル説明）
- 環境変数一覧と自動読み込みについて

---

プロジェクト概要
- 日本株のデータ取得（J-Quants）、ニュース収集（RSS）、加工（ETL）、特徴量計算、シグナル生成、バックテストを行うためのモジュール群。
- データ永続化に DuckDB を採用。analysis / research 用の関数は DB 接続を受け取り副作用を最小化する設計。

機能一覧
- データ取得・保存
  - J-Quants API クライアント（jquants_client）
    - 日足（OHLCV）、財務データ、マーケットカレンダー取得
    - レート制限、リトライ、401 のトークンリフレッシュ対応
  - ニュース（RSS）収集（news_collector）
    - RSS 取得、URL 正規化、記事 ID 生成、記事保存、銘柄抽出
- データ基盤
  - DuckDB スキーマ初期化・接続管理（data.schema）
  - ETL パイプライン（data.pipeline）: 差分更新、品質チェック（quality モジュールと連携）
  - 統計ユーティリティ（data.stats）: Z スコア正規化等
- 研究 / 特徴量
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、要約統計
  - feature_engineering（strategy）: 生ファクターの正規化・合成 → features テーブルへ保存
- 戦略・シグナル
  - signal_generator（strategy）: features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成
- バックテスト
  - engine: 日次ループで generate_signals を呼び出すフルバックテスト（run_backtest）
  - simulator: 擬似約定・ポートフォリオ状態管理（スリッページ・手数料モデル）
  - metrics: CAGR / Sharpe / 最大ドローダウン 等の算出
  - CLI エントリーポイント（kabusys.backtest.run）
- 実行層（execution）: 発注・実行インターフェース（パッケージのプレースホルダ）

---

セットアップ手順（開発 / 実行環境）
1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. Python 環境（推奨: 3.10+）を準備し仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - ":memory:" を指定するとインメモリ DB が作成されます（バックテスト等の一時処理で有用）。

5. 環境変数の設定
   - 必要な環境変数（下記「環境変数一覧」参照）を .env または OS 環境に設定。
   - パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を基準に自動で .env / .env.local を読み込みます（自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン。get_id_token で使用。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)
  - 有効値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)
  - 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 に設定すると .env 自動読み込みを無効化

.env のパースはシェルライクな形式をサポート（export 付きやクォート、コメント処理あり）。

---

使い方（主要な例）

1) DB スキーマ初期化
- Python:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

2) J-Quants からデータを取得して保存（概念例）
- API 呼び出しと保存（実行には JQUANTS_REFRESH_TOKEN が必要）
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)
  conn.close()

3) RSS ニュース収集
- 単一ソースのフェッチ + 保存
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと記事→銘柄の紐付けも実施
  result = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  conn.close()
  # result は {source_name: saved_count} を返す

4) 特徴量構築（features テーブルの作成）
- build_features を呼んで指定日分を作成（冪等）
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 3, 31))
  conn.close()
  # n は処理した銘柄数

5) シグナル生成（generate_signals）
- features / ai_scores / positions を読んで signals テーブルに書き込む
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,3,31))
  conn.close()

6) バックテスト（CLI 実行）
- 提示済みの DB（prices_daily, features, ai_scores, market_regime, market_calendar を含む）を用意した上で：
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

- run_backtest を Python API から呼ぶことも可能：
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import get_connection
  from datetime import date
  conn = get_connection("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()
  # result.history / result.trades / result.metrics が利用可能

7) ETL パイプライン（差分更新）
- data.pipeline モジュールの関数（例: run_prices_etl）を呼び、差分取得→保存→品質チェックを行います。
- 例（概念）：
  from kabusys.data.pipeline import run_prices_etl
  conn = init_schema("data/kabusys.duckdb")
  res = run_prices_etl(conn, target_date=date.today())
  # ETLResult 型を返し、取得件数・保存件数・品質問題などを含む

注意点
- 各処理（feature/build/signals/backtest）は target_date 単位で「日付分を一括削除して挿入」することで冪等性を保っています。
- J-Quants の API 制限（120 req/min）に合わせた内部レートリミッタ、リトライ、401 リフレッシュロジックを備えています。
- news_collector は SSRF 対策や XML パースの安全化（defusedxml）を行っています。

---

ディレクトリ構成（主要ファイルの概要）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数のロード・検証・Settings クラス（settings インスタンス）
    - .env 自動読み込みロジック（プロジェクトルート検出）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得／保存ユーティリティを含む）
    - news_collector.py
      - RSS フィード取得、記事保存、銘柄抽出
    - pipeline.py
      - ETL 差分更新・品質チェック
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
      - init_schema(), get_connection()
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 生ファクター統合 → features テーブルへ保存（Z スコア正規化 + クリッピング）
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（本体ループ・in-memory コピー・シミュレーション呼び出し）
    - simulator.py
      - PortfolioSimulator（擬似約定、マーク・トゥ・マーケット、トレード記録）
    - metrics.py
      - バックテスト評価指標計算（CAGR, Sharpe, MaxDD 等）
    - run.py
      - CLI エントリーポイント（python -m kabusys.backtest.run）
    - clock.py
      - SimulatedClock（将来拡張用）
  - execution/
    - __init__.py
    - （発注 API 周りの実装はここに配置）
  - monitoring/
    - （監視・メトリクス系の実装場所）

---

開発上の補足／注意事項
- DuckDB のバージョンや defusedxml 等の依存はプロジェクト要件に合わせて固定してください。
- schema.init_schema は初回作成時に親ディレクトリを自動作成します（db_path が ":memory:" でない場合）。
- news_collector の fetch_rss は外部ネットワークにアクセスするため、テスト時は _urlopen をモックして差し替える設計になっています。
- config の自動 .env 読み込みは、プロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

貢献・連絡
- バグ報告や機能提案はプルリクエスト / Issue を通してください。
- 大きな設計変更（スキーマや戦略モデルの変更）はドキュメント（StrategyModel.md / DataPlatform.md 等）を更新してください。

---

以上が README の概要です。追加で、実行例（具体的なコマンドやサンプルスクリプト）、環境（Docker / CI）向けの設定、.env.example のテンプレートなどを作成することもできます。希望があれば追記します。