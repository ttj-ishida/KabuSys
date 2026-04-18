# KabuSys

日本株向け自動売買システムの一部モジュール群を含むリポジトリです。  
このREADME はコードベースから抽出した機能や使い方、セットアップ手順を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数 / .env の説明
- ログ・DBの既定値
- 停止・Kill フラグの扱い
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - 本番 / ペーパートレーディングを切り替え可能
- システム監視（Monitoring）起動スクリプト（run_monitoring）
  - CPU / メモリ / ディスク / プロセス状態 / データ鮮度の監視
- 監視 DB 層（SQLite）および監視用レポジトリ
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定等）
- リサーチ用ファクター計算（DuckDB を利用）
- AI 関連モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- ツール：Paper Trading 検証レポート生成スクリプト

設計方針の一部:
- DB は DuckDB（分析用）と SQLite（監視 / 発注ログ）を併用
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV による）
- LLM 呼び出しは OpenAI（gpt-4o-mini）を利用する想定。API 呼び出しは失敗耐性を考慮

---

## 機能一覧

主な機能（抜粋）:

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い data/paper_trading.db に記録
  - プロセス優先度の設定、PID ファイル管理、停止フラグ検出
- run_monitoring.py
  - SystemMonitor のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔指定）
  - 監視結果を SQLite に保存し、必要ならリスクログ等を記録
- config_setup.py
  - 対話式ウィザードで .env を作成 / 更新
- validate_config.py
  - .env と config/*.yaml（存在する場合）の基本検証 CLI（--strictあり）
- tools/paper_verification_report.py
  - ペーパートレード DB を読み取り、稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定
- monitoring モジュール
  - MonitoringDB（永続化レイヤ）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / AlertManager（アラート処理）
- portfolio モジュール
  - 候補選定、重み計算、セクター上限適用、ポジションサイジング
- research モジュール
  - ファクター計算（モメンタム、バリュー、ボラティリティなど）、IC 計算、統計集計
- ai モジュール
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector: ETF の MA と LLM のマクロセンチメントを合成して市場レジーム判定

---

## セットアップ手順

前提:
- Python 3.10+（ソースは型注釈: Path | None 等を使用）
- システムに DuckDB が利用可能であること（Python パッケージ duckdb）
- OpenAI API を使う機能は OPENAI_API_KEY が必要
- psutil が必要（プロセス優先度 / CPU 情報等）

推奨手順（UNIX 系）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - optional: pip install pyyaml （validate_config の YAML 検証に必要）

   （プロジェクトに requirements.txt があればそれを使用してください）

3. パッケージをローカルインストール（任意）
   - pip install -e .   # setup があれば使う（pyproject.toml/セットアップファイルがある場合）

4. 初期設定
   - python -m kabusys.config_setup
     - 対話形式で .env を生成または更新します（.env は絶対にリポジトリにコミットしないでください）
   - python -m kabusys.validate_config
     - 設定検証。問題があれば修正してください。

---

## 使い方

### 重要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

重要: .env は config_setup で作成できます。

### 設定の検証
- python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1)

### 実行エンジン (Execution)
- python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に試行設定します（権限により失敗する場合あり）
  - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite にログを残します（本番 DB と分離）
  - 停止条件:
    - data/stop_requested.flag が存在すると起動せず/停止します
    - KillSwitch（監視側）が data/kill.flag を書くと ExecutionEngine は停止されます
  - PID ファイル: data/execution.pid（既定、Settings でオーバーライド可）

### 監視（Monitoring）
- python -m kabusys.run_monitoring
  - SystemMonitor のポーリングループを開始します（デフォルト 60 秒間隔、MONITOR_POLL_INTERVAL で上書き可能）
  - 監視は Settings.env に関係なく本番 sqlite_path を使用して監視 DB に書き込みます
  - 監視ループを終了するには data/stop_requested.flag を作成するか、Ctrl+C

MONITOR_POLL_INTERVAL の例:
- export MONITOR_POLL_INTERVAL=30
- python -m kabusys.run_monitoring

### Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示することも可（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

### AI 関連
- kabusys.ai.score_news（関数）
  - raw_news / news_symbols / ai_scores テーブルを操作します。OPENAI_API_KEY の設定が必要
- kabusys.ai.regime_detector.score_regime（関数）
  - DuckDB を渡して呼び出し、market_regime テーブルに書き込みます
- これらは CLI エントリポイントは同梱されていないため、スクリプトやスケジューラから関数を呼ぶ / ラッパーを用意してください。

---

## ログ・DB の既定値

- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- ログディレクトリ: logs/
  - 各アプリケーション（monitoring, execution 等）ごとに logs/<app_name>.log を日次ローテート（30世代保持）
  - ログレベルは LOG_LEVEL 環境変数、または setup_logging の引数で変更可能

ログ設定は kabusys.utils.logging_setup.setup_logging を通して統一的に行われます。

---

## 停止・Kill フラグ

- 停止要求（スクリプトの優雅な停止）
  - data/stop_requested.flag
    - run_monitoring / run_execution はこのファイルの存在を見てループを終了またはエンジンを停止します
- Kill Switch（監視による強制停止指令）
  - data/kill.flag
    - KillSwitch 評価により書き込まれるファイルで、ExecutionEngine がこのフラグを検出するとセーフに停止する想定
    - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動でこのフラグをクリアします（注意: 本番では推奨しません）

ファイルは手動で作成／削除できます（存在チェック、上書きは KillSwitch 側で冪等に行われます）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主な構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings ラッパー
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログセットアップユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — 実行時に使用される SQLite / フラグ / PID を格納する想定のディレクトリ（デフォルト）

注: 実際のファイル一覧はリポジトリのソースを参照してください。上記は主要モジュールの抜粋です。

---

## 追加メモ・運用上の注意

- 本番運用時は必ず KABUSYS_ENV=live の環境で各設定（LINE 通知等）を確認してください。validate_config は live 時に追加の警告を出します。
- .env は秘匿情報を含むため Git 等にコミットしないでください。config_setup.py による自動生成を推奨します。
- OpenAI への API 呼び出しにはレート制限やネットワークエラーがあります。ai モジュールはリトライ/フォールバックを備えていますが、API キーやコスト管理に注意してください。
- Logging のファイル出力に失敗した場合はコンソール出力のみで継続するよう設計されています（ディレクトリ作成失敗など）。
- process_priority の設定は OS / 権限によって失敗する可能性があります。失敗時は警告ログが出てスキップされます。

---

この README はコードベース（src/kabusys 以下）を元に作成しています。  
詳細や追加の運用ドキュメントはリポジトリ内のドキュメントファイル（もしあれば）や各モジュールの docstring を参照してください。質問や README に追記してほしい項目があれば教えてください。