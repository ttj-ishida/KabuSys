# KabuSys

日本株自動売買システムのコアライブラリ群（監視・実行エンジン・ポートフォリオ構築・リサーチ・AI補助機能など）。  
この README はリポジトリ内の主要スクリプト／モジュールを利用するための概要、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

注意：本 README はソースコード（src/kabusys 以下）を参照して作成しています。実行には Python 環境と外部ライブラリ（duckdb, psutil, requests, openai, streamlit など）が必要です。

## プロジェクト概要
- システム監視（SystemMonitor / MonitoringEngine）
  - CPU・メモリ・ディスク・プロセス生存・株価データ鮮度等を定期ポーリングし SQLite に記録。
  - アラートは LINE Messaging API 経由で送信可能。
  - Kill Switch により条件に応じて ExecutionEngine 停止のためのフラグを書き込む。
- 実行エンジン（ExecutionEngine）
  - ブローカークライアントを通じて注文管理、リスク管理、リコンシリエーションを行う。
  - `paper_trading` 環境ではモックブローカーを使用し、本番 DB と分離された専用 SQLite（data/paper_trading.db）に記録。
- ポートフォリオ構築（選定・重み付け・ポジション算出・リスク調整）
  - 等重・スコア重み・リスクベースの単純関数群を提供。
- リサーチ（ファクター計算・特徴量探索）
  - DuckDB を用いたファクター計算（Momentum / Value / Volatility）や IC・将来リターン計算。
- AI 補助（ニュース NLP / レジーム検出）
  - OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメントスコア付与、マクロセンチメント合成によるレジーム判定。
- ツール
  - Paper Trading の検証レポート生成スクリプト等。
- ダッシュボード
  - Streamlit ベースの監視ダッシュボード（read-only で monitoring.db を参照）。

## 主な機能一覧
- SystemMonitor: OSリソース・プロセス生存・データ鮮度の定期検査、ログ永続化。
- TradeMonitor: 注文滞留（stale orders）・約定価格異常の検出とリスクログ記録。
- RiskMonitor: ドローダウン・ポジション上限の監視とアラート／Kill Switch トリガー。
- MonitoringEngine: 各モニタを束ねて周期的に実行、LINE 通知連携。
- ExecutionEngine（および OrderManager / Reconciler）: 注文ライフサイクル管理、起動時の自動リコンシリエーション。
- Portfolio モジュール: 候補選定・重み計算・株数算出・セクター制限・レジーム乗数。
- Research モジュール: DuckDB を使ったファクター計算、IC 等の統計分析。
- AI モジュール: ニュースを LLM でスコア化（ai_scores に書き込み）、市場レジーム判定。
- Tools: Paper Trading 検証レポート生成（期間指定可）。
- Streamlit ダッシュボード: 監視情報の可視化（monitoring.db を read-only で参照）。

## 必要条件（概略）
- Python 3.9+（ソースは型ヒントで新しい構文を使用）
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
（実際はプロジェクトの requirements.txt を用意している場合はそれを利用してください。）

例:
```
pip install duckdb psutil requests openai streamlit
```

## 環境変数（主要なもの）
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）。
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）。
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）。
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）。
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用アクセストークン（任意。設定なければ送信はスキップ）。
- LINE_USER_ID: LINE Push 先ユーザー ID。
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）。
- SQLITE_PATH: 監視用 SQLite（monitoring） DB（デフォルト: data/monitoring.db）。
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）。
- PAPER_FILL_MODE: Paper Trading のフィルルール（instant / partial / never / reject。デフォルト: instant）。
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒。デフォルト: 60）。不正値はデフォルトにフォールバック。
- PID_FILE_PATH, KILL_FLAG_PATH など（監視・停止フラグのパス指定）。
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。

設定ファイルとして .env / .env.local を使用可能（自動ロードされます）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

## セットアップ手順（ローカル開発用）
1. リポジトリをクローンし、作業ディレクトリをルートにする（pyproject.toml または .git がある場所）。
2. Python 仮想環境を作成・有効化。
3. 依存パッケージをインストール。
   - 例: pip install -r requirements.txt
   - もし requirements.txt が無い場合は上記の主要パッケージを個別にインストール。
4. data ディレクトリを作成（DB ファイル・フラグファイルの配置先）。
   ```
   mkdir -p data
   ```
5. .env を作成（.env.example を参考に必要な環境変数を設定）。最低限以下は設定してください:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY（AI 機能を使う場合）
   - 必要に応じて LINE 関連トークン
