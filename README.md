README
=====

概要
----
KabuSys は日本株向けの自動売買システム（リサーチ・ポートフォリオ構築・発注・監視・AI 補助機能を含む）です。
このリポジトリは、実運用（live）、ペーパートレード（paper_trading）、開発（development）を切り替えて利用できるよう設計されています。
主要な起動スクリプトやユーティリティ、監視／レポート機能、ポートフォリオ構築の純粋関数群、AI 関連モジュール（OpenAI を用いたニュース NLP / レジーム判定）などを含みます。

主な特徴
--------
- ExecutionEngine（発注処理）と Monitoring（監視）を独立して実行可能
- Paper trading モードでは MockBroker を使用し、実運用 DB と完全分離
- モニタリング：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）監視、Kill Switch
- ポートフォリオ構築：候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ：定量ファクター計算（モメンタム/バリュー/ボラティリティ 等）、IC 計算、特徴量サマリ
- AI：ニュースのセンチメントスコアリング、マクロニュースを使った市場レジーム判定（OpenAI）
- ツール：ペーパートレードの検証レポート生成スクリプトなど
- 設定支援：.env 作成ウィザード、設定検証 CLI

システム要件
------------
- Python 3.10+
- 必要なパッケージ（例、主要なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証で必要）
- （推奨）仮想環境（venv / pyenv など）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <このリポジトリ>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows (PowerShell では別コマンド)

3. 依存ライブラリをインストール
   - もし requirements.txt があれば: pip install -r requirements.txt
   - 最小例（requirements.txt が無い場合）:
     - pip install duckdb psutil openai PyYAML

4. 環境変数 (.env) を作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（プロジェクトルートに .env）
   - 必須環境変数（少なくともこれらを設定してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（デフォルト値は .env ウィザードや Settings クラス参照）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（paper_trading 時に使用）
     - LOG_LEVEL — デフォルト: INFO
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
     - OPENAI_API_KEY — AI 機能を使う場合に必要

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

基本的な使い方
--------------
- 実行（ExecutionEngine）
  - 役割: 発注処理の開始。KABUSYS_ENV に応じて実ブローカ or MockBroker を選択。
  - 実行コマンド:
    - python -m kabusys.run_execution
  - 実行時の挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、デフォルトで data/paper_trading.db に記録する（本番 DB と分離）。
    - 起動前に data/stop_requested.flag が存在すると起動を中止する。
    - 実行中は data/execution.pid が作成される (設定により PID パスは変更可能)。

- 監視（Monitoring）
  - 役割: SystemMonitor 等をポーリングしてシステム状態や注文の異常を検知、kill.flag を書くなどを行う。
  - 実行コマンド:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL — ポーリング間隔（秒）。デフォルト 60 秒。
  - 備考:
    - 監視は常に本番 sqlite_path を参照（環境に依存せず本番監視 DB を使う設計）。
    - 停止は data/stop_requested.flag を置くことでループ内で検知して終了する。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env ファイルを対話的に生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - config/*.yaml の存在や .env の必須値等をチェックします。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH で DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）
  - 出力: 稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定

- AI 機能（ニュース NLP / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を利用してニュースをスコアリング・レジーム判定を行います。
  - OpenAI API キーが必要（OPENAI_API_KEY または api_key 引数）。
  - これらは DuckDB 接続を受け取り、ai_scores や market_regime テーブルへ書き込みます。

kill.flag / stop flag / PID
----------------------------
- data/kill.flag: Kill Switch が発動した場合に監視側が書き込むファイル。ExecutionEngine は Settings.kill_flag_path を参照して対処できます。
- data/stop_requested.flag: run_monitoring / run_execution のループを優雅に終了させるためのフラグ。手動で作成してください。
- data/execution.pid (デフォルト): 実行エンジンの PID を記録するファイル（パスは Settings で上書き可）。

ログ
----
- デフォルトでコンソール出力（stdout）とファイル出力を行います。
- ログファイルディレクトリ：ログは logs/<app_name>.log（デフォルト logs/）に日次ローテーションで保存されます（30 日保持）。
- ログレベルは LOG_LEVEL 環境変数で調整可能。

設定（Settings）概要
-------------------
Settings クラスは環境変数から各種設定を取得します。主要プロパティ：
- jquants_refresh_token
- kabu_api_password
- kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- line_channel_access_token, line_user_id
- duckdb_path (デフォルト: data/kabusys.duckdb)
- sqlite_path (デフォルト: data/monitoring.db)
- paper_sqlite_path (PAPER_TRADING_SQLITE_PATH, デフォルト: data/paper_trading.db)
- pid_file_path / kill_flag_path
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- env (KABUSYS_ENV: development | paper_trading | live)
- log_level

ディレクトリ構成（主要ファイル）
-----------------------------
プロジェクトの主要なソース配置（src/kabusys を基準）:

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョンなど）
  - config.py                  — 環境変数読み込み・Settings 定義・.env 自動ロード
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py         — ルートロガー設定（コンソール + 日次ファイルローテーション）
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py         — SQLite を用いた監視 DB 操作層
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度・プロセス死活チェック
    - trade_monitor.py         — (注文監視用ファイル、コード中で参照)
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — Kill Switch（kill.flag 書き込み）
    - monitoring_engine.py     — 複数 Monitor を束ねるポーリングエンジン
    - alert_manager.py         — （通知管理、コードベースに存在する想定）

  - execution/
    - execution_engine.py      — ExecutionEngine 本体（run_session など）
    - order_manager.py         — 注文マネージャ
    - order_repository.py      — 注文永続化（SQLite）など
    - broker_factory.py        — ブローカクライアント生成（Mock / 実 API）
    - reconciler.py            — 注文整合処理
    - risk_manager.py          — 発注前のリスクチェック

  - portfolio/
    - portfolio_builder.py     — 候補選定、重み付け（等重/スコア重み）
    - position_sizing.py       — 株数決定・aggregate cap・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py       — モメンタム/バリュー/ボラティリティ計算（DuckDB）
    - feature_exploration.py   — 将来リターン / IC / 統計要約
    - __init__.py

  - ai/
    - news_nlp.py              — ニュースを OpenAI で解析して ai_scores に書き込む
    - regime_detector.py       — マクロ + ETF MA から市場レジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

補足・運用上の注意
-----------------
- Paper trading: KABUSYS_ENV=paper_trading を使うと MockBroker を用いて本番 DB と完全分離で記録します（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視は本番 sqlite_path を参照します（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用）。
- OpenAI を使用する機能は API キーとネットワーク接続が必要です。失敗時のフォールバックロジックは実装されていますが、結果が空になる場合があります。
- .env は機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- ログディレクトリや data/ の書き込み権限を事前に確認してください。

よくあるコマンドまとめ
---------------------
- 環境ウィザード（.env 作成）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- （AI スコアリングをプログラム的に呼ぶ場合）DuckDB 接続を作り、
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")

ライセンス / 貢献
-----------------
- 本 README ではライセンス情報を記載していません。リポジトリルートの LICENSE 等を参照してください。
- コントリビュートする際は、機密情報（API トークン等）を含めないように注意してください。

以上。README に関して追加で記載したい項目（サンプル .env.example、起動時の systemd / supervisor 用ユニット例、より詳細なアーキテクチャ図など）があれば教えてください。必要に応じて追記します。