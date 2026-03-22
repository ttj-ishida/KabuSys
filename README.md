# KabuSys

KabuSys は日本株の自動売買を想定したモジュール型システムです。  
データ取得（J-Quants、RSS）→ ETL → 研究（ファクター計算）→ 特徴量作成 → シグナル生成 → バックテスト → （実運用）実行 のワークフローを段階的に実装しています。  
（本リポジトリはライブラリ/フレームワーク部分を含み、発注レイヤーや運用監視は別途実装／設定が必要です。）

主な設計方針
- ルックアヘッドバイアスを回避するデータ設計（fetched_at 等による取得時刻の記録）
- DuckDB ベースのローカル DB スキーマ（冪等性を意識した INSERT/ON CONFLICT）
- 外部依存を最小化（標準ライブラリ + 必要最小限のライブラリ）
- テストしやすい構成（関数に依存注入が可能、DB を :memory: で初期化可能）

---

## 機能一覧（モジュール概観）

- kabusys.config
  - 環境変数管理（.env 自動ロード / 必須値チェック）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・レート制御・リトライ）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出（SSRF 対策・gzip対策）
  - schema: DuckDB スキーマ定義と初期化
  - pipeline: ETL ジョブ（差分取得・バックフィル・品質チェック呼び出し）
  - stats: z-score 正規化などの統計ユーティリティ
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- kabusys.strategy
  - feature_engineering: 生ファクターの正規化・フィルタ・features テーブルへの書込み
  - signal_generator: features と ai_scores を統合して BUY / SELL シグナルを生成
- kabusys.backtest
  - engine: バックテストの主ループ（DB コピー → 日次ループ → シグナル適用）
  - simulator: 擬似約定・ポートフォリオ管理（スリッページ/手数料モデル）
  - metrics: バックテスト評価指標計算（CAGR, Sharpe, MaxDD, WinRate, Payoff）
  - run: CLI エントリ（python -m kabusys.backtest.run）
- その他
  - news_collector の URL 正規化・銘柄抽出ロジック、J-Quants の保存関数（raw → processed）など

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで | 型を使用）
- Git が使える環境（.env 自動検出でプロジェクトルートを探索）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要ライブラリをインストール
   - 最低限必要なライブラリ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください）

4. パッケージを編集インストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートの `.env` または環境変数を用意します。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意)
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

   - .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

6. DB 初期化
   - Python REPL で:
     ```
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - またはスクリプトから呼び出してください。":memory:" を指定するとインメモリ DB になります。

---

## 使い方（主要な操作例）

以下は代表的な操作の最小例です。各関数は duckdb の接続オブジェクト（DuckDBPyConnection）を受け取ります。

1. DuckDB を初期化して接続を取得
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. J-Quants から株価を取得して保存
   ```
   from kabusys.data import jquants_client as jq
   records = jq.fetch_daily_quotes(date_from=...)
   saved = jq.save_daily_quotes(conn, records)
   ```

3. ニュース収集（RSS）を実行
   ```
   from kabusys.data.news_collector import run_news_collection
   # known_codes: 銘柄抽出に使う有効コードセット（例: {'7203','6758',...}）
   results = run_news_collection(conn, known_codes=known_codes)
   ```

4. ETL（差分更新）: 株価 ETL の例
   ```
   from kabusys.data.pipeline import run_prices_etl
   from datetime import date
   fetched, saved = run_prices_etl(conn, target_date=date.today())
   ```

5. 特徴量作成（features テーブル作成）
   ```
   from kabusys.strategy import build_features
   from datetime import date
   count = build_features(conn, target_date=date(2024, 02, 01))
   ```

6. シグナル生成（signals テーブル作成）
   ```
   from kabusys.strategy import generate_signals
   from datetime import date
   total_signals = generate_signals(conn, target_date=date(2024, 02, 01))
   ```

7. バックテスト実行（CLI）
   - コマンド例:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - 引数:
     - --start / --end : バックテスト期間（YYYY-MM-DD）
     - --cash : 初期資金（円）
     - --slippage / --commission : 手数料・スリッページ率
     - --max-position-pct : 1銘柄あたりの最大ポートフォリオ比率
     - --db : DuckDB ファイルパス

8. ライブラリ API を使ったバックテスト（スクリプトでの利用）
   ```
   from kabusys.data.schema import init_schema
   from kabusys.backtest.engine import run_backtest
   from datetime import date
   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
   print(result.metrics)
   conn.close()
   ```

ログレベルや動作モード:
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。
- LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のいずれか。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要ファイル一覧）

- src/kabusys/
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
  - execution/              (発注層の実装ファイル置き場、現状 __init__.py)
  - monitoring/             (監視系モジュール想定)
  - backtest/*              (バックテスト実装)

各ファイルの役割は前述の「機能一覧」を参照してください。schema.py にスキーマ定義がまとまっています。

---

## 注意点 / 運用上のヒント

- 環境変数の自動ロード
  - config.py はプロジェクトルートにある .env / .env.local を自動で読み込みます。
  - テスト時などで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants API
  - rate limit（120 req/min）とリトライ処理を実装済みですが、大量取得時は実行時間がかかります。
  - get_id_token、fetch_*、save_* の組み合わせで差分取得→保存を行ってください。

- News Collector
  - RSS の取得は SSRF/サイズ/圧縮などの安全対策を実装しています。
  - 銘柄抽出は単純な正規表現（4 桁）に基づくため、known_codes を与えて精度を高めてください。

- 冪等性
  - 多くの保存関数は ON CONFLICT を使った冪等性を備えているため、再実行に耐えます。

- 実運用
  - 本番発注（kabu ステーション等）を行うには execution レイヤーと適切な認証・安全対策（送金/注文制御）を実装してください。
  - Slack や監視ルールは別途実装／設定が必要です（config で Slack トークンを管理）。

---

## 貢献・拡張のアイデア

- execution 層（kabu API との連携）とオーダー管理の強化
- ポートフォリオ最適化（ターゲットウェイト算出）
- AI スコアの算出・登録 pipeline（ai_scores テーブル）
- 分足シミュレーションのサポート（SimulatedClock を用いた拡張）
- 品質チェックルールの追加（pipeline.quality を拡充）

---

README は以上です。必要であれば、使用例スクリプトや .env.example の雛形、CLI 追加（ETL 実行等）のサンプルを追記します。どの部分を優先して整備したいか教えてください。