README
======

概要
----
KabuSys は日本株向けの自動売買システム（ライブラリ + 起動スクリプト群）です。  
本リポジトリは、以下のような機能をモジュール化して提供します。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアントを介した発注・注文管理
- 監視（Monitoring） — システム状態、注文の健全性、リスク（ドローダウン等）を定期チェック
- ポートフォリオ構築ロジック（候補選定・重み計算・枚数決定）
- リサーチ（ファクター計算・特徴量探索）
- AI 補助（ニュースセンチメント、レジーム判定） — OpenAI を利用可能
- 開発支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

目標は本番環境での堅牢な自動売買運用と、研究／検証用の分析パイプラインの両立です。

主な機能一覧
-------------
- run_execution.py：ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db がデフォルト）に記録して本番 DB と分離
  - 起動時にプロセス優先度を "high" に設定
  - 停止は data/stop_requested.flag や data/kill.flag によるフラグで制御
- run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更（デフォルト 60 秒）
  - 監視用 DB（SQLite）は環境に関係なく本番 sqlite_path を参照
- monitoring パッケージ
  - system_monitor：CPU/MEM/DISK、プロセス生存、データ鮮度をチェック
  - trade_monitor：発注ログ・滞留注文・約定異常の検出（ソース内に実装）
  - risk_monitor：ドローダウン・ポジション上限監視、必要時 risk_logs に記録
  - kill_switch：条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止させる
  - monitoring_db：監視用 SQLite のテーブル定義・読み書きユーティリティ
  - monitoring_engine：複数モニタをまとめて定期実行、アラート発行
- portfolio パッケージ（純粋関数）
  - 候補選定、等ウェイト／スコア加重、ポジションサイズ計算（リスクに基づく方式含む）、セクター上限適用、レジーム乗数
- research パッケージ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ等
- ai パッケージ
  - news_nlp.score_news：raw_news を OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロニュースセンチメントを合成して market_regime に保存
  - OpenAI 使用時は OPENAI_API_KEY が必要
- utils
  - logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: Windows/Linux での優先度設定と CPU affinity
- 設定関連
  - config_setup.py：.env を対話式に作成・更新するウィザード
  - validate_config.py：.env や config/*.yaml の起動前検証
- tools
  - paper_verification_report.py：ペーパートレード DB から検証レポートを生成（稼働率・成功率・レイテンシ等）

セットアップ手順
----------------

前提
- Python 3.9+ を想定（実際の要件は依存パッケージに依存）
- 必要なパッケージ例（プロジェクトの requirements.txt に従ってください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML の中身を検証する場合）
  - その他（実装のブローカークライアント等に依存）

手順概要
1. リポジトリをクローンし、仮想環境を準備して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
   - pip install -r requirements.txt もしくは pip install duckdb psutil openai pyyaml

2. .env を作成する（自動ロードあり）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作る（.env.example を参照）

   自動ロードの仕組み:
   - 起動時にプロジェクトルート（.git または pyproject.toml を探索）から .env を自動読み込みします。
   - OS 環境変数 > .env.local > .env の順に優先されます。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

3. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に FAIL としたい場合は --strict を付けます。

4. データディレクトリの準備
   - デフォルトでは data/ に SQLite DB 等を作成します。必要に応じて .env の SQLITE_PATH や DUCKDB_PATH を変更してください。
   - ログは logs/ に保存されます（LOG_DIR 環境変数で変更可能）。

基本的な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading モードの DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- LOG_LEVEL（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、run_monitoring で使用）
- PAPER_FILL_MODE（paper_trading の注文約定挙動: instant|partial|never|reject、デフォルト instant）

使い方
------

設定ウィザード / 検証
- 対話式に .env を作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱い

ExecutionEngine（発注エンジン）の起動
- 標準起動:
  - python -m kabusys.run_execution
- ペーパートレード（.env の KABUSYS_ENV=paper_trading を設定）では MockBrokerClient を使い data/paper_trading.db に記録します
- 起動は data/stop_requested.flag の存在で抑止、停止時は同フラグを作成してエンジンに停止を通知します
- PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書き出されます

Monitoring（監視）の起動
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）
- 監視は SQLite（Settings.sqlite_path）と DuckDB（Settings.duckdb_path）に接続して動作します
- data/stop_requested.flag を配置すると監視ループが終了します

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスを指定する場合:
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY を設定して利用します
- ニュースのスコアリング:
  - kabusys.ai.news_nlp.score_news を呼び出すコードから利用
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime を呼び出す
- 注意: API 呼び出しはリトライやフェイルセーフを組んでいますが、コストやレート制限に注意してください

ログ
- logging_setup.setup_logging を各起動スクリプトから呼び出して統一的にログ出力
- デフォルトログディレクトリ: logs/
- ログファイル名は app_name（例: execution）に基づいて logs/execution.log に日次ローテートで保存

Kill Switch / 停止フラグ
- kill_switch はリスク条件（ドローダウン、ポジション上限など）から data/kill.flag を書き込み、ExecutionEngine 側が停止する仕組みです
- kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag を自動クリアします（本番では 0 推奨）

ディレクトリ構成（src/kabusys 以下の要約）
------------------------------------
- __init__.py
- config.py                 — 設定読み込み / Settings クラス（.env 自動ロード含む）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

パッケージ（主要なもの）
- ai/
  - news_nlp.py             — ニュースの OpenAI スコアリング
  - regime_detector.py      — レジーム判定（ETF MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite スキーマと DB ラッパー
  - system_monitor.py       — CPU/MEM/DISK、プロセス生存、データ鮮度監視
  - trade_monitor.py        — 注文ログ/滞留/約定異常の検出（該当ファイルあり）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — Kill Switch 実装
  - monitoring_engine.py    — 複数 Monitor を束ねる
  - alert_manager.py        — （アラート送信の統合地点）
- execution/
  - execution_engine.py     — 発注エンジン本体（EngineConfig 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py       — ブローカークライアント生成（Mock を含む）
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

トップレベル（プロジェクトルートの例）
- .env, .env.local
- config/ (system_config.yaml, strategy_config.yaml, ...)
- data/ (デフォルトの SQLite / PID / flag ファイル)
- logs/ (ログファイル)
- src/kabusys/...

運用上の注意
-------------
- KABUSYS_ENV を live にすると本番モードになります。LINE 通知や kill flag の扱い等を事前に確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup でも明記しています）。
- OpenAI や外部 API キーは安全に管理してください。
- paper_trading モードは本番 DB と完全に分離して動作するよう設計されています。PAPER_TRADING_SQLITE_PATH を確認してください。
- MONITOR_POLL_INTERVAL や LOG_LEVEL などは運用中に環境変数で調整できます。

補足（デバッグ・開発）
- 各モジュールはユニットテスト可能な設計（副作用最小化、純粋関数の利用）になっています。CI／ローカルで関数単位のテストを作成してください。
- .env 自動ロードを無効にしてテスト用に環境を制御する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

お問い合わせ・貢献
----------------
このドキュメントはソースコードの注釈に基づいて作成しています。実行時に不明点や不整合があれば Issue を立てるか、Pull Request を送ってください。