6. 初回実行時はスクリプトが必要な DB テーブルを自動作成します（monitoring の init_monitoring_db を利用）。

## 使い方（主要コマンド／スクリプト）
以下はリポジトリルートから実行する想定です。

- 監視ループの起動（SystemMonitor 単独）
  ```
  # デフォルト: MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を変更:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - run_monitoring は常に本番（settings.sqlite_path）を監視 DB として使用します。

- 実行エンジンの起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って PAPER_TRADING_SQLITE_PATH に記録します。
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 停止フラグ（外部からの停止）:
    - 停止要求: data/stop_requested.flag を作成するとループが検知して安全に終了します。
    - KillSwitch は data/kill.flag を書き込みます（KillSwitch の評価により自動的に書かれます）。

- Streamlit 監視ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - monitoring.db を read-only で開いてダッシュボード表示を行います。

- Paper Trading 検証レポート生成（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。別 DB を使う場合は --db オプションか環境変数 PAPER_TRADING_SQLITE_PATH を指定。

- AI 関連（コードからの利用例）
  - ニュースセンチメント（ai_scores テーブルへ書き込み）:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="あなたのAPIキー")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="...")
    ```

- ライブラリとしての利用（ポートフォリオ・リサーチ関数）
  - 例: ポートフォリオ構築関数の呼び出し
    ```python
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_score_weights(candidates)
    sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)
    ```

## 停止・制御方法（フラグファイル）
- data/stop_requested.flag
  - run_monitoring.py や run_execution.py のメインループはこのファイルの存在をチェックして安全に終了します。外部から停止させたいときはこのファイルを作成します（テキストの中身は任意）。
- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込まれるフラグ。イベントの理由がファイルに書かれ、別プロセス（ExecutionEngine 側のチェック処理）で参照されます。
- data/execution.pid
  - 実行中の ExecutionEngine の PID を保持。SystemMonitor は PID を参照して実プロセスの生存を確認します。

（注意）フラグ／PID の挙動は環境に依存するため、運用時はスクリプトのログとファイルの扱いを確認してください。

## 開発時メモ
- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動で読み込みます。OS 環境変数を保護するため .env.local は override=True ですが OS 側にある変数は上書きされません。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DB マイグレーション（簡易）
  - monitoring_db.init_monitoring_db は必要なテーブルとインデックスを冪等的に作成します。既存テーブルに列が足りない場合は簡易的な ALTER を試みます（例: trade_logs.latency_ms, dashboard.peak_value）。
- テストのしやすさ
  - 多くの OpenAI 呼び出し・外部 API 呼び出し箇所はモックしやすい設計（専用の内部 _call_openai_api を patch 可能）になっています。

## ディレクトリ構成（要約）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込みロジック
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース NLP スコアリング
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — システム監視
    - trade_monitor.py — 注文監視
    - risk_monitor.py — ドローダウン等の監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各監視の統合エンジン
    - alert_manager.py — LINE 通知
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 注文管理・リコンシリエーション等
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・統計解析
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (ランタイムで生成されることを想定)
    - monitoring.db（SQLITE_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - kabusys.duckdb（DUCKDB_PATH）
    - stop_requested.flag, kill.flag, execution.pid など

（上記は主なファイルを抜粋した要約です。詳細は src/kabusys 以下のソースを参照してください。）

## よくある質問 / トラブルシューティング
- Q: monitoring.db が見つからない／開けない
  - A: MonitoringEngine を先に起動して DB を初期化してください。Streamlit は read-only で開くため権限やファイルパスに注意。
- Q: OpenAI API 呼び出しで失敗したら？
  - A: AI モジュールは 429/タイムアウト/5xx を再試行するロジックを持ち、失敗した場合はフェイルセーフ（0.0 など）で継続します。ただし API キーが未設定の場合は明示的にエラーになります。
- Q: Paper Trading と本番 DB を分離したい
  - A: KABUSYS_ENV=paper_trading に設定すると paper_sqlite_path を使用します（デフォルト: data/paper_trading.db）。この環境では MockBrokerClient が使用される想定です。

---

この README はコードベースに基づく簡易ガイドです。詳細な利用方法や設計仕様（PortfolioConstruction.md, StrategyModel.md など参照）は別ドキュメントを参照してください。必要があれば README の拡張（運用手順、監視ダッシュボードのスクリーンショット、CI/デプロイ方法など）も作成します。