KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
主な目的は次のとおりです。

- 発注エンジン（ExecutionEngine）による売買実行（本番 / ペーパートレード対応）
- 監視サブシステム（System/Trade/Risk）による稼働・リスク監視と Kill Switch
- ポートフォリオ構築、ポジションサイジング、セクター制約などの純粋関数群
- DuckDB を使ったリサーチ／ファクター計算モジュール
- OpenAI を用いたニュース NLP / レジーム判定（任意）
- 検証ツール（Paper Trading レポート生成）や設定ウィザード／検証 CLI

主な特徴
--------
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）実行モードをサポート
- .env を使った設定管理（自動ロード / 対話式ウィザードあり）
- SQLite（監視・注文ログ） + DuckDB（分析）を併用
- 監視ループ（monitoring）によりプロセス死活・データ鮮度・リスクを監視し、Kill Switch を発動可能
- AI モジュールは OpenAI（gpt-4o-mini 等）を利用した安全策つきのバッチ処理実装
- 純粋関数として設計されたポートフォリオ／リスクロジック（テストしやすい）

セットアップ（ローカル開発向け）
-------------------------------
前提
- Python 3.10+
- git, などの基本ツール

推奨パッケージ（最低限）
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（config YAML 検証を使う場合）
- そのほか依存があれば requirements.txt を用意している場合はそれを利用してください。

手順（例）
1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を準備
   - 対話式で .env を作る: python -m kabusys.config_setup
   - あるいは .env を手動作成（下記の「.env の主要項目」を参照）
5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

主要な環境変数（.env の例）
--------------------------
最小で必須なのは次の2つです:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
- KABU_API_PASSWORD=your_kabu_api_password_here

よく使う項目（デフォルト値は括弧内）
- KABUSYS_ENV=development | paper_trading | live (development)
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- OPENAI_API_KEY=（AI 機能で必要）
- KILL_FLAG_CLEAR_ON_START=0（起動時に kill.flag を自動クリアするか）
- MONITOR_POLL_INTERVAL=60（監視ループの秒間隔、run_monitoring で参照）

自動ロードの挙動
- 起動時にプロジェクトルート（.git / pyproject.toml を探索）を基に .env を自動ロードします。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要スクリプト）
-----------------------

設定関連
- 対話式 .env 作成・更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

実行エンジン（Execution）
- 起動:
  - python -m kabusys.run_execution
  説明:
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 実行中は data/execution.pid を作成します。
  - 停止は data/stop_requested.flag を作成するか（monitoring サブシステム経由で kill.flag を書く）、プロセスにシグナルを送ることで行います。

監視ループ（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
  説明:
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、必要に応じて Kill Switch を書き込み（data/kill.flag）ます。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化します。

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI / リサーチ機能（任意）
- ニュース NLP スコアリング:
  - kabusys.ai.score_news を呼び出して raw_news を解析し ai_scores を更新します。
  - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。
- 市場レジーム判定:
  - kabusys.ai.regime_detector.score_regime を呼び出して market_regime に書き込み。
- ファクター計算 / リサーチ:
  - kabusys.research モジュール (calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary 等)

停止と Kill フラグ
- 手動停止（Execution 停止）:
  - data/stop_requested.flag を作成すると run_execution のループが終了します。
- Kill Switch:
  - monitoring がリスク条件を検出すると data/kill.flag を書き込みます。ExecutionEngine は起動時や稼働中に kill.flag の存在を検知して停止します。
- kill.flag の自動クリア:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では推奨しません）。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます。
- デフォルトログディレクトリ: logs/
- 各アプリケーション（execution / monitoring など）ごとに logs/<app_name>.log に日次ローテーションで出力されます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                — .env / 環境変数読み込み・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動ラッパー
- run_monitoring.py        — SystemMonitor ポーリング起動ラッパー

サブパッケージ（主なモジュール）
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py        — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — (存在する場合) 注文系監視ロジック
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag の書き込み/監視ユーティリティ
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        —（アラート送信管理、LINE 連携等を想定）
- execution/
  - execution_engine.py     — ExecutionEngine（発注セッションの本体）
  - broker_factory.py       — BrokerClient のファクトリ（Mock / 実ブローカ）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 発注株数計算・資金制約
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum/value/volatility）
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

注意事項 / 運用上のヒント
------------------------
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリアを無効にし、LINE などで通知設定を整えてください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- OpenAI API 呼び出しはコストとレート制限があります。AI 機能を運用する場合はバッチ頻度・バッチサイズを調整してください。
- DuckDB / SQLite のファイルパスは .env で変更できます。バックアップ・保持ポリシーを検討してください。
- ログディレクトリ作成に失敗した場合はコンソール出力にフォールバックします。起動ユーザーのファイル作成権限を確認してください。

貢献
----
バグ報告・改善提案は Issue を立ててください。設計原則として「純粋関数」「副作用を限定」「ルックアヘッドバイアス排除」を重視しています。テストやドキュメントの追加貢献を歓迎します。

付録：よく使うコマンド一覧
-------------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。README に不足している具体的な運用手順や systemd / container 化のサンプルが必要であれば次に示してください。