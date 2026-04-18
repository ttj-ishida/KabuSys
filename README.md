# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買システム KabuSys のコアライブラリです。  
本 README はプロジェクトの概要・機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、銘柄選定（ポートフォリオ構築）・ポジションサイジング・発注エンジン・監視・研究（ファクター計算）・AI を用いたニュースセンチメント評価などを含む、自動売買プラットフォームのプロトタイプ実装です。  
設計方針として、

- データ永続化は SQLite（監視/ペーパートレード）および DuckDB（分析）を併用
- 本番（live）/ペーパー（paper_trading）/開発（development）環境の明示的分離
- モジュール単位での純粋関数実装（テスト容易性）
- OpenAI を使ったニュース NLP / レジーム判定機能（オプション）
- ログ管理・監視・Kill Switch 機能（安全停止）

などを採用しています。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式の環境設定ウィザード（`kabusys.config_setup`）
  - 起動前チェック CLI（`kabusys.validate_config`）

- 実行エンジン
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - Paper Trading 時は MockBrokerClient を使用し、paper_trading 用 DB を分離

- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / Execution プロセス死活監視
  - TradeMonitor：滞留注文・約定異常等の監視（該当コードを参照）
  - RiskMonitor：ドローダウン、ポジション上限の監視とアラート記録
  - MonitoringEngine：各 Monitor を束ねたポーリングループ（`run_monitoring.py`）

- Kill Switch
  - 条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine を停止させる仕組み

- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、セクターキャップ適用、レジーム乗数、株数決定（単元丸め）

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC 計算・統計サマリー

- AI（オプション）
  - ニュースを OpenAI (gpt-4o-mini 等) でセンチメント評価して ai_scores に記録（`kabusys.ai.news_nlp.score_news`）
  - マクロ + ETF MA を使った市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）

- ツール
  - Paper Trading の検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## 必要な依存ライブラリ（代表）

最低限の依存（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証を厳密に行いたい場合）

インストール例（仮）:
pip install duckdb psutil openai PyYAML

（実際の requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install -r requirements.txt  （requirements.txt があれば）

3. .env の作成（2つの方法）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - ウィザードは .env に必要なキーを書き込みます（.env は Git にコミットしないでください）
   - 手動で .env を作成：
     - ルートに .env を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. 必須環境変数（代表）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live）（デフォルト: development）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意: アラート通知用）
   - その他は src/kabusys/config.py を参照

5. ディレクトリ作成（必要に応じて）
   - data/ （DB・フラグファイルを格納）
   - logs/ （ログファイルが出力されます）

---

## 使い方（コマンド例）

各モジュールはパッケージモードで起動できます（プロジェクトルートから実行）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を失敗として扱う）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込みます。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/stop_requested.flag の出現を検知すると安全停止します。
    - 実行時に data/execution.pid（デフォルト）へ pid を書き込む挙動があります。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（settings.sqlite_path）を使用して監視データを記録します。
  - 停止は data/stop_requested.flag を作成して下さい（監視プロセスは存在チェックを行い終了します）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 系（ニュース / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - モジュール関数を呼んで利用:
    - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
  - これらはライブラリ関数として利用することを想定しています（CLI ラッパーはありません）。

- 停止・Kill Switch
  - KillSwitch は内部評価の結果、`data/kill.flag` に理由を書き込むことで ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側はこのフラグを検知して停止する設計）。
  - 手動で停止したい場合は `data/stop_requested.flag` を作成してください（run_* スクリプトはこれを参照して終了します）。

---

## ログ

- ログはデフォルトで stdout と日時ローテーションされるファイル（logs/<app_name>.log）へ出力されます。
- ログ設定は `kabusys.utils.logging_setup.setup_logging` を介してアプリケーション起動時に統一的に設定されます。
- ログレベルは .env の LOG_LEVEL または引数で変更できます（"DEBUG","INFO","WARNING","ERROR","CRITICAL"）。

---

## 重要なパス・フラグファイル

- data/stop_requested.flag
  - 実行ループ（監視/エンジン）が存在を検知すると安全にシャットダウンします。

- data/kill.flag
  - Kill Switch が書き込み、ExecutionEngine を停止させるための永続フラグ（本番環境では自動クリア設定に注意）。

- data/execution.pid（デフォルト）
  - ExecutionEngine が PID を記録するためのファイルパス（Settings.pid_file_path で変更可）。

- DB
  - DuckDB: デフォルト data/kabusys.duckdb（Settings.duckdb_path）
  - 監視 SQLite: デフォルト data/monitoring.db（Settings.sqlite_path）
  - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

---

## よく使う環境変数（代表）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- PAPER_FILL_MODE — paper_trading の fill モード（instant|partial|never|reject）
- OPENAI_API_KEY — AI 機能利用時に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知設定（任意）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリアを避ける（0 推奨）

設定は .env / .env.local に記述できます。`kabusys.config` が起動時にプロジェクトルートを基準に自動読み込みします（無効化可）。

---

## ディレクトリ構成（主要ファイル抜粋）

以下はリポジトリ内の主要なモジュール構成（src/kabusys 配下）です。実際のファイル数は多いため代表的なものを列挙します。

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / Settings クラス
    - config_setup.py        — .env 対話ウィザード
    - validate_config.py     — 起動前検証 CLI
    - run_execution.py       — ExecutionEngine 起動スクリプト
    - run_monitoring.py      — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
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
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                  — 実行時に DB / フラグファイルを置く（git 管理しないこと）
    - config/                — yaml 設定ファイル（system_config.yaml など。テンプレートあり）

---

## 運用上の注意点 / ベストプラクティス

- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に保つことを推奨します。
- Monitoring は本番の監視 DB（settings.sqlite_path）を使って永続化するため、監視用の DB バックアップやローテーション方針を検討してください。
- ExecutionEngine の起動前に `python -m kabusys.validate_config` で設定検証を行ってください。
- AI 機能は API 費用が発生するため利用時は注意してください（レート制限やリトライの実装は入っていますが、API キー・課金ポリシーの管理を行ってください）。
- ログディレクトリの権限・ディスク容量監視を行ってください（TimedRotatingFileHandler により日次ローテーションされますが、バックアップ保持数は設定されています）。

---

## 参考（よくある起動例）

- 初期セットアップ（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定確認
  - python -m kabusys.validate_config

- 監視をデーモンとして起動（例: systemd / supervisor でラップ）
  - python -m kabusys.run_monitoring &
  - （MONITOR_POLL_INTERVAL=30 を環境に設定すると 30 秒間隔でポーリング）

- Execution 起動（paper_trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば、README に含めるコマンドの詳細、設定ファイル雛形（.env.example）、systemd ユニットファイルサンプル、あるいは API ドキュメント（関数引数や戻り値の詳細）などを追加します。どの部分をより詳しくまとめるか教えてください。