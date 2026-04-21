KabuSys — 日本株自動売買システム（簡易 README）
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を提供します。

- 注文実行エンジン（本番 / ペーパートレード切替）
- 監視（システム状態・注文状況・リスク監視・Kill Switch）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助機能（ニュース NLP によるセンチメントスコア、レジーム判定）
- 各種 CLI ツール（.env ウィザード、設定検証、検証レポート生成 等）

主な特徴
--------
- 実行環境切替（KABUSYS_ENV = development | paper_trading | live）
  - paper_trading モードでは MockBroker を使用し、本番 DB と完全分離された data/paper_trading.db を使用する
- 監視プロセスは環境に関係なく本番 monitoring DB（デフォルト data/monitoring.db）を用いる（監視の一貫性保持）
- DuckDB を用いた分析用データレイク（デフォルト data/kabusys.duckdb）
- OpenAI（gpt-4o-mini）を使ったニュース NLP / マクロ判定（API キー必須）
- ログは標準出力と日次ローテーションログ（logs/<app>.log）に出力
- プロセス優先度・CPU affinity を OS に配慮して設定（psutil 利用）

セットアップ手順
----------------
前提
- Python 3.10 以上（型ヒントに | を使用）
- システムに pip が使えること

1. リポジトリをクローン
   - git clone ...（本リポジトリをクローン）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）PyYAML をインストールすると設定検証時に config/*.yaml のパース検査が有効になる:
     - pip install pyyaml

4. 初期設定（.env の生成）
   - python -m kabusys.config_setup
     - 対話形式のウィザードで .env を生成します（.env は絶対に Git にコミットしないでください）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. ディレクトリ準備（手動で必要な場合）
   - data/ や logs/ は自動で作成されますが、アクセス権等で失敗する場合は手動で作成してください。

主要環境変数（主なもの）
-----------------------
以下は本プロジェクトで使用される主な環境変数（.env で設定可能、括弧内はデフォルト値や説明）。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db) — 監視 DB（monitoring はこの DB を常に参照）
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — paper_trading 用 DB
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — デフォルト: instant
- LOG_LEVEL ("DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL") — デフォルト: INFO
- LOG_DIR (logs/)
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でアラート通知を行う場合
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0|1) — 1 にすると起動時に kill flag を自動クリア（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（実行例）
----------------

1) 実行エンジン（ExecutionEngine）
- 本番またはペーパートレードで注文実行を行うメインモジュール:
  - python -m kabusys.run_execution
  - 仕様:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用しデータは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録される
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了する
    - 実行中は data/execution.pid に PID を書き込む（pid ファイルパスは Settings で変更可能）
    - 停止は data/stop_requested.flag を作ることで可能

2) 監視プロセス（SystemMonitor をポーリング）
- センサー類（CPU、メモリ、ディスク、データ鮮度）やトレード・リスク監視を行う:
  - python -m kabusys.run_monitoring
  - 仕様:
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使う
    - 停止はプロジェクトルート/data/stop_requested.flag を作成
    - ログは logs/monitoring.log に日次ローテートで出力

3) .env ウィザード（対話式）
- python -m kabusys.config_setup

4) 設定検証 CLI
- python -m kabusys.validate_config
- --strict を付けると警告も FAIL 扱いで exit(1)

5) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH （指定がない場合は PAPER_TRADING_SQLITE_PATH 環境変数、未設定なら data/paper_trading.db を使用）

6) AI（ニュース NLP / レジーム判定）
- これらの機能は OpenAI API を使用します。事前に OPENAI_API_KEY を .env に設定してください。
- ニュース NLP（ai.score_news）は duckdb 接続と target_date を受ける関数インターフェースです（CLI 実装は無し）。同様に regime_detector.score_regime も関数呼び出しで利用します。

停止・Kill Switch
----------------
- ExecutionEngine の即時停止要請:
  - data/kill.flag に理由文字列を書き込む（KillSwitch が存在を検知して ExecutionEngine を停止する）
- 監視・実行プログラムの通常停止（安全にループを終了）:
  - data/stop_requested.flag を作成（run_execution/run_monitoring はこのファイルを検知して終了）

ログ
---
- デフォルトではコンソール（stdout）と logs/<app>.log（日次ローテーション）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出しています。
- LOG_DIR 環境変数でログディレクトリを上書き可能。

開発者向けメモ / 実装上のポイント
--------------------------------
- 環境変数の自動読み込み:
  - src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env と .env.local を自動ロードします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB
  - DuckDB は分析用（prices_daily, raw_financials など）。パイプラインでデータを投入して利用します。
  - monitoring 用の SQLite（monitoring_db）には system_status, trade_logs, positions, risk_logs, dashboard 等のテーブルがあり、init_monitoring_db で自動作成・マイグレーションされます。
- 依存ライブラリ
  - duckdb, psutil, openai は主要な依存です。PyYAML は validate_config の追加検査にのみ必要です。
- Python バージョン
  - 型ヒントに新しい構文（X | Y）を使用しているため Python 3.10 以上を推奨します。

主要なディレクトリ構成
--------------------
（プロジェクトルートの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（init / MonitoringDB クラス）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文関連監視（存在）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の書き込み / 評価
    - monitoring_engine.py   — 複数モニタの統合ループ
    - alert_manager.py       — アラート管理（存在）
  - execution/               — 実行エンジン / ブローカー / 注文管理（主要ロジック）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 連携）
    - regime_detector.py     — マーケットレジーム判定（OpenAI 連携）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

よくある質問 / トラブルシューティング
-------------------------------------
Q: OpenAI を使わないで起動できますか？
A: はい。AI 機能を使わない限り OPENAI_API_KEY は不要です。AI を呼ぶ関数は API キー未設定時に ValueError を出します。

Q: ログディレクトリ作成に失敗したら？
A: 権限などで作成できない場合、コンソール出力のみの動作になります。必要に応じて LOG_DIR を書き込み可能な場所に変更してください。

Q: 監視はどの DB を書き換えますか？
A: 監視は設定に基づく sqlite_path（デフォルト data/monitoring.db）を使い、system_status 等を記録します。run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使います。

貢献・拡張
----------
- strategy / execution ロジックやブローカープラグインを追加することで実運用向けに拡張できます。
- ニュース NLP のプロンプトやバッチ戦略、LLM エラーハンドリングは現状の設計をベースに改善可能です。
- tests ディレクトリや CI を整備してユニットテスト／統合テストを追加してください。

---

必要であれば、README にサンプル .env（例示、機密情報は除く）や起動スクリプト systemd / supervisor 用のサービス定義のテンプレート、さらに詳しいディレクトリツリー（file tree）を追加します。どれを追加しますか？