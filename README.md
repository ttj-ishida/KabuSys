# KabuSys

日本株向け自動売買システムのコアライブラリ（モジュール群）。  
市場データの取得・ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集などを含むヘッドレス（ライブラリ／CLI）実装です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（.env 例）
- ディレクトリ構成（主要ファイルの説明）
- 補足・運用注意点

---

プロジェクト概要
- KabuSys は日本株向けのアルゴリズム取引パイプラインのコア実装です。
- データ取得（J-Quants）、ETL、DuckDB スキーマ、ファクター計算（research）、特徴量生成（strategy.feature_engineering）、シグナル生成（strategy.signal_generator）、バックテスト（backtest）およびニュース収集（news_collector）を含みます。
- 発注／execution 層や外部 API への直接発注は本リポジトリの中心モジュールでは直接行わず、発注ロジックは execution レイヤーや別プロセスで扱う設計になっています。

---

機能一覧
- データ取得・保存
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レート制御）
  - RSS ニュース収集（SSRF 対策、トラッキング除去、前処理、銘柄抽出）
  - DuckDB へ冪等的に保存（ON CONFLICT / UPSERT）
- データ基盤
  - DuckDB スキーマ定義と初期化（init_schema）
  - 生データ層 / 処理済み層 / 特徴量層 / 実行層のテーブル定義
- ファクター／リサーチ
  - モメンタム、ボラティリティ、バリュー等のファクター計算（prices_daily / raw_financials を利用）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約
  - Zスコア正規化ユーティリティ
- 特徴量生成（feature_engineering）
  - 研究フェーズの生ファクターを正規化・合成して features テーブルへ UPSERT（date 単位で置換）
  - ユニバースフィルタ（最低株価・流動性）適用、Zスコア ±3 クリップ
- シグナル生成（signal_generator）
  - features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を重み付けして final_score を算出
  - Bear レジーム検出による BUY 抑制、SELL（エグジット）判定、signals テーブルへの冪等書き込み
- バックテスト
  - インメモリ DuckDB にデータをコピーして日次ループでシミュレーション（run_backtest）
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）、日次スナップショット、トレード履歴
  - バックテストメトリクス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ETL パイプライン（data.pipeline）
  - 差分更新、バックフィル（後出し修正吸収）、品質チェックフック（quality モジュール利用）

---

セットアップ手順（開発環境向け）
1. Python をインストール（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows
3. 依存ライブラリのインストール（プロジェクトに requirements.txt がなければ主要依存を個別インストール）
   - pip install duckdb defusedxml
   - その他必要に応じて logging 等の標準ライブラリ以外を追加
   - 開発モードインストール（プロジェクトのルートに pyproject.toml / setup.cfg がある場合）
     - pip install -e .
4. データベースの初期化（例）
   - Python REPL やスクリプトで：
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - またはインメモリで試す:
     from kabusys.data.schema import init_schema
     conn = init_schema(":memory:")
5. 環境変数の設定
   - プロジェクトルートの .env / .env.local を用意（下に例を記載）
   - 自動ロードはデフォルトで有効。不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化。

---

環境変数（.env 例）
最低限必要な環境変数（本番的運用では必須）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development  # allowed: development, paper_trading, live
- LOG_LEVEL=INFO

データベースパス（任意デフォルトあり）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

例 (.env)
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb

注意:
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードします。
- .env.local は .env を上書き（override=True）しますが、OS 環境変数は保護されます。
- テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

簡単な使い方（コード例）
- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- ETL（株価差分取得）※ pipeline の run_prices_etl などを呼ぶ
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- 特徴量生成（features テーブルを作成）
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date(2024, 1, 10))
  # -> features テーブルへ date=2024-01-10 のレコードを日付単位で置換（冪等）

- シグナル生成（signals テーブルを作成）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date(2024, 1, 10))
  # -> signals テーブルへ BUY/SELL を日付単位で置換（冪等）

- バックテスト（CLI）
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  # オプション: --cash, --slippage, --commission, --max-position-pct

- バックテスト（プログラムから）
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date)
  # result.history / result.trades / result.metrics を参照

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"}, timeout=30)

注意:
- 各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- 多くの書き込みは「日付単位の置換（DELETE WHERE date = ? の後に INSERT）」で実装されており冪等です。
- generate_signals は positions テーブルを参照して SELL 判定を行うため、バックテスト等で positions を適切に書き戻す必要があります（run_backtest はこの処理を含みます）。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（J-Quants トークン、kabu API、Slack、DB パス等）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL 差分更新 / run_prices_etl 等（品質チェックフロー）
  - research/
    - __init__.py
    - factor_research.py
      - mom / volatility / value のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、factor_summary、rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features 作成（ユニバースフィルタ・正規化・UPSERT）
    - signal_generator.py
      - final_score 計算、BUY/SELL 生成、signals テーブル書込
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（インメモリ DB コピー、日次ループ）
    - simulator.py
      - PortfolioSimulator（擬似約定、履歴、トレード記録）
    - metrics.py
      - バックテスト指標計算
    - run.py
      - バックテスト CLI エントリポイント
    - clock.py
      - SimulatedClock（将来拡張用）
  - execution/
    - __init__.py
    - （execution 層の実装場所／拡張ポイント）
  - monitoring/
    - （監視／メトリクス関連の実装場所）

---

補足・運用注意点
- セキュリティ
  - news_collector は SSRF 対策（ホスト検証・リダイレクト検査）や XML パースの安全化（defusedxml）を実装していますが、外部ネットワークに対するアクセスの権限設定は運用側で慎重に管理してください。
- レート制限とリトライ
  - J-Quants クライアントは 120 req/min に合わせた固定間隔スロットリングと指数的バックオフを実装しています。大量取得時は制限に注意してください。
- 冪等性
  - データ保存（raw_prices / raw_financials / raw_news 等）は基本的に冪等（ON CONFLICT）で実装されています。ただし運用での同時実行や手動 DB 操作では注意が必要です。
- テスト／デバッグ
  - init_schema(":memory:") を使うことでインメモリ DB 上で素早くユニットテストや手動検証が可能です。
- 環境（KABUSYS_ENV）
  - KABUSYS_ENV により開発／ペーパー／実運用ロジックの分岐が可能です。live 運用時は特に注意して設定してください。

---

お問い合わせ・拡張
- この README はコードベースから自動的に要点を抜粋してまとめています。各モジュールの詳細な使い方やパラメータ仕様は該当ソースコードの docstring / コメントを参照してください。
- execution 層（kabu API 経由の発注等）や外部通知（Slack 連携）などの統合は別モジュールでの実装／拡張を想定しています。

--- 

以上。初期セットアップや運用に関する具体的なコマンドやサンプルが必要であれば、使いたいユースケース（例：全データ ETL → feature ビルド → signal 生成 → バックテスト）を指定してください。必要に応じてステップごとの具体的なコマンド例を作成します。