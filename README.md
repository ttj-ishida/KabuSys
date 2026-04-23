# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ + 実行スクリプト群）。

この README はコードベースの主要機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は、シグナル生成 → ポートフォリオ構築 → 発注（Execution） → 監視（Monitoring）までを含む日本株自動売買プラットフォームの骨格実装です。  
主な設計方針は以下の通りです。

- DuckDB を用いてファクター計算やリサーチ処理を行う（prices_daily / raw_financials / raw_news 等のテーブルを利用）。
- Execution は本番（live）／ペーパートレード（paper_trading）を切り替え可能。ペーパー時は MockBrokerClient を使い DB を分離。
- Monitoring はシステム健全性・注文状況・リスク指標を定期ポーリングしてログ・アラート・Kill Switch を管理。
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / レジーム判定の拡張機能を内蔵（APIキー必須、失敗時はフェイルセーフで継続）。
- 設定は .env 経由で管理。対話式ウィザードと検証スクリプトを提供。

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（.env / .env.local、OS 環境変数優先）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行エンジン（Execution）
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - 本番 / ペーパー切替（KABUSYS_ENV）
  - RiskManager、OrderManager、Reconciler 等の組立て
  - PID ファイル管理 / stop flag による停止

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（python -m kabusys.run_monitoring）
  - monitoring DB（SQLite）による永続化
  - Kill Switch（data/kill.flag）による Execution 停止
  - MONITOR_POLL_INTERVAL によるポーリング間隔制御（デフォルト 60 秒）

- ポートフォリオ構築（純関数群）
  - 銘柄選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数

- リサーチ / 特徴量計算
  - momentum、volatility、value 等のファクター計算
  - forward returns、IC 計算、統計サマリー

- AI / NLP 機能（OpenAI）
  - ニュース記事を LLM でセンチメント集計して ai_scores に書き込み
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（market_regime へ書込み）

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提（推奨環境）

- Python 3.10+
- 推奨パッケージ（pipでインストール）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定検証で YAML 検査を行う場合）
- SQLite は標準ライブラリで利用可能

requirements.txt がある場合はそれを利用してください。なければ例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
   - git clone ... && cd <project>

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の生成（対話式推奨）
   - python -m kabusys.config_setup
     - 対話形式で .env を作成／更新します。
     - 作成後は必ず機密情報（トークン・パスワード）を正しく設定してください。

5. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱いで exit(1) になります。

6. データディレクトリの確認
   - デフォルトの DB / PID / flag の場所はプロジェクト内の data/ 以下です。必要なら .env で上書きしてください。

環境変数の主な例（.env に設定）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY (AI 機能を使う場合)
- PID_FILE_PATH / KILL_FLAG_PATH 等も .env で上書き可能

---

## 使い方（主要コマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と完全分離）。
    - 実行中に data/stop_requested.flag が作成されると安全停止します。
    - 実行時に PID ファイル（デフォルト data/execution.pid）を出力します。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は設定上の環境に関わらず本番 sqlite_path を使用して監視データを記録します。
  - 監視中に project_root/data/stop_requested.flag が存在すると監視ループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶかスクリプト化して実行
  - OPENAI_API_KEY の設定が必要。API 呼び出しは失敗時にフォールバック動作をする設計です。

ログ:
- デフォルトのログ出力先は logs/<app_name>.log とコンソール（stdout）。
- setup_logging が各起動スクリプトで呼ばれます。
- LOG_DIR / LOG_LEVEL は .env または環境変数で制御可能。

停止フラグ / Kill Switch:
- data/stop_requested.flag: run_execution / run_monitoring がチェックする停止要求ファイル（外部からの停止要求に利用）。
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止を促す（Risk 条件などで書き込まれる）。

---

## 運用メモ / 注意点

- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や Kill Switch の取り扱いに注意してください。validate_config は本番向けの追加チェックを行います。
- run_execution と run_monitoring はそれぞれプロセス優先度を "high" に設定しようとします。権限や OS によっては設定に失敗する場合があり、その場合は警告ログが出ます。
- ペーパートレードでは DB を分離しているため、本番 DB を汚す事故を防げます。PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- DuckDB / SQLite のパスは .env で指定可能。ログディレクトリも同様です。
- OpenAI を利用する機能は API 呼び出しの失敗に対して堅牢化されていますが、API キーと利用料に注意してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（.env 自動ロード挙動を含む）
  - config_setup.py
    - 対話式 .env ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag 管理、paper_trading 対応）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
  - utils/
    - logging_setup.py: ログ初期化ユーティリティ
    - process_priority.py: プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite 監視 DB 永続化層（テーブル初期化含む）
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: （注文監視ロジック）
    - risk_monitor.py: ドローダウン・ポジション上限の監視
    - kill_switch.py: Kill Switch 制御（kill.flag）
    - monitoring_engine.py: 各 Monitor を束ねるエンジン
    - alert_manager.py: （アラート送信ロジック）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - Execution に関する主要コンポーネント（発注・リスク制御等）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み付け
    - position_sizing.py: 発注株数計算
    - risk_adjustment.py: セクター制限・レジーム乗数
  - research/
    - factor_research.py: momentum/volatility/value 計算
    - feature_exploration.py: forward returns / IC / 統計サマリ
  - data/
    - pipeline.py 等（prices_daily 取得・ETL 補助）
  - ai/
    - news_nlp.py: ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py: レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート

プロジェクトルートには data/（DB・flag・pid を置く）、logs/（ログ）を作成して運用する想定です。

---

## よく使うコマンド例

- .env を作る:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視をデーモン的に起動（開発環境での手動起動）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート（期間指定）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README の追加項目（デプロイ手順、systemd / supervisor 設定例、CI／テスト方法など）を作成できます。特に本番環境運用に移す場合、ログローテーション、バックアップ、監視（外部）、および安全停止フローのドキュメント整備をおすすめします。