KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム／研究ツール群です。本リポジトリには以下の主要機能が含まれます。

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper_trading と live を切替可能）
- システム監視（SystemMonitor）・取引監視・リスク監視・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限・レジーム補正）
- リサーチ用モジュール（ファクター計算、特徴量探索、IC 計算）
- ニュースの NLP（OpenAI を利用したセンチメント評価）と市場レジーム判定
- Paper Trading 検証レポート生成ツール
- 起動時の .env 対話ウィザード・設定検証ツール

主な特徴
-------
- 環境切替: KABUSYS_ENV により development / paper_trading / live を切替
- Paper Trading モードでは実際の注文を送らず mock ブローカーを使用し DB を分離
- 監視モジュールは sqlite（monitoring.db）を用いて安定性・注文状況・リスクを永続化
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価、レジーム判定機能（API キーは環境変数で指定）
- ロギングは統一セットアップ（stdout + 日次ローテートファイル）
- フェイルセーフ設計：API エラー・DB エラーなどで全体を停止しない実装

必要条件
-------
- Python >= 3.10
- 推奨ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルのパース検証に任意）
- （開発用）pipenv/venv などで仮想環境を推奨

インストール（例）
-----------------
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

   （実プロジェクトでは requirements.txt を用意している想定です: pip install -r requirements.txt）

セットアップ手順
--------------
1. プロジェクトルートに移動（`.git` または pyproject.toml があるディレクトリがプロジェクトルートになります）。

2. .env を作成・更新（対話式ウィザード）:
   - python -m kabusys.config_setup
   - ウィザードに従い J-Quants / kabu API などの必要な環境変数を設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

3. 設定検証:
   - python -m kabusys.validate_config
   - 本番相当まで厳密にチェックするなら: python -m kabusys.validate_config --strict

4. データディレクトリ・ログディレクトリの確認（自動作成されますが、パーミッション等を事前確認してください）:
   - data/（デフォルト DB やフラグファイル用）
   - logs/（デフォルトのログ出力先）

主な環境変数（抜粋）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な任意/設定:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- その他: LINE 通知用 TOKEN 等

自動 .env 読み込み:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します。

基本的な使い方
-------------
起動スクリプト（パッケージモジュールとして実行）:

- ExecutionEngine（取引エンジン）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録。本番環境で実行する場合は KABUSYS_ENV=live を指定。

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60sec）。
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用して監視データを永続化します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

停止・フラグ管理:
- モニタリングやエンジンはプロジェクト内 data/stop_requested.flag を監視し、存在するとループを終了します（外部プロセスから停止したいときに作成）。
- Kill Switch: data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。KillSwitch はリスク条件（ドローダウンやポジション上限）を評価して flag を書き込みます。
- PID ファイル: data/execution.pid 等を PID 管理に使用します。

ログ
---
ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログレベルは環境変数 LOG_LEVEL もしくは setup_logging の引数で制御できます。

主要モジュール説明（抜粋）
-----------------------
- run_execution.py
  - ExecutionEngine を組み立て、ブローカー・OrderManager・RiskManager 等を初期化して実行します。
  - paper_trading モードでは専用の SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録。

- run_monitoring.py
  - SystemMonitor を用いて定期的にシステム状態を監視・永続化します。

- config.py
  - 環境変数・.env の読み込み・Settings 抽象化を提供。KABUSYS_ENV, DB パス, 各種しきい値を取得できるプロパティを持ちます。

- config_setup.py
  - .env を対話式で生成・更新するウィザード。

- validate_config.py
  - .env や config/*.yaml の基本検証を行う CLI。

- monitoring/
  - monitoring_db.py: SQLite スキーマ定義・永続化 API（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - risk_monitor.py: ドローダウン・ポジション数の監視
  - kill_switch.py: 判定により kill.flag を書き込む
  - monitoring_engine.py: 複数のモニタを束ねてポーリング・アラート送信

- portfolio/
  - portfolio_builder.py: 候補選定・等重/スコア重み計算
  - position_sizing.py: 株数計算・投資額スケール・lot 単位丸め
  - risk_adjustment.py: セクター上限除外・レジーム乗数

- research/
  - factor_research.py: モメンタム・ボラティリティ・バリューなどのファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン計算・IC（Spearman）等

- ai/
  - news_nlp.py: raw_news を OpenAI でスコアリングして ai_scores に格納
  - regime_detector.py: ETF（1321）MA とマクロニュースの LLM 評価を合成して market_regime を更新

- tools/
  - paper_verification_report.py: Paper Trading の運用検証レポート作成 CLI

想定ディレクトリ構成
-------------------
（主要ファイルを抜粋）

- project-root/
  - .env (生成)
  - data/
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/
    - execution.log
    - monitoring.log
  - src/
    - kabusys/
      - __init__.py
      - config.py
      - config_setup.py
      - validate_config.py
      - run_execution.py
      - run_monitoring.py
      - tools/
        - paper_verification_report.py
      - ai/
        - news_nlp.py
        - regime_detector.py
      - monitoring/
        - monitoring_db.py
        - system_monitor.py
        - risk_monitor.py
        - trade_monitor.py (参照あり)
        - kill_switch.py
        - monitoring_engine.py
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
      - execution/  (Engine, OrderManager 等の実装が含まれる)
      - data/      (DuckDB/データパイプライン関連)
      - (その他モジュール)

開発・運用上の注意
-----------------
- .env の扱い: センシティブな情報（API キー等）は .env に置き、絶対に VCS にコミットしないでください。
- 本番実行時: KABUSYS_ENV=live の設定は取り扱いに十分注意してください（通知設定や Kill Switch の挙動を事前確認推奨）。
- Paper Trading: paper_trading モードは本番 DB とは分離されます。データパスが正しいことを確認してください。
- OpenAI の利用: API 呼び出しは失敗時にフォールバック（スコア 0.0 等）する実装ですが、API キー管理とコストに注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。適切なパーミッションを用意してください。

追加情報 / コマンド早見表
------------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス・貢献
----------------
（ここにはプロジェクトのライセンス情報や貢献ガイドラインを記載してください）

---

この README はコードベースの主要点をまとめたものです。導入や運用で不明点があれば、特定のモジュール（例: ai/news_nlp.py / monitoring/system_monitor.py / portfolio/position_sizing.py）について更に詳しい説明や使用例を提供できます。必要であれば教えてください。