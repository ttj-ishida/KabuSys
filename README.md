# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ + 実行用スクリプト群）

この README はソースツリー（src/kabusys）を基に作成した概要・セットアップ・使い方ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するシステムで、主に以下の機能群を含みます。

- 発注 / ExecutionEngine（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk モニタ）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み・ポジションサイズ計算・セクター制約）
- リサーチ（ファクター計算・特徴量探索）
- AI 連携（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（環境設定ウィザード、設定検証、検証レポート等）
- 永続化：DuckDB（分析用）・SQLite（監視 / ペーパートレード用）

設計上の主な特徴：
- 本番 DB とペーパートレード DB を分離（ペーパーモード時は data/paper_trading.db を使用）
- 環境変数 / .env ファイルベースで設定管理（config.py）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとマクロセンチメントの評価（API キー必須）
- モジュールは可能な限り副作用を避け、ユニットテストしやすい純粋関数で構成

---

## 主な機能一覧

- Execution
  - 実際のブローカー／モックブローカー（paper_trading）による発注処理（run_execution.py）
  - RiskManager / Reconciler / OrderManager を組み合わせた実行フロー
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視（run_monitoring.py）
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 各モニタを束ねて通知・Kill Switch トリガを実行
- AI
  - news_nlp: ニュースの銘柄別センチメントを LLM で算出し ai_scores に保存
  - regime_detector: ETF（1321）の MA200 とマクロセンチメントを合成して市場レジーム判定
- Portfolio
  - 候補選定、等金額/スコア加重、リスクベース配分、セクター上限、レジーム乗数
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ツール
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順（開発用ローカル）

注意: プロジェクトに requirements.txt がない場合は、以下の主要パッケージをインストールしてください。

推奨 Python バージョン: 3.10+

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # bash / zsh (Linux/macOS)
   .venv\Scripts\activate     # PowerShell/Windows
   ```

3. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb psutil openai
   # 開発時に以下があると便利
   pip install pyyaml
   ```
   （実際の requirements はプロジェクトに合わせて調整してください。）

4. .env の作成
   - 対話式ウィザードで作成するのが簡単です（後述）。
   - 例: `python -m kabusys.config_setup`

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を fail として扱いたい場合（--strict）
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（主なもの）

以下は主要な環境変数とデフォルト値の代表です（すべて .env で設定可能）。

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DB / ファイル:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (monitoring 用, default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading の専用 SQLite, default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
- Paper trading:
  - PAPER_FILL_MODE (instant | partial | never | reject) — default: instant
- OpenAI:
  - OPENAI_API_KEY
- ログ:
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- Monitoring:
  - MONITOR_POLL_INTERVAL（秒。run_monitoring で使用。デフォルト 60）

詳しくは src/kabusys/config.py のプロパティコメントを参照してください。

---

## 使い方（主要コマンド）

※ 各コマンドはプロジェクトルート（pyproject.toml や .git が存在する場所）で実行してください。

1. 環境変数ウィザード（.env 作成）
   ```
   python -m kabusys.config_setup
   ```

2. 設定検証
   ```
   python -m kabusys.validate_config
   ```

3. 実行エンジン起動（ExecutionEngine）
   - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替
   - 例：ペーパートレードで起動
     ```
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
   - 実行中は data/execution.pid に PID が書かれます。
   - 途中で停止させたい場合は後述の停止方法を参照。

4. 監視ループ起動（SystemMonitor のポーリング）
   ```
   python -m kabusys.run_monitoring
   ```
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能:
     ```
     export MONITOR_POLL_INTERVAL=30
     python -m kabusys.run_monitoring
     ```

5. Paper Trading 検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB を指定する場合:
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

6. AI スコア / レジーム判定（プログラムから呼び出す）
   - news_nlp.score_news や regime_detector.score_regime は DuckDB 接続を渡して呼び出します。
   - 例（概念）:
     ```py
     import duckdb
     from datetime import date
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     n_written = score_news(conn, date(2026,4,1), api_key="sk-...")
     ```

---

## 停止方法（Graceful stop / Kill Switch）

- 手動で監視 / 実行プロセスを止める（run_execution / run_monitoring は stop flag を監視）:
  - data/stop_requested.flag を作成すると、run_execution や run_monitoring のループは検知して終了します。
    ```
    mkdir -p data
    echo "" > data/stop_requested.flag
    ```
- モニタ側から自動停止（Kill Switch）
  - MonitoringEngine 内の KillSwitch が条件を満たすと data/kill.flag に理由を書き込みます。
  - ExecutionEngine 実装側は kill.flag を読み取り停止するようになっています（Settings.kill_flag_path を使用）。
- 強制的に kill する場合は OS のプロセス殺し（kill/Task Manager）を使用してください。

---

## 開発・デバッグのヒント

- logging はモジュール内で基本設定されているので、環境変数 LOG_LEVEL を変更してログ出力を制御します。
- validate_config は .env と config/*.yaml の存在や基本的な整合性をチェックします。PyYAML がない場合は YAML 検証をスキップします。
- MonitoringDB（SQLite） の初期化 / マイグレーションは init_monitoring_db() で行われます。既存 DB が古いスキーマでも互換性のための ALTER が実行されます。

---

## ディレクトリ構成（要約）

（ソースルート: src/kabusys）

- __init__.py
- config.py                     — 環境変数 / 設定管理
- config_setup.py               — 対話式 .env ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

- execution/                    — 発注関連（ExecutionEngine, OrderManager, BrokerFactory, Reconciler, RiskManager, OrderRepository 等）
- monitoring/
  - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py            — （アラート通知の抽象層）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py          — レジーム判定（MA + マクロセンチメント）
- monitoring/
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
- data/                         — 実行時に生成される DB / PID / flag 等（例: monitoring.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag）

（各ディレクトリ内にさらに多くの実装ファイルがあります。詳細はソースを確認してください。）

---

## よくある質問 / 注意点

- ペーパートレードと本番で DB を混同しないでください。KABUSYS_ENV=paper_trading のときは paper_sqlite_path が使用されます。
- monitoring のログや kill.flag により本番 ExecutionEngine が停止される場合があります。KABUSYS_ENV=live のときは設定（LINE 通知など）を十分に確認してください。
- OpenAI API を利用する機能は外部サービスに依存します。API キーの管理、エラーハンドリング、コストに注意してください。
- process priority の設定は psutil の権限に依存します（権限不足で設定に失敗しても警告のみで継続します）。

---

必要であれば、README にサンプル .env テンプレートや各サブパッケージ（execution, monitoring, ai 等）の API 呼び出し例を追加できます。どのセクションをより詳細化したいか教えてください。