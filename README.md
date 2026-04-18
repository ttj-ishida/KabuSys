README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを提供します。設計方針として「本番コードとリサーチ/分析コードの分離」「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」を重視しています。

主な機能
--------
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント（本番 / paper_trading 用のモック分離）
  - 注文管理、リスク管理、再整合（reconciler）などの実装（エンジン内部は別モジュール）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化する monitoring_db（system_status, trade_logs, positions, risk_logs, dashboard）
  - Kill Switch （条件により data/kill.flag を書き込み ExecutionEngine を停止）
  - run_monitoring.py によるポーリングループ起動
- ポートフォリオ構築
  - 候補選定、重み計算（等分配 / スコア加重）
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（単元丸め、aggregate cap、risk-based 配分）
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB を用いた高速な時系列集計
- AI（OpenAI ベース）
  - ニュースを LLM（gpt-4o-mini）でセンチメント化して ai_scores に保存（news_nlp）
  - マクロニュース + ETF MA200 を合成して市場レジーム判定（regime_detector）
  - API 呼び出しはリトライやフォールバックを備えフェイルセーフに実装
- ツール
  - .env 対話式作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - 統一的なログ設定（utils/logging_setup.py）: stdout + 日次ローテーションファイル
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - 環境変数管理（config.py）: .env 自動読込や Settings 抽象化

セットアップ手順
--------------
前提:
- Python 3.9+ を想定（プロジェクトの pyproject.toml を参照してください）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
これらは requirements.txt がある場合はそれを使用してください。ない場合は手動でインストールします:

例:
- pip install duckdb psutil openai pyyaml

1. リポジトリをクローン / ソース配置
2. 仮想環境を作成して依存パッケージをインストール
3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成してプロジェクトルートに置く
4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / フラグパス:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db (paper_trading 用)
     - data/execution.pid
     - data/kill.flag / data/stop_requested.flag
   - ログディレクトリ: logs/

重要な環境変数 (主なもの)
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading: MockBrokerClient を使用し paper_trading.db に記録（本番 DB と分離）
- OPENAI_API_KEY: AI 機能を使う場合に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — 監視 DB（monitoring は env に関係なく本番 sqlite_path を使用します）
- PAPER_TRADING_SQLITE_PATH（paper_trading 使用時の DB パス）
- LOG_LEVEL（例: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒; デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（1 にすると ExecutionEngine 起動時に kill.flag を自動クリア）

使い方
------
起動スクリプト
- 監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によってポーリング間隔を上書き可能（秒）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します
- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い paper_trading 用 DB に記録します
  - 停止: data/stop_requested.flag を作成するとエンジンに停止シグナルを送ります

設定周り
- .env を作成 / 更新:
  - python -m kabusys.config_setup
- 確認:
  - python -m kabusys.validate_config [--strict]

ツール
- Paper Trading の検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH もしくは環境変数 PAPER_TRADING_SQLITE_PATH を使用

AI 機能
- ニュース NLP（score_news）やレジーム判定（score_regime）は OpenAI API を利用します。実行には OPENAI_API_KEY 設定が必要です。
- API 呼び出しはリトライ・バックオフを持ち、失敗時は安全なフォールバック（ゼロスコア等）で継続する実装です。

停止 / Kill Switch
- KillSwitch は risk チェック等の条件を満たした場合に data/kill.flag を作成し、ExecutionEngine 停止のトリガーになります。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番では推奨されません）。

ログ
- 共通ログ設定を使用:
  - stdout（コンソール）に出力する StreamHandler
  - 日次ローテーションファイル logs/<app_name>.log（30 日保持）
- LOG_DIR 環境変数でログディレクトリを指定可能

ディレクトリ構成
----------------
以下は src/kabusys 以下の主なファイル・モジュール構成（抜粋）です:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読込）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py           — SQLite 監視テーブル作成 / 永続化 API
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — （省略: トレード監視 logic）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - kill_switch.py             — Kill Switch 実装
    - alert_manager.py           — （省略: 通知管理）
  - execution/
    - execution_engine.py        — 実行エンジン（EngineConfig, run_session 等）
    - order_manager.py           — 注文管理
    - order_repository.py        — 注文 DB 層
    - reconciler.py              — オンライン再整合
    - broker_factory.py          — ブローカークライアント生成
    - risk_manager.py            — リスク管理（RiskConfig）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・丸め・aggregate cap
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - factor_research.py         — Momentum / Value / Volatility 計算
    - feature_exploration.py     — 将来リターン, IC, 統計サマリー
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py         — レジーム判定（ETF + マクロセンチメント）
  - data/                        — 実行時に生成される想定のパス（DB / PID / flags）
  - logs/                        — ログ出力先（デフォルト）

補足と注意事項
--------------
- monitoring_db.init_monitoring_db は冪等でテーブル・インデックスを作成し、マイグレーション（カラム追加）も含みます。
- Settings クラスは .env / 環境変数を読み取り、値検証（有効値チェック）を行います。不足時は例外を送出します。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を調整できます。1未満や不正値はデフォルト 60 秒にフォールバックします。
- ExecutionEngine と Monitoring は停止フラグ（data/stop_requested.flag）を監視して安全に終了します。
- OpenAI を使う機能は API の課金対象になります。テスト時はモック化（unittest.mock.patch）を想定した設計です。

ライセンス / バージョン
------------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報や貢献方法はリポジトリのトップレベル LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
----------
使い方や拡張に関しては該当モジュールの docstring を参照してください。特定の機能についての解説や README の補足が必要であれば教えてください。