KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株自動売買（Execution）とそれを支える監視（Monitoring）、研究（Research）、ポートフォリオ構築（Portfolio）、AI（ニュースセンチメント / レジーム検出）などのコンポーネントをまとめたコードベースです。  
設計方針として、実運用に耐える監視・ログ・フェイルセーフ機構（Kill Switch、監視 DB、ログローテーション等）を備えつつ、研究・検証用に DuckDB を使った分析環境を提供します。

主な特徴
---------
- ExecutionEngine（発注エンジン）と BrokerClientFactory による本番／ペーパートレード切替
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて paper_trading DB（data/paper_trading.db）へ記録し、本番 DB と完全分離
- Monitoring（System / Trade / Risk モニタ）と Kill Switch による自動停止・アラート
  - 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 研究モジュール（research）: ファクター計算、将来リターン、IC 計算、特徴量サマリ等（DuckDB 前提）
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、セクターキャップ、ポジションサイズ計算（単元丸め等）
- AI モジュール（ai）: ニュースの LLM によるセンチメント評価、レジーム判定（OpenAI クライアントを使用）
  - API 呼び出しは可変的にリトライ・フェイルセーフ実装
- ユーティリティ: ロギングセットアップ（stdout + 日次ローテーション）、プロセス優先度／CPU affinity 設定、.env ウィザード、設定検証 CLI 等
- ツール: Paper Trading の検証レポート生成スクリプト

セットアップ手順（開発・実行共通）
-------------------------------
1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最小依存（例）:
     - pip install duckdb psutil openai
   - 追加（任意）:
     - pip install pyyaml  # validate_config が YAML の検証を行う場合
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt

3. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに沿って J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV 等を設定します。
   - 生成された .env を Git にコミットしないでください（機密情報含む）。

4. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は修正して再実行。--strict を付けると警告も FAIL 扱いになります。

環境変数（主要）
----------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / オプション
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs/）
  - OPENAI_API_KEY: OpenAI API Key（ai モジュール利用時必須）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

主な実行方法（コマンド例）
--------------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution Engine を起動（本番/ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行開始時に process priority を "high" に設定し、paper_trading の場合は専用 DB に接続します。
  - data/stop_requested.flag（または _STOP_FLAG）を作成すると停止処理が走ります。

- Monitoring を起動（バックグラウンド定期実行想定）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI モジュール（プログラム内から利用）
  - ニューススコアリング: from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)
  - これらは OpenAI API を使用します（OPENAI_API_KEY または api_key 引数が必要）。

運用に関する重要なポイント
-------------------------
- ペーパートレード分離
  - KABUSYS_ENV=paper_trading の場合、発注系は本番 DB を汚染しません。paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます。
- Kill Switch / 停止フラグ
  - kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine は安全に停止します（KillSwitch による自動書き込みもあり）。
  - data/stop_requested.flag を置くと run_execution / run_monitoring のループは検出して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動でクリアされます）。
- ロギング
  - setup_logging により stdout（StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）を出力します。
  - LOG_DIR の作成に失敗した場合はコンソール出力のみで継続します。
- DB マイグレーション
  - init_monitoring_db(conn) は必要なテーブルとインデックスを冪等に作成します。既存 DB の簡易マイグレーション（カラム追加など）も実施します。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / Settings 管理（.env 自動ロード機能含む）
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 起動前チェック CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - ai/
      - news_nlp.py              — ニュースセンチメント（OpenAI）
      - regime_detector.py       — 市場レジーム判定（OpenAI + MA）
    - monitoring/
      - monitoring_db.py         — 監視ログ SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py         — （存在: 参照あり）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py         — （存在: 参照あり）
    - execution/
      - execution_engine.py      — ExecutionEngine（エンジン本体）
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - その他発注関連
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/                       — 既定の保存先（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）
    - logs/                       — ログ出力先（デフォルト）
- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, ... （サンプル / 参照用）

開発上の注意 / テストヒント
-------------------------
- validate_config は PyYAML が無ければ YAML の中身チェックをスキップしますが、存在する場合は YAML の構文チェックも行います。
- AI モジュールは OpenAI クライアント呼び出しを内部でラップしているため、テスト時は _call_openai_api をモックすることが想定されています。
- MonitoringEngine.run_once / 各 Monitor の check_once はユニットテスト向けに単発実行できるよう設計されています。
- DuckDB 接続を渡して research や ai の関数を直接呼び、結果を確認することでオフライン検証が可能です。

ライセンス・貢献
----------------
- 本 README はコードベースの説明です。実際のライセンスファイル（LICENSE）や貢献ガイドがプロジェクトに含まれる場合はそちらに従ってください。

最後に
------
まずは以下の順で準備・確認することを推奨します。
1. 仮想環境作成 → 依存ライブラリをインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定検証
4. DuckDB / SQLite ファイルの場所を確認
5. python -m kabusys.run_monitoring（監視）と python -m kabusys.run_execution（発注）を起動

追加で README に載せたい項目（例）
- requirements.txt（推奨パッケージ一覧）
- systemd / supervisor 用のサンプルユニットファイル
- 実運用時の監視アラート設計（LINE 通知テンプレート等）

必要であれば上記の追記（サンプル systemd ユニット、例 .env.example、要件一覧）も作成します。どの追加情報が欲しいか教えてください。