# KabuSys

日本株向け自動売買プラットフォームの一部を実装したコードベースの README です。ここでは本リポジトリの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

> 注意: 本 README はソース内のドキュメント文字列（docstring）や設定モジュールを元に作成しています。実行には外部パッケージや環境変数の設定が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を含むモジュール群です。

- 注文発行・状態管理・リコンシリエーション（Execution）
- モニタリング（プロセス監視・注文滞留検出・リスク監視・アラート）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ（ファクター計算・特徴量探索・IC計測など）
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI API を利用）
- ツール類（Paper Trading 検証レポート生成、Streamlit ダッシュボードなど）
- 設定管理（.env 自動ロード、Settings ラッパー）

設計方針として、DB（SQLite / DuckDB）や外部 API 呼び出しを明示的に扱い、ルックアヘッドバイアスを避ける実装／フェイルセーフな挙動を重視しています。

---

## 主な機能一覧

- Execution
  - Broker クライアントの抽象化（実ブローカー / Mock for paper trading）
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - Reconciler による起動時の自動再同期（OrderSent の突合、ポジション差分検知）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 注文滞留（stale order）や約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch: 条件により ExecutionEngine 停止フラグ（data/kill.flag）を書き込む
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit 監視ダッシュボード
- Portfolio
  - 候補選定（スコア順選抜）
  - 等金額／スコア加重の重み計算
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap、スケールダウン）
- Research
  - ファクター計算（Momentum, Value, Volatility, Liquidity）
  - 将来リターン計算、IC (Spearman) 計算、統計サマリー
- AI
  - news_nlp: OpenAI を用いた銘柄単位のニュースセンチメント評価 → ai_scores テーブルへ書込
  - regime_detector: ETF MA とマクロニュースの LLM 評価を合成して日次レジーム判定 → market_regime テーブルへ書込
- Tools
  - paper_verification_report: Paper Trading 用 SQLite を解析して検証レポートを出力
- config
  - Settings クラス: 環境変数ラッパー（.env / .env.local の自動ロードをサポート）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）基準

---

## セットアップ手順（開発環境）

以下は開発 / 実行のための最低限手順です。実行環境やパッケージバージョンはプロジェクト要件に合わせて調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（概ね以下が必要）
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   - 実際の requirements.txt がある場合はそれを使用してください。

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を用意すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 代表的な環境変数（例）:
     - KABUSYS_ENV = development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - PAPER_FILL_MODE = instant | partial | never | reject (paper_trading 時)
     - PAPER_TRADING_SQLITE_PATH（paper DB）
     - SQLITE_PATH（monitoring DB, デフォルト: data/monitoring.db）
     - DUCKDB_PATH（価格データ等, デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH
     - LOG_LEVEL
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）
     - MONITOR_POLL_INTERVAL（監視ループの秒 interval、デフォルト 60）
   - 例: .env
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. data ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

6. 初期 DB 作成
   - 多くの起動スクリプトが自動的に monitoring DB のテーブルを作成します（init_monitoring_db を呼ぶ）。
   - DuckDB / prices データは別途用意する必要があります（リサーチ機能等で参照されます）。

---

## 使い方（主要スクリプト / コマンド例）

- ExecutionEngine を起動（本番 / paper_trading の設定は KABUSYS_ENV に依存）
  ```
  # 実行例 (モジュール実行)
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
  - 起動時にプロセス優先度を上げ、必要な DB 初期化を行います。

- Monitoring のポーリングループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path を使用する（ソースの仕様）。
  - 起動時にプロセス優先度を設定します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db PATH` で別パスを指定可能。
  - 出力は標準出力にレポート形式で表示されます。

- Streamlit 監視ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 既存の monitoring.db を read-only モードで開き、ダッシュボードを表示します。
  - MonitoringEngine がデータを書き込んでいることが前提です。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必須です。関数はプログラムから呼び出せます:
    - kabusys.ai.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)
  - API レスポンスのリトライ・バリデーションやスコアクリップ等の安全策を実装しています。

---

## 実運用に関する注意点

- process priority / CPU affinity
  - 起動スクリプトは set_process_priority("high") を試みます。psutil の権限により失敗する可能性があります（警告ログ）。
- kill.flag（ExecutionEngine 停止フラグ）
  - KillSwitch はファイル (デフォルト data/kill.flag) を作成して ExecutionEngine に停止指示を行います。
  - ExecutionEngine 起動時にフラグをクリアする挙動は設定で制御できます（Settings.kill_flag_clear_on_start）。
- データ鮮度チェック
  - SystemMonitor は DuckDB の prices_daily の最終日付を参照し、最新日との差が _FRESHNESS_DAYS（デフォルト 3日）以内かを判定します。
- Paper Trading と本番 DB の分離
  - run_execution は KABUSYS_ENV が paper_trading の場合、paper 用 SQLite を使用して本番 DB とは分離します（安全設計）。

---

## 主要なディレクトリ構成

以下はソース内の主要モジュールと概要です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み込み・自動 .env ロード・各種パス／フラグのラッパー
  - run_execution.py
    - ExecutionEngine 起動エントリポイント（paper_trading 時の挙動分離）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py
      - monitoring 用 SQLite テーブル作成／CRUD ユーティリティ（MonitoringDB）
    - system_monitor.py
      - CPU/MEM/DISK・プロセス・データ鮮度チェック
    - trade_monitor.py
      - 注文滞留・約定異常価格の検出
    - risk_monitor.py
      - ドローダウン／ポジション上限チェック
    - kill_switch.py
      - kill.flag の作成・判定
    - alert_manager.py
      - LINE Push による通知（クールダウン）
    - monitoring_engine.py
      - 各モニターを束ねてポーリングする高レベルエンジン
    - streamlit_dashboard.py
      - Streamlit ベースの軽量ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (参照あり)
    - broker_factory, broker_api, execution_engine, risk_manager, order_record など（注文処理／実行に関するコンポーネント）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算（等金額 / スコア重み）
    - position_sizing.py
      - 発注株数決定、単元丸め、aggregate cap のスケーリング
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - research/
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算（DuckDB 接続受け取り）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py
      - raw_news を OpenAI に投げて銘柄単位のセンチメントを ai_scores に書き込む
    - regime_detector.py
      - MA とマクロニュースを合成して market_regime を算出／永続化
  - utils/
    - process_priority.py
      - プラットフォーム差分を吸収した優先度 / CPU affinity 設定ユーティリティ

注: 上記は主要ファイルのみ抜粋しています。実際のリポジトリにはさらに補助モジュール（data パイプライン、execution 内の他クラス等）が含まれます。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API を使う機能でエラーが出る
  - `OPENAI_API_KEY` が設定されていること、ネットワーク接続があることを確認してください。API 呼び出しはリトライロジックをもっていますが、キー未設定は例外になります。
- Monitoring が期待どおりの DB に書き込まれない
  - run_monitoring は Settings.sqlite_path（本番用）を使います。paper_trading 用 DB は run_execution のみが分離して使います。

---

必要に応じて README に追記します。特定のコマンド例や各モジュールの API ドキュメント（関数シグネチャや戻り値）を README に追加したい場合は、その旨を教えてください。