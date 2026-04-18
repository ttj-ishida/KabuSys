KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。  
戦略の研究／ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、そして AI を使ったニュース評価などの機能を含みます。

主な特徴
--------
- ポートフォリオ構築
  - シグナルから候補選定（スコア順、上位N）
  - 等金額・スコア加重配分
  - リスクベースの株数算出（単元株丸め、aggregate cap 調整）
  - セクター集中制限適用、レジームに応じた乗数適用
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で算出
  - 将来リターン計算、IC（Spearman）や統計サマリ
- 発注関連（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モード時は MockBroker と専用 SQLite（data/paper_trading.db）を使用し本番 DB と分離
  - リスク管理（ポジション上限、ドローダウン等）
- 監視（Monitoring）
  - System / Trade / Risk 各種モニタと集約エンジン
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止）
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL で間隔上書き可）
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 想定）でニュースをセンチメント評価し ai_scores に格納
  - マクロニュース + ETF MA200 による市場レジーム判定
- ユーティリティ
  - .env 対話式生成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- ロギング
  - 統一的なログ設定ユーティリティ（TimedRotatingFileHandler + stdout）

クイックセットアップ
-------------------
※ 以下は開発マシン向けの一般的な手順です。環境依存の調整は適宜行ってください。

1. Python（3.10+ 推奨）仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）PyYAML があれば config YAML の検証が行えます: pip install pyyaml

   ※ requirements.txt が無い場合は上記を参考にインストールしてください。

3. .env ファイルの作成（対話式）
   - python -m kabusys.config_setup
   - 生成された .env を必ず Git にコミットしないでください

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗として扱います: python -m kabusys.validate_config --strict

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト development
  - paper_trading: MockBroker を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

主要なコマンド・使い方
-------------------

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 失敗時は exit code が 1 を返します

- 監視ループの起動（常時プロセス）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に「本番」sqlite_path（Settings.sqlite_path）を使用します

- ExecutionEngine（発注エンジン）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker（paper DB に記録）
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中は data/execution.pid に PID を書きます（設定で変更可）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI モジュール（ニューススコア / レジーム判定）
  - kabusys.ai.score_news および kabusys.ai.regime_detector.score_regime をプログラムから呼ぶ
  - OpenAI API キーが必要（OPENAI_API_KEY）

停止方法・フラグ運用
-------------------
- run_monitoring と run_execution はプロジェクトの data ディレクトリに存在するフラグファイルを参照します。
  - data/stop_requested.flag: これが存在するとループ／実行スレッドは停止または起動をスキップします
  - Kill Switch は条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine はこの kill.flag を監視して停止します。
- kill.flag を自動クリアするかは KILL_FLAG_CLEAR_ON_START 環境変数で制御します（本番では 0 推奨）。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging を通じて設定されます。
- デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30 日保持）へ出力します。
- LOG_DIR 環境変数または setup_logging の引数でログ保存先を変更できます。

データベース（デフォルトパス）
---------------------------
- DuckDB: data/kabusys.duckdb
- Monitoring (SQLite): data/monitoring.db
- Paper trading (SQLite): data/paper_trading.db

モジュール概要 / ディレクトリ構成
------------------------------
以下は主要ファイル・ディレクトリの簡易構成（src/kabusys 以下）です。

- run_monitoring.py
  - SystemMonitor を起動して監視ループを回すスクリプト
  - MONITOR_POLL_INTERVAL で間隔変更可能
- run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading では MockBroker を使い paper DB に記録

- config.py
  - Settings クラス：.env / 環境変数から各種設定を読み出す
  - 自動 .env 読み込みロジックを含む（プロジェクトルート検出）

- config_setup.py
  - .env 初期作成・更新の対話式ウィザード

- validate_config.py
  - .env と config/*.yaml の検証 CLI

- utils/
  - logging_setup.py : 共通ログ設定
  - process_priority.py : プロセス優先度 / CPU affinity ヘルパ
  - （他ユーティリティ）

- monitoring/
  - monitoring_db.py : 監視用 SQLite のスキーマ・永続化 API（MonitoringDB）
  - system_monitor.py : システム状態・データ鮮度チェック
  - trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py, monitoring_engine.py など（監視ロジック群）

- execution/
  - ExecutionEngine 関連、ブローカーファクトリ、OrderManager, RiskManager, Reconciler 等（発注ロジック）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 銘柄選定・重み・株数算出・セクター制限など

- research/
  - factor_research.py : Momentum, Volatility, Value 等のファクター算出（DuckDB）
  - feature_exploration.py : 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py : ニュース記事を OpenAI で評価し ai_scores に書き込む
  - regime_detector.py : MA200 + マクロニュースでレジーム判定

- tools/
  - paper_verification_report.py : Paper Trading の検証レポート出力

- data/
  - 実行時に利用するフラグ・DB等（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/kill.flag 等）

設計上の注意点 / 運用上のポイント
--------------------------------
- paper_trading モードは本番 DB と完全に分離する設計です。KABUSYS_ENV=paper_trading の設定を確実に行ってください。
- AI（OpenAI）を利用する処理は API コスト・レイテンシ・エラー耐性を設計に組み込んでいますが、API キー管理には注意してください（OPENAI_API_KEY）。
- run_* スクリプトはプロセス優先度を上げる処理（psutil）を行います。権限不足の環境では警告を出してスキップします。
- 監視・Kill Switch は運用保護機能です。KILL_FLAG_CLEAR_ON_START を本番で 1 にしないことを推奨します（誤った自動クリアは危険）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。

最後に
------
この README はコードベースの重要点をまとめたものです。各モジュールの詳細な使い方はソース内 docstring（関数・クラスの説明）を参照してください。導入や実行時に不明点があれば、具体的なエラーや期待する振る舞いを添えて質問してください。