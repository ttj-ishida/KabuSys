README — KabuSys（日本株自動売買システム）
=======================================

概要
----
KabuSys は日本株の自動売買およびそれを支える監視・リサーチ機能を備えた軽量なシステムです。本リポジトリは主に以下を提供します。

- 注文実行エンジン（ExecutionEngine）とその周辺コンポーネント（注文管理、リスク管理、ブローカー抽象化）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine）
- ポートフォリオ構築・ポジションサイズ計算（等配分・スコア加重・リスクベース等）
- リサーチ（ファクター計算、特徴量探索、IC計算 等）
- AI 支援モジュール（ニュースのセンチメント解析 / 市場レジーム判定；OpenAI を利用）
- 各種 CLI ユーティリティ（.env 設定ウィザード、設定検証、ペーパートレード検証レポート 等）

主な機能
--------
- ExecutionEngine
  - 本番（live）/ ペーパートレード（paper_trading）を切り替え可能
  - ブローカークライアントを抽象化し、paper_trading 時は MockBrokerClient を使用して本番 DB と分離
- Monitoring
  - システム資源（CPU/メモリ/ディスク）、プロセス生存、データ鮮度を監視
  - 注文の滞留検出、約定価格異常検出
  - ドローダウンやポジション上限の監視と Kill Switch（data/kill.flag）連携
  - 監視ログは SQLite（monitoring.db）に保存
- Portfolio モジュール
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- AI（OpenAI）
  - raw_news を LLM（gpt-4o-mini）でスコアリングして ai_scores に書込み
  - マクロニュースで市場レジーム判定（market_regime に保存）
  - API 呼び出しはリトライ・バックオフやフェイルセーフ（失敗時は neutral 相当で継続）
- ツール
  - .env 生成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------

1. Python 環境
   - Python 3.10+ を推奨（typing 機能を使用）
   - 仮想環境を作成・有効化するのを推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML (config 検証で使用)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env の準備（対話ウィザード推奨）
   - 初期設定を対話式で作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（下記「環境変数」を参照）

4. 設定検証
   - 簡易チェック:
     - python -m kabusys.validate_config
   - 警告を厳密エラー扱いにする:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトで data/ に DB や PID/flag ファイルを作成します。必要に応じてパスは環境変数で上書きできます。

環境変数（主要）
----------------
必須（実行に必須なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API アクセス用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

重要なオプション
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し DB は data/paper_trading.db を使用（分離）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite パス（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill switch ファイルパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動削除するか（0/1、デフォルト 0）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant|partial|never|reject、デフォルト instant）

簡易 .env 例
-------------
（このファイルは決して Git にコミットしないこと）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方（主要コマンド）
--------------------

- 環境作成ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告をエラー扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番/開発（デフォルト）:
    - python -m kabusys.run_execution
  - ペーパートレードで起動（Mock ブローカー、data/paper_trading.db を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  実行のポイント:
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。
  - data/stop_requested.flag が存在すると起動を行わない/停止します（run_execution, run_monitoring の停止制御）。
  - 実行中、data/execution.pid に PID を書き込みます。

- Monitoring（単体起動）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - レポートは稼働率、注文成功率、送信率、レイテンシなどを出力して PASS/FAIL を判定します。

重要な挙動・運用メモ
-------------------
- ペーパートレードは本番データと完全分離されるよう設計されています（別 SQLite ファイルを使用）。
- Kill Switch:
  - RiskMonitor が基準を超えると KillSwitch が data/kill.flag を書き込み、ExecutionEngine は起動中にこのファイルを検知すると停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番環境では注意）。
- OpenAI の利用:
  - news_nlp.score_news / regime_detector.score_regime は OPENAI_API_KEY に依存します。
  - LLM の呼び出しはリトライ・バックオフやレスポンスバリデーションを行い、失敗時はフェイルセーフ（スコア=0 相当）で継続します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等でテーブル作成および簡易マイグレーション（カラム追加）を行います。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理、自動 .env ロード
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 単独ポーリング起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py            — ニュースを OpenAI でスコアリング
  - regime_detector.py     — マクロ + ma200 を組み合わせたレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 監視 DB 層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （アラート送信）※本コードベースの実装に依存
- execution/
  - (order_manager / execution_engine / broker_factory など)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py

data/
- （実行時に生成される DB、PID、flag ファイル等）
  - kabusys.duckdb (default)
  - monitoring.db (default SQLite)
  - paper_trading.db (paper_trading 用 SQLite)
  - execution.pid
  - kill.flag
  - stop_requested.flag

開発・拡張のヒント
------------------
- DuckDB 接続を受け取る研究モジュールは副作用が少なく、テストが容易です（SQL を直接実行して結果を検証可能）。
- AI モジュールは外部 API 呼び出し箇所を小さく切り出しているため、ユニットテストでは呼び出し部分をモックしやすく設計されています。
- モニタリングやリスク判定はログと DB への永続化を行うため、運用中の診断やアラートルールの調整がしやすいです。

ライセンス・注意事項
-------------------
- .env には機密情報（API キー・パスワード）を含めるため、絶対にリポジトリにコミットしないでください。
- 本システムを実運用（実際の注文送信）する場合は、十分な検証・リスク管理を行ってください。特に KABUSYS_ENV=live の設定は慎重に取り扱ってください。

問い合わせ
----------
不明点や実行時の問題があれば、実行ログ（INFO/ERROR 出力）と data/ 以下の関連ファイル（該当する DB、pid/flag）を添えて共有してください。

以上。