# KabuSys

日本株向けの自動売買システム（ライブラリ＋実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポーティング・AI 補助モジュールを含む小規模な自動売買プラットフォームのコードベースです。  
主要な設計方針として「本番 DB／発注 API に直接アクセスしない研究モジュール」「ペーパートレードは本番と分離」「外部 API 呼び出しは明示的に渡す（テスト容易性）」などを採っています。

以下は本プロジェクトの概要、機能、セットアップと使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株の自動売買を行うためのエンジン群と補助ツール群を提供する。
- 主なコンポーネント:
  - ExecutionEngine（発注エンジン） — ブローカークライアントと連携して注文を管理・実行
  - Monitoring（監視） — システム稼働状態、注文滞留、約定異常、リスク（ドローダウン等）を定期チェック
  - Portfolio（ポートフォリオ構築） — 候補選定、重み付け、ポジションサイズ計算
  - Research（研究） — ファクター計算、将来リターン・IC 計算など DuckDB ベースの分析
  - AI（news_nlp / regime_detector） — OpenAI を用いたニュースセンチメント評価／市場レジーム判定
  - ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

---

## 主な機能一覧

- 環境管理・設定
  - .env 自動読み込み（プロジェクトルートを探索して .env / .env.local をロード）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config (--strict オプションで警告も FAIL 扱い)

- 実行・発注
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading は MockBrokerClient を使用して data/paper_trading.db に記録）
  - ブローカークライアントは環境に応じて抽象化（BrokerClientFactory）

- 監視
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 環境変数で間隔指定、デフォルト 60 秒）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager を組み合わせて監視と自動停止（kill.flag）を実行

- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア加重、リスクベースのポジションサイズ計算、セクター上限適用、レジーム乗数

- 研究・分析
  - DuckDB 接続を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリー）

- AI支援
  - ニュースのセンチメント評価（OpenAI を用いて ai_scores テーブルに書き込み）
  - 市場レジーム判定（ma200 とマクロセンチメントを合成して daily レジームを判定）

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL 判定

---

## セットアップ手順

前提: Python 3.10+ を想定（typing の一部表記に依存）。プロジェクトルートに移動して行ってください。

1. リポジトリをクローンし、環境を作成
   - 例（venv）:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     pip install -U pip
     ```

2. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイルの検証を行う場合、オプション）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```

3. .env の作成
   - 対話式ウィザードで作成・更新:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で .env を作り、必須キーを設定してください（下記参照）。

4. 設定検証
   - 必須環境変数や config/*.yaml の検査:
     ```
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
     ```

5. データディレクトリの準備
   - デフォルトの DB パスは .env の値に依存しますが、デフォルトでは次を使用します:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
   - 必要に応じてディレクトリを作成:
     ```
     mkdir -p data
     ```

6. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定するか、API キーを関数呼び出しに渡してください。

---

## 必須／主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用の DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- PAPER_FILL_MODE（paper_trading の挙動: instant | partial | never | reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト 60）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか。0/1、デフォルト: 0）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

.env.example のようなサンプルを参考に .env を作成してください。

自動 .env ロード: プロジェクトルートに .env/.env.local があれば、モジュール読み込み時に自動で一部ロードされます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番/開発/ペーパートレードは KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```
  - 注意:
    - run_execution は起動時に PID ファイルを作成します（デフォルト: data/execution.pid）。
    - ペーパートレード時は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と完全に分離されます。
    - 停止は data/stop_requested.flag を設置することで検知します。

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60）。
  - 監視は常に本番 sqlite_path（KABUSYS_ENV に依存せず）を使用してログを記録します。
  - data/stop_requested.flag により停止します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

- ライブラリ関数（例）
  - AI スコア算出（プログラムから呼ぶ場合）
    - kabusys.ai.score_news(...)
  - 市場レジーム算出
    - kabusys.ai.regime_detector.score_regime(...)

---

## 実行停止／フラグ制御

- stop_requested.flag: run_execution / run_monitoring がプロセス内で監視している停止フラグ（場所: data/stop_requested.flag）
- execution.pid: 実行エンジンの PID を記録（デフォルト data/execution.pid）
- kill.flag: monitoring が条件を満たしたときに書き込むと ExecutionEngine 側で停止シグナル（場所は Settings.kill_flag_path、デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアする（本番では 0 を推奨）

---

## ディレクトリ構成（主要ファイル）

以下は src 配下の主要ファイルとモジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA200）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（schema 作成・読み書き）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック、未掲示の実装箇所あり）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/                — 発注関連コンポーネント（OrderManager 等）※詳細ファイルはリポジトリに依存
  - data/ (runtime)
    - execution.pid
    - stop_requested.flag
    - kill.flag
    - monitoring.db (デフォルト SQLite)
    - kabusys.duckdb (デフォルト DuckDB)

（注）その他、config/*.yaml 等の設定テンプレートが存在することを想定しています。

---

## 注意点 / 運用上のヒント

- 環境（KABUSYS_ENV）により動作モードが変わります。特に paper_trading と live は DB の分離や MockBroker の使用等に違いがあるため、本番切り替え時は .env を慎重に確認してください。
- run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を参照して監視ログを記録します（監視は本番データを前提にする設計）。
- OpenAI を利用するモジュールは API 呼び出しの失敗に対してリトライやフェイルセーフ（0.0 フォールバック等）を実装していますが、API キーやレート制限には注意してください。
- データ鮮度やプロセス生存確認、リスク閾値は Settings 経由で環境変数から調整できます。KILL_FLAG_CLEAR_ON_START は本番で 1 にすると危険です（自動的に Kill Switch をクリアしてしまうため）。
- テスト／CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化するとテストの独立性が保てます。

---

必要であれば README に含めるコマンドの具体例（systemd のユニット例、Dockerfile、CI 設定）や、各モジュールの詳細設計（API、DB スキーマ、パラメータの意味）も作成します。どの情報を優先して追加しましょうか？