KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システム（プロトタイプ）です。  
本 README は、コードベース（src/kabusys）を元にした概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は以下を提供します。

- 注文実行エンジン（ExecutionEngine）とその起動スクリプト
- システム監視（Monitoring）コンポーネントと監視ループ
- リスク監視（ドローダウン／ポジション上限等）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI を使ったニュース NLP（OpenAI）連携（ニュースセンチメントのスコア付与）
- ペーパートレード用の検証レポート生成ツール

設計上の特徴：
- 設定は .env ファイル / 環境変数で管理（自動ロード機能あり）
- SQLite（監視 DB / paper trading DB）と DuckDB（分析用）を併用
- ログはコンソール + 日次ローテーションファイルに出力
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を切替可能

主な機能一覧
-------------
- 実行エンジン起動: src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading のとき MockBrokerClient を使用し paper_trading DB に記録
  - 停止指示は data/stop_requested.flag（起動前チェック）や data/kill.flag（Kill Switch）で行う
- 監視ループ起動: src/kabusys/run_monitoring.py
  - システム状態や各種モニターを定期実行してログ・アラート・Kill Switch を評価
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 設定ウィザード: src/kabusys/config_setup.py
  - 対話式で .env を作成 / 更新
- 設定検証 CLI: src/kabusys/validate_config.py
  - .env と config/*.yaml の有無や簡易チェックを実行。--strict で警告もエラー扱い
- Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
  - ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計し PASS/FAIL 判定
- AI（ニュース NLP / レジーム判定）: src/kabusys/ai/*
  - news_nlp.score_news()：OpenAI によるニュースセンチメントを ai_scores に書込
  - regime_detector.score_regime()：ETF MA とマクロ NLP を合成して市場レジーム判定
- ポートフォリオ構築: src/kabusys/portfolio/*
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター上限適用、レジーム乗数等
- 研究用: src/kabusys/research/*
  - ファクター計算（momentum/volatility/value）、将来リターン、IC 計算、統計サマリー
- ユーティリティ:
  - ロギング設定: kabusys.utils.logging_setup.setup_logging()
  - プロセス優先度 / CPU affinity: kabusys.utils.process_priority

セットアップ手順
----------------
1. リポジトリをクローンして、必要パッケージをインストールします（仮想環境推奨）。

   必要な Python パッケージ（代表例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML の構文チェック用。ただし必須ではない）
   - （テスト / 開発に応じて追加）

   例:
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt が無い場合は上記を目安にインストールしてください。

2. .env ファイルを作成する（対話式ウィザード推奨）:

   - 対話式で作る:
     python -m kabusys.config_setup

   - 手動の最小例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

   注意: .env は Git にコミットしないでください（シークレット情報を含む）。

3. 設定検証:

   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い

4. データディレクトリの作成（必要に応じて）:
   デフォルトでは data/ 以下に SQLite や PID/フラグファイルを置きます。必要に応じて作成してください。
   ログは logs/ に出力されます（自動で作成されますが権限に注意）。

基本的な使い方
--------------
起動スクリプト（モジュール実行）:

- 実行エンジン起動
  - 本番/ペーパーは KABUSYS_ENV に依存
  - 起動:
    python -m kabusys.run_execution
  - 停止方法:
    - run_execution は data/stop_requested.flag を監視しています。停止させるには stop_requested.flag を作成（または実行中にプロセスへ SIGINT）。
    - Kill Switch（監視で発動する場合）は data/kill.flag を書き込み、ExecutionEngine が検出して停止します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path から参照）

- 監視ループ起動
  - 起動:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照する実装）

- Paper Trading 検証レポート（ローカル実行）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / レジーム判定（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None)  # conn は DuckDB connection
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは環境変数 OPENAI_API_KEY または引数で渡してください。

重要な環境変数（抜粋）
-------------------
- 必須（最低限）:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 運用 / パス:
  - KABUSYS_ENV — execution 環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
  - OPENAI_API_KEY — OpenAI API キー（AI 関連）

- 自動ロード制御:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

ログとファイル
---------------
- ロギング:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30 日保持）
  - コンソール出力は stdout（stderr ではない）

- フラグ / PID:
  - data/stop_requested.flag — 起動前チェック / 実行中ループでの停止検出に使用
  - data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine が参照）
  - data/execution.pid — ExecutionEngine の PID ファイル（設定可能）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下のおおまかな構成です（主要ファイルのみ抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるセンチメント取得
    - regime_detector.py      — レジーム判定（ETF MA + マクロ NLP）

  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（テーブル作成 / CRUD）
    - system_monitor.py       — システム監視（CPU/MEM/DISK / データ鮮度 / プロセス稼働）
    - trade_monitor.py        — 注文 / 約定の監視（滞留・異常約定検出）※実装ファイルあり
    - risk_monitor.py         — ドローダウン / ポジション上限の監視
    - kill_switch.py          — Kill Switch ロジック（flag 書込）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — 通知管理（LINE 等への送信用ラッパー）※実装ファイルあり

  - execution/
    - execution_engine.py     — ExecutionEngine の本体（スレッド実行など）※実装ファイルあり
    - broker_factory.py       — ブローカークライアント生成（本番 / mock）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文履歴保存ロジック
    - reconciler.py           — ブローカーとの状態整合処理
    - risk_manager.py         — 発注前リスク評価

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数計算
    - risk_adjustment.py      — セクター制限・レジーム乗数

  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ

  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成ツール

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度・CPU affinity 設定ユーティリティ

運用上の注意 / ヒント
--------------------
- 本番環境では KABUSYS_ENV=live を設定する前に validate_config.py で確認してください。
- .env は機密情報を含むため絶対に Git に含めないでください（config_setup も README に明記）。
- OpenAI を使用する機能は API コスト・レート制限が発生します。API キー管理に注意してください。
- run_monitoring は監視用 DB（Settings.sqlite_path）を参照します。監視は本番 DB を用いる設計になっています。
- MONITOR_POLL_INTERVAL の値に 0 以下を指定すると無効扱いになりデフォルト（60秒）にフォールバックします。
- process_priority は OS によっては権限不足で設定に失敗することがあります（警告ログが出ます）。

参考コマンド一覧
----------------
- .env 作成（対話式）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視ループ起動（ポーリング間隔 30 秒で起動）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper trading レポート（期間指定）:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

その他
-----
- この README はソースコードの実装に基づく簡易ドキュメントです。各モジュールの詳細な使い方は該当ファイルの docstring / コメントを参照してください。
- 追加で README に記載したい実行例、依存関係ファイル（requirements.txt）、デプロイ手順や systemd / cron 用のサンプルユニットファイル等が必要であれば教えてください。