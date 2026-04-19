KabuSys
=======

日本株向け自動売買システムのコアライブラリ群と起動スクリプトをまとめたリポジトリです。
このREADME はリポジトリ内の主要モジュール（実行エンジン / 監視 / ポートフォリオ構築 / 研究 / AI 等）の概要、
セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
--------------
KabuSys は日本株の自動売買プラットフォーム向けライブラリ兼起動スクリプト群です。主な役割は以下の通りです。

- ExecutionEngine（注文発行・リスク管理・約定管理）を起動してトレードを実行
- Monitoring（システム状態・注文・リスク監視）で稼働状況を記録・アラート・Kill Switch を制御
- Portfolio construction（銘柄選定、配分、ポジションサイズ計算）の関数群
- Research（ファクター計算・特徴量解析）機能（DuckDB を用いた時系列処理）
- AI 支援機能（ニュースの NLP スコア付与、レジーム判定）――OpenAI API 利用
- 各種ユーティリティ（環境設定ウィザード、設定検証、ログセットアップ 等）
- ペーパートレード専用 DB と検証レポート生成ツール

機能一覧
--------
主要な機能（抜粋）：

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードを切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 環境設定・検証
  - config_setup.py: 対話式ウィザードで .env を作成／更新
  - validate_config.py: .env と config/*.yaml の存在／整合性チェック（--strict あり）
- 監視
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py
  - monitoring_db.py: SQLite ベースの監視ログ永続化層
  - kill.flag による ExecutionEngine 停止（Kill Switch）
- ポートフォリオ構築
  - portfolio_builder、position_sizing、risk_adjustment（等金額・スコア加重・リスクベース等）
- リサーチ / 特徴量
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン、IC、統計サマリー
- AI（OpenAI）
  - news_nlp.py: ニュース記事をまとめて LLM に投げ、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.py: ETF の MA とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - tools.paper_verification_report.py: Paper Trading DB から検証レポートを生成

セットアップ手順
---------------
前提
- Python 3.10 以上（ソース内で | 型注釈を使用しているため）
- DuckDB / SQLite / psutil 等の Python パッケージ
- OpenAI 機能を使う場合は OpenAI API キー

推奨手順（ローカル開発環境）
1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - pyyaml（config YAML の検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を使ってください）

3. .env の作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - オプション / 重要変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL, LOG_DIR, OPENAI_API_KEY (AI 機能用)
   - .env は Git にコミットしないでください（ウィザードは .env を生成時に警告します）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

使い方
------
一般的な起動方法（本番・開発共通の例）：

1. 監視ループの起動
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
   - 起動:
     - python -m kabusys.run_monitoring
   - 監視は .env の KABUSYS_ENV に依らず production の sqlite_path を使用してログを永続化します。
   - 停止: data/stop_requested.flag を作成するか Ctrl+C

2. 実行エンジン（ExecutionEngine）の起動
   - KABUSYS_ENV による挙動:
     - paper_trading: MockBrokerClient を使用し、デフォルトで data/paper_trading.db に書き込む（本番 DB と分離）
     - live: 実ブローカーに接続して発注
   - 起動:
     - python -m kabusys.run_execution
   - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
   - stop の指示は監視コンポーネントが data/kill.flag を書くことで行われ、run_execution はその存在を検知して engine.stop() を呼びます。

3. Paper Trading の検証レポート生成
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
   - 使い方:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - python -m kabusys.tools.paper_verification_report --db /path/to/db.sqlite

4. AI 機能
   - OpenAI API を利用する機能（ニュース NLP / レジーム判定）は OPENAI_API_KEY を設定するか、関数に api_key を渡してください。
   - 公開 API は以下を提供:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

環境変数とファイル
- 重要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV (development | paper_trading | live) — 実行モード切替
  - OPENAI_API_KEY — OpenAI 利用時に必要
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH — DB ファイルパス
  - LOG_LEVEL, LOG_DIR — ログ設定
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（run_monitoring 用）
- 制御ファイル
  - data/kill.flag — Kill Switch（監視が条件を満たすとこのファイルを作成）
  - data/stop_requested.flag — 外部から監視・実行を停止するためのフラグ
  - data/execution.pid — ExecutionEngine の PID 保持（run_execution が利用）

ログ
- kabusys.utils.logging_setup.setup_logging を各スクリプトで使用しており、
  stdout に出力すると同時に logs/<app_name>.log に日次ローテーションで保管します（既定: logs/）。

ディレクトリ構成
----------------
以下はソースツリー（主要ファイル）の抜粋です。実際は src/kabusys 以下に配置されています。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - system_monitor.py        — システム状態・データ鮮度監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - trade_monitor.py         — (存在想定) 注文関連監視
    - kill_switch.py           — kill.flag の作成・評価
    - alert_manager.py         — (存在想定) アラート送信ロジック
  - portfolio/
    - portfolio_builder.py     — 銘柄選定・スコアソート
    - position_sizing.py       — 株数計算・スケールダウンロジック
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py   — forward returns / IC / 統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度・CPU affinity 設定
    - __init__.py
  - (その他)
    - execution/               — ExecutionEngine 本体・OrderManager 等（インポート参照あり）
    - data/                    — データパイプライン / stats など（インポート参照あり）

注意事項 / 運用上のポイント
--------------------------
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- validate_config.py による事前チェックを行うと、本番誤設定を減らせます（--strict モード推奨）。
- run_monitoring は監視用 DB を利用して稼働率やエラーを記録します。MONITOR_POLL_INTERVAL で間隔調整可。
- run_execution は paper_trading モード時に本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使うため
  テスト・検証に便利です。
- AI 機能（OpenAI）利用時は API 呼び出しに失敗する可能性があるため、コード内で再試行・フェイルセーフ処理が組まれていますが、
  実運用では API キー管理とコストに注意してください。
- process_priority.set_process_priority を最初に呼んでおり、アクセス権限により設定に失敗する場合があります（警告ログのみ）。

開発・拡張
-----------
- 新しいモニタリングルールやアラートは monitoring_engine に組み込むことで統合的に動作します。
- DuckDB を利用した研究モジュールは prices_daily / raw_financials 等のテーブルスキーマに依存します。データパイプライン側でスキーマを満たしてください。
- ポートフォリオ構築関数群は純粋関数設計（副作用なし）なのでユニットテストしやすくなっています。

問い合わせ・貢献
----------------
- バグ報告や機能追加提案は GitHub Issue を立ててください。
- コントリビュートする際はテスト、静的解析、設定検証を行うことを推奨します。

以上。必要であれば README にデプロイ手順（systemd ユニット例や Dockerfile、CI/CD 設定など）を追加で記述します。どの項目を詳しく追記するか教えてください。