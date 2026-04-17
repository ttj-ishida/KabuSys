# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリ群（部分抜粋）。  
このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP / レジーム判定などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群です：

- 自動売買の実行エンジン（ExecutionEngine）と注文管理
- システムおよび取引状態の監視（Monitoring）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量探索（DuckDB を利用）
- ニュースを用いた NLP スコアリング（OpenAI API）
- ペーパートレード用の分離された DB と検証レポート生成

設計上、
- 実行と監視は DB（SQLite / DuckDB）で状態を永続化します。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離されます。
- .env と config/*.yaml で設定を管理。設定ウィザードや検証ツールを提供します。

---

## 主な機能一覧

- 実行（run_execution.py）
  - ブローカークライアントの生成（実口座 / Mock）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine の起動
  - 停止フラグ（data/stop_requested.flag）の監視、PID ファイル（data/execution.pid）管理
- 監視（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - 監視ログの永続化（SQLite）
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
- 監視 DB 層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル管理・マイグレーション
- アラート（alert_manager.py）
  - LINE Messaging API による一方向プッシュ（クールダウン管理）
- Kill Switch（kill_switch.py）
  - 条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止
- ポートフォリオ（portfolio/*）
  - 銘柄選定、スコア重み付け、セクターキャップ、ポジションサイジング
- リサーチ（research/*）
  - DuckDB を使ったモメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC (Information Coefficient)、統計サマリー
- AI（ai/*）
  - ニュースを OpenAI でスコアリング（score_news）
  - マクロとETF MA による市場レジーム判定（score_regime）
- ツール（tools/paper_verification_report.py）
  - ペーパートレード DB を集計して検証レポートを生成

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（注: union types（A | B）を使用しているため 3.10 以上を想定）
- Git

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例（最低限）:
     - pip install duckdb psutil openai requests
   - optional:
     - pip install PyYAML  # validate_config の YAML 検証を有効化する場合

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数の設定（.env）
   - 初期設定は対話式ウィザードで作成可能:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限セットすること）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI API を使う場合に必須
     - PAPER_FILL_MODE: instant | partial | never | reject  (デフォルト: instant)
   - .env を作成したら、設定検証を実行:
     - python -m kabusys.validate_config
     - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトの DB / PID / flag は data/ 以下に作成されます。
   - 必要なら手動で作成: mkdir -p data

---

## 使い方（代表的コマンド）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も FAIL 扱い

- 実行エンジン起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、デフォルトで data/paper_trading.db を使用して本番 DB と分離
    - 起動前に data/stop_requested.flag が存在すると起動しません
    - PID は data/execution.pid に書き込まれます
    - 停止は data/stop_requested.flag を作成するか（run_execution は起動中に監視して engine.stop() を呼ぶ）、Kill Switch（監視側）で data/kill.flag が書かれることで行われます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - オプション / 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依らず本番 path を使用）
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループが終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（優先度: --db > PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）
  - 出力は標準出力のテキストレポート（稼働率、成功率、レイテンシ等）

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続を渡して呼び出します
  - 両関数は API 失敗に対してフォールバックやリトライの実装あり（フェイルセーフ設計）

---

## 重要なファイル / フラグの説明

- data/execution.pid
  - 実行エンジンの PID を書きます。SystemMonitor はこの PID を参照してプロセス稼働を検知します。

- data/stop_requested.flag
  - run_execution / run_monitoring のスクリプトが監視する停止フラグ（存在するとループを終了または起動を中止します）

- data/kill.flag
  - KillSwitch が書き込むフラグ。存在すると ExecutionEngine を強制停止すべき理由が記録されています（実運用でのセーフガード）

---

## 設定項目（抜粋）

主要な Settings プロパティ（デフォルト値等）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (デフォルト: 0) — 本番では 0 推奨
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT （監視しきい値）
- KABUSYS_ENV: development | paper_trading | live

.env の作成は config_setup のウィザードを推奨します。

---

## 実装上の注意・運用メモ

- Paper Trading は実データベースと分離されています（安全を重視）。
- OpenAI を使う機能は API キーが必要。API 呼び出し部分はリトライとフォールバック（失敗時はスコア 0 等）を行いますが、API 使用料が発生します。
- Monitoring は常に本番用の sqlite_path を参照する実装になっています（KABUSYS_ENV に依らず）。
- process priority 設定は psutil に依存し、権限不足や未対応 OS の場合は警告を出してスキップします。
- validate_config により起動前に設定の妥当性チェックを行うことを推奨します。

---

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主なモジュールとファイル（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - execution/                 — Execution 系の実装（OrderManager 等）  # 一部参照あり（省略）
  - data/                      — デフォルトで使用される DB / PID / flag 等（運用環境で作成）

---

## よくある操作例（まとめ）

- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視の起動（ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

README は以上です。必要であれば以下を追加できます：
- requirements.txt の推奨内容
- 各モジュールの API 使用例（コードスニペット）
- CI / デプロイ手順（systemd 等でのサービス化方法）
どれを優先して追加しますか？