KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株自動売買システムのコードベースです。本リポジトリには以下の主要機能が含まれます。
- ExecutionEngine（発注・リスク管理・再整合）
- Monitoring（システム状態・注文状況・リスクの常時監視、Kill Switch）
- Portfolio Construction（銘柄選定・重み計算・ポジションサイズ決定）
- Research（ファクター計算・特徴量探索）
- AI 補助モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

主な機能一覧
-------------
- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式ウィザードで .env 作成（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行（Execution）
  - 実取引 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカー抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）
  - 注文管理（OrderManager / OrderRepository）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス状態、データ鮮度
  - TradeMonitor: 注文滞留／約定異常などの検出（trade_logs）
  - RiskMonitor: ドローダウン／ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件満たしたら data/kill.flag を書き込み Execution を停止
  - MonitoringEngine: 各モニタをまとめて定期実行、AlertManager 経由で通知可能
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等分配・スコア加重配分
  - セクターキャップ、レジーム乗数
  - ポジション株数決定（lot（単元）丸め、aggregate cap）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、統計サマリ
  - DuckDB を使った高速集計
- AI（OpenAI）
  - news_nlp.score_news: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector.score_regime: MA とマクロセンチメントを合成して市場レジーム判定
- 運用ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）

必須 / 推奨依存パッケージ
------------------------
（requirements.txt がない場合の参考）
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml を検証する場合）
- その他: sqlite3（標準）、typing 等標準ライブラリ

セットアップ手順
----------------
1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成する
     - .env.example を参照して必要な環境変数を設定してください

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

5. DB・ログディレクトリ
   - デフォルトでは以下の場所を使用します。必要に応じて .env で変更してください。
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - ペーパートレード SQLite: data/paper_trading.db
     - ログ: logs/
   - 監視/実行スクリプトは起動時に必要なテーブルを作成します（init_monitoring_db が冪等で実装されています）。

主な環境変数（代表）
-------------------
重要な環境変数とデフォルト値・説明（すべて .env に設定できます）:

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に書き込み（本番 DB と完全分離）
    - live: 本番（発注が行われます）

- DB / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - LOG_DIR (default: logs/)

- ログ / 動作
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) default: INFO
  - KILL_FLAG_CLEAR_ON_START (0/1) default: 0
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- Paper Trading / AI
  - PAPER_FILL_MODE (instant|partial|never|reject) default: instant
  - OPENAI_API_KEY: OpenAI を使う機能で必要（news_nlp / regime_detector）

使い方（起動コマンド例）
-----------------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は mock ブローカーを使い paper_trading 用 DB に記録します
    - 停止は data/stop_requested.flag を作成することで行えます（または Execution 側の kill.flag を利用）

- Monitoring 起動（デーモン的にポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 停止は data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する例:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使います

停止フラグ / PID
-----------------
- 停止フラグ: data/stop_requested.flag（run_execution / run_monitoring が監視）
- Kill Switch（Execution を強制停止させる条件が満たされた場合に書き込まれる）: data/kill.flag
- PID ファイル: data/execution.pid（ExecutionEngine が使用）

ディレクトリ構成（主要ファイル）
------------------------------
リポジトリの主要モジュール構成（src/kabusys 以下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル初期化・読み書きユーティリティ）
    - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度・プロセスチェック
    - trade_monitor.py       — （注文ログ監視。コード中に参照あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 操作
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （アラート送信管理。コード中に参照あり）
  - execution/                — Execution 系（Engine, OrderManager, Broker 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記に加えて data/ や logs/ などのランタイム生成ディレクトリが想定されます）

注意事項 / 運用上のポイント
---------------------------
- 本番（KABUSYS_ENV=live）では .env の値を慎重に確認してください。validate_config は live 時に追加チェック（LINE 通知設定など）を行います。
- .env は絶対にリポジトリにコミットしないでください（config_setup もその旨を表示します）。
- run_execution / run_monitoring は起動時にプロセス優先度を "high" にしようとしますが、権限や OS によって失敗する場合があり、その場合は警告が出て処理は継続します。
- AI（OpenAI）を利用する機能はネットワークに依存します。API 失敗時はフォールバックする（0 値扱い・スキップ）実装です。
- DuckDB / SQLite のファイルパスは .env で変更可能です。特に Paper Trading は本番 DB と分離することを推奨します。

開発・拡張
-----------
- モジュールの多くは純粋関数（副作用が少ない）で実装されており、ユニットテストが書きやすく設計されています。
- OpenAI 呼び出し部分はテスト時に差し替え可能（内部呼び出し関数を patch してモック化）
- monitoring_db.init_monitoring_db は冪等にテーブル・カラムを作成／マイグレーションします。既存 DB に対しても安全に実行できます。

問い合わせ / 貢献
------------------
バグ報告や改善提案、PR は歓迎します。まずは issue を立ててください。README に書かれていない運用手順や追加の設定が必要な場合は issue で共有してください。

以上がこのコードベースの概要とセットアップ・運用手順です。必要であれば各コマンドのより詳細な使い方（引数一覧や環境変数の全列挙、サンプル .env）を追加で作成します。どの部分を詳しく書いてほしいか教えてください。