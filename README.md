# KabuSys README

以下はこのリポジトリ（KabuSys）の概要と使い方をまとめた README です。日本株の自動売買を想定したモジュール群（Execution エンジン、Monitoring、ポートフォリオ構築、リサーチ、AI ユーティリティ等）を含みます。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な目的は以下のとおりです。

- 発注エンジン（ExecutionEngine）の実行と管理（実口座 / ペーパートレード対応）
- システム稼働・注文・リスクの監視およびアラート / Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ用ファクター計算・特徴量探索
- ニュースの NLP を用いた銘柄センチメント評価 / レジーム判定（OpenAI 経由）
- ペーパートレード検証レポート生成などのツール群
- 設定ウィザード・設定検証 CLI

設計方針として、DB（SQLite / DuckDB）を使った永続化、LLM 呼び出しは外部 API（OpenAI）経由、監視はファイルフラグ（kill.flag / stop_requested.flag）や PID ファイルで制御する仕組みを採用しています。

---

## 機能一覧（ハイライト）
- Execution
  - 実取引（live）/ ペーパートレード（paper_trading）対応
  - ブローカークライアント抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）、オーダーマネージャ、照合（Reconciler）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウン監視
  - KillSwitch：条件達成で data/kill.flag を書き込み Execution を停止
  - MonitoringEngine：複数モニタの定期実行・アラート連携
- Portfolio
  - 候補選定（スコア順）、等比率/スコア比率での重み付け
  - ポジションサイズ計算（risk_based / equal / score）、単元株丸め、aggregate cap
  - セクター集中制限、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメントのバッチ評価（ai_scores）
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を組み合わせた市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB を元に PASS/FAIL 判定の検証レポートを生成
- 設定関連
  - config_setup: .env の対話式生成・更新ウィザード
  - validate_config: 起動前チェック（必須環境変数・config/*.yaml 等）

---

## セットアップ手順（ローカル）
以下は最小限のセットアップ手順例です。プロジェクトの配布方法に応じて調整してください。

1. 前提
   - Python 3.9+ を推奨（コードは型ヒントに Python 3.9+ 機能を使用）。
   - OS により psutil の一部機能で管理者権限が必要になる場合があります。
   - DuckDB, psutil, openai などの外部依存があります。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai
   - （YAML 検証を使う場合）pip install PyYAML
   - 追加でテスト・開発ツールがあれば適宜インストールしてください。

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. 環境変数設定
   - ルートに `.env` を作成するか、環境変数を直接設定します。対話式で作成するには:
     - python -m kabusys.config_setup
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他（省略時はデフォルトが使われる）:
     - KABUSYS_ENV（development / paper_trading / live。デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - LOG_LEVEL（デフォルト INFO）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading 時の fill 振る舞い）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

6. データディレクトリ
   - デフォルトでは data/ 配下のファイル（SQLite / DuckDB / PID / フラグ）を使用します。権限に注意してください。

---

## 使い方（よく使うコマンド）
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution Engine の起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag があれば起動を行わず終了
    - 停止は data/stop_requested.flag を作成する、または Kill Switch による data/kill.flag で通知されます
    - 実行時に PID ファイル（data/execution.pid）を作成します

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は設定にかかわらず本番 sqlite_path を使って監視ログを書きます（監視 DB 用）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI 関連（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None) などの関数 API を利用（スクリプトとしては直接 CLI 実装は無し）
  - OPENAI_API_KEY を設定すること

- 停止制御
  - 実行プロセスを優雅に停止させたい場合はリポジトリルートの data/stop_requested.flag を作成します（run_* スクリプトはこれを監視して終了します）。
  - KillSwitch が作動すると data/kill.flag が書かれ、ExecutionEngine 側で検出して停止します。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリア（本番では 0 を推奨）。

---

## 主要な環境変数（抜粋とデフォルト）
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- LOG_LEVEL — INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視・停止関連

詳細は `src/kabusys/config.py` を参照してください。

---

## ログ
- デフォルトは `logs/` ディレクトリを使い、アプリ名ごとに daily ローテートでログを出力します（例: logs/execution.log, logs/monitoring.log）。
- ログ設定は `kabusys.utils.logging_setup.setup_logging()` により統一的に初期化されます。
- 環境変数 LOG_DIR でログ出力ディレクトリを変更可能。作成権限がない場合はコンソール出力のみになります。

---

## ディレクトリ構成（主要ファイルの概要）
以下は src/kabusys 以下の主要なモジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理（自動 .env ロード / 検証ユーティリティ）
  - config_setup.py — .env 対話式ウィザード（CLI）
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（PID / stop flag 処理）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を生成するロジック
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB のスキーマ & 永続化処理
    - system_monitor.py — システム状態・データ鮮度チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （注文系監視、コードベースに存在）
    - monitoring_engine.py — 監視コンポーネントの束ね
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — （アラート通知ハンドリング）
  - execution/
    - execution_engine.py — 実際の ExecutionEngine 実装（セッション管理）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行に関する依存コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算（単元丸め等）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に使用される想定のディレクトリ)
    - monitoring.db（デフォルト SQLite）
    - paper_trading.db（paper_trading 用 DB）
    - kabusys.duckdb（DuckDB）
    - execution.pid, stop_requested.flag, kill.flag などの制御ファイル

（上は主要モジュールの抜粋です。他にも補助的なモジュールが含まれます。実装の詳細は各モジュールの docstring を参照してください。）

---

## 運用上の注意・トラブルシューティング
- KABUSYS_ENV=live の設定は本番リスクがあるため慎重に。validate_config は live 時に追加警告を出します。
- .env は絶対にバージョン管理にコミットしないこと。
- psutil の優先度設定や CPU affinity 設定は権限により失敗する場合があります（アクセス拒否時は警告出力で継続します）。
- OpenAI API 呼び出しは課金対象・レート制限が発生します。API エラー・429 は内部で指数バックオフでリトライする実装ですが、長時間の失敗はその機能をオフにするなど運用上の対策を検討してください。
- DuckDB / SQLite のファイルは複数プロセスからの同時書き込みに注意（設計上は各用途でファイル分離されていますが、運用時にロック競合が起きない設計を確認してください）。
- run_monitoring は MONITOR_POLL_INTERVAL によって sleep 時間を決めます。値が 0 以下や数値でない場合はデフォルト 60 秒にフォールバックします。

---

## 最後に
本 README はコード中の docstring / 実装方針に基づいて作成しています。詳細な実装や API 使用方法については各モジュール（特に execution/*、monitoring/*、ai/*、research/*）の docstring を参照してください。必要であれば、本 README をベースにさらに運用マニュアルやアーキテクチャ図を作成できます。