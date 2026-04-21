# KabuSys — 日本株自動売買システム (README)

本リポジトリは日本株向けの自動売買プラットフォームの一部実装です。  
主に以下の責務を持つコンポーネント群を含みます：市場データ処理・リサーチ、ポートフォリオ構築、ポジションサイズ計算、発注/実行エンジン、監視・アラート、AI を活用したニュース評価、運用補助ツール。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール化された自動売買基盤です。

- 株価や財務データからファクターを計算し、シグナルを生成する（research）  
- 候補銘柄選定・重み計算・ポジションサイズ算出（portfolio）  
- ExecutionEngine による発注/注文管理（execution） — 本番 / ペーパートレードの切替対応  
- システム状態・注文状況・リスク監視と Kill Switch（monitoring）  
- OpenAI を用いたニュースセンチメント評価・市場レジーム判定（ai）  
- 運用支援ツール（.env ウィザード・設定検証・ペーパートレード検証レポート 等）  

設計方針として「副作用を最小化した純粋関数」「ルックアヘッドバイアス回避」「部分故障時のフェイルセーフ」を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env 対話式ウィザード（kabusys.config_setup.run_wizard）
  - 起動前の設定検証 CLI（kabusys.validate_config）
  - 環境自動読み込み（プロジェクトルートの .env / .env.local）
- 実行エンジン（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント抽象化
  - OrderManager / RiskManager / Reconciler / ExecutionEngine
- 監視（Monitoring）
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限
  - MonitoringDB: SQLite へログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch: 指定しきい値を超えたら data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各モニタを統合してポーリング（run / run_once）
- ポートフォリオ構築
  - 銘柄選定（score 降順）、等比率・スコア重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ算出（risk_based / equal / score）、単元株（lot）丸め、aggregate cap
- リサーチ / 統計
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - forward returns、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - ニュースを LLM でスコア化し ai_scores に保存（news_nlp.score_news）
  - ETF とマクロニュースを合成して市場レジーム判定（regime_detector.score_regime）
  - API コールはリトライ・バリデーション付きで安全に実行
- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+（typing の一部機能を利用）
- SQLite（stdlib）
- DuckDB（Python パッケージ）
- psutil（プロセス優先度 / CPU 情報）
- openai（AI 機能を使う場合）
- PyYAML（config の YAML 検証に任意で使用）

推奨パッケージ（例）:
- duckdb
- psutil
- openai
- pyyaml

例: 仮想環境を作って必要パッケージをインストールする
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb psutil openai pyyaml
- Windows (PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1
  - pip install --upgrade pip
  - pip install duckdb psutil openai pyyaml

初期設定 (.env)
1. リポジトリルートでウィザードを実行:
   - python -m kabusys.config_setup
2. 生成した .env を編集して必要なシークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定。
   - 注意: .env は Git にコミットしないでください。

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）として扱います

data ディレクトリ / DB 作成
- デフォルトでは data/ 以下に SQLite / DuckDB / pid/flag ファイルを作成します。必要に応じて手動でディレクトリを作成してください:
  - mkdir -p data logs

環境変数の自動読み込みを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを行いません（テスト用途）。

---

## 使い方（主要コマンド例）

1. .env の作成（ウィザード）
   - python -m kabusys.config_setup

2. 設定の検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

3. 実行エンジン起動（本番/ペーパーは KABUSYS_ENV に依存）
   - python -m kabusys.run_execution
   - ペーパートレード:
     - 環境変数 KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録されます。

4. 監視ループ起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30（秒）
   - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境に依らず）

5. 停止制御
   - Graceful 停止: プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring/run_execution 内ループが検知して終了します。
   - Kill Switch: monitoring の評価で data/kill.flag が書かれると ExecutionEngine は停止シグナルとして扱います。
   - 起動時に Kill Flag を自動クリアしたい場合は .env で KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では推奨しません）。

6. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
   - DB は環境変数 PAPER_TRADING_SQLITE_PATH、または --db オプションで指定可能

7. ログ
   - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30日保持）
   - ログレベルは環境変数 LOG_LEVEL で調整

注意: AI 機能を使うには環境変数 OPENAI_API_KEY を設定してください。AI モジュールはエラー時にフェイルセーフ動作（0.0 等）で継続するよう設計されていますが、API 使用料に注意してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使用する場合に必要
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB のデフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（KABUSYS_ENV=paper_trading）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。0推奨）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス。環境変数の解決・デフォルト・検証を担う。
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番/ペーパートレード対応）
  - run_monitoring.py
    - SystemMonitor を用いた監視ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化・CRUD ラッパー（MonitoringDB）
    - system_monitor.py
      - CPU/MEM/DISK、プロセス検出、データ鮮度チェック
    - trade_monitor.py (参照されるが実装はプロジェクト内に存在する想定)
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（RiskMonitor）
    - monitoring_engine.py
      - 各モニタ・KillSwitch・AlertManager を束ねる
    - kill_switch.py
      - data/kill.flag の作成・評価
    - alert_manager.py (参照されるが実装はプロジェクト内に存在する想定)
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 発注/実行に関するコンポーネント（モジュール設計参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
      - 銘柄選定・重み計算・ポジションサイズ・セクター制限等
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
      - DuckDB を用いたファクター計算・IC/統計解析
  - ai/
    - news_nlp.py
      - ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py
      - 市場レジーム判定（ETF MA + マクロニュース LLM）
    - __init__.py
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証用の集計・判定レポート
  - utils/
    - logging_setup.py
      - 共通ログ設定（stdout + 日次ローテートファイル）
    - process_priority.py
      - プロセス優先度設定（Windows / POSIX 対応）
    - __init__.py

その他、scripts / config/*.yaml やデータディレクトリ（data/）を期待します。config/*.yaml 用のテンプレートはスクリプトで生成する想定です（validate_config は YAML の存在もチェックします。PyYAML が無い場合は該当チェックはスキップします）。

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定を慎重に扱ってください。validate_config は live 時の追加警告を出します。
- Kill Switch（data/kill.flag）は本番で強力な停止機構です。KILL_FLAG_CLEAR_ON_START=1 の設定は本番では推奨しません。
- OpenAI など外部 API を利用する機能は API キーと使用料に注意して運用してください。API の失敗は安全にフォールバックする設計ですが、結果欠落やスコア不一致が生じます。
- ログは logs/ に出力されます。log ローテーションと保持日数は logging_setup.py 内で制御（デフォルト 30 日）されています。
- DuckDB / SQLite ファイルは data/ 配下に配置されることが多いです。バックアップ・排他アクセスに注意してください。

---

もし README に追加してほしい項目（例: 開発向けのユニットテスト実行方法、CI 設定、詳細な設定項目一覧など）があれば教えてください。必要に応じてサンプル .env のテンプレートや典型的な運用フローも追記します。