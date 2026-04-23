# KabuSys — 自動売買基盤（README）

このリポジトリは日本株向けの自動売買補助ライブラリおよび実行／監視スクリプト群です。  
以下はコードベース（src/kabusys/*.py）を元に作成した README です。

要点
- Python >= 3.10 を想定（型ヒントに | 演算子等を使用）
- DB: DuckDB（分析用）と SQLite（監視・注文ログ）
- AI 機能は OpenAI API（gpt-4o-mini 等）を利用（APIキー必須）
- 実行環境は KABUSYS_ENV 環境変数で切替（development / paper_trading / live）

1. プロジェクト概要
- KabuSys は日本株自動売買システムの基盤ライブラリ集合です。主な責務は以下。
  - データ処理・ファクター計算（research）
  - ポートフォリオ構築・ポジションサイズ計算（portfolio）
  - 実行エンジン起動スクリプト（run_execution）
  - 監視ループ（run_monitoring）と各種モニタ（system/trade/risk）
  - AI を使ったニュースセンチメント判定・レジーム判定（ai）
  - 環境設定ウィザード / 設定検証ツール（config_setup / validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
- ロギング・プロセス優先度・DB 初期化等の共通ユーティリティを内包。

2. 主な機能一覧
- Settings（kabusys.config）: 環境変数 / .env の読み込みと検証
- 環境ウィザード（kabusys.config_setup）: 対話式に .env を生成・更新
- 設定検証（kabusys.validate_config）: .env と config/*.yaml の整合チェック
- 実行エンジン起動スクリプト（run_execution）:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading.db に記録
  - プロセス優先度を高く設定して ExecutionEngine を起動
- 監視ループ（run_monitoring）:
  - SystemMonitor 等を定期ポーリングし監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境に依らず）
- Monitoring サブコンポーネント:
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度検査
  - TradeMonitor: 注文滞留・約定異常等の検出（trade_logs を参照）
  - RiskMonitor: ドローダウン監視、ポジション上限監視 / dashbord 保持
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止させる
  - AlertManager (抽象): 発報処理（LINE 等を想定）
- Portfolio モジュール:
  - 候補選定、等重・スコア重み算出、セクター制限、ポジションサイズ計算
- Research モジュール:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を用いる）
  - 将来リターン、IC（スピアマン）などの解析ユーティリティ
- AI モジュール:
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector: ma200 乖離 + マクロニュースで市場レジーム判定し保存
- Tools:
  - paper_verification_report: Paper Trading DB を解析し PASS/FAIL 判定でレポート出力

3. セットアップ手順（開発環境向け）
- 1) Python 環境を準備
  - 推奨: Python 3.10+
  - 仮想環境作成例:
    - python -m venv .venv
    - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- 2) 必要パッケージ（代表例）
  - pip install duckdb psutil openai PyYAML
  - 補足: sqlite3 は標準ライブラリ。プロジェクト固有の requirements.txt があればそちらを使用してください。
- 3) .env の初期作成
  - 対話式で作る（推奨）:
    - python -m kabusys.config_setup
  - もしくは手動で .env を作成（プロジェクトルートに配置）
  - 主要な環境変数（例）
    - JQUANTS_REFRESH_TOKEN=your_token_here
    - KABU_API_PASSWORD=your_password_here
    - KABU_API_BASE_URL=http://localhost:18080/kabusapi
    - DUCKDB_PATH=data/kabusys.duckdb
    - SQLITE_PATH=data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    - KABUSYS_ENV=development|paper_trading|live
    - LOG_LEVEL=INFO
    - OPENAI_API_KEY=sk-...  （AI 機能を使う場合）
- 4) 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit(1)）

4. 使い方（起動・運用例）
- ログディレクトリ
  - デフォルト: logs/
  - ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - LOG_DIR 環境変数で変更可
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します
- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB とは分離して動作
  - 実行中は data/execution.pid に PID を書き出す（ファイルパスは Settings.pid_file_path で変更可）
  - 停止: data/stop_requested.flag を作成する（run_execution が検知して engine.stop() を呼ぶ）
  - KillSwitch が動作すると data/kill.flag が書き込まれ、次回の起動阻止や外部通知が可能
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH
- AI 機能
  - news_nlp.score_news / regime_detector.score_regime を呼ぶには OpenAI API キーが必要（OPENAI_API_KEY）
  - API へのリクエストはバッチ化・リトライ実装あり（429/5xx 等）
- 停止・クリア操作
  - kill.flag の削除（Execution 起動時に自動クリア動作を無効にする設定もある）
    - デフォルトパス: data/kill.flag（Settings.kill_flag_path）
  - stop_requested.flag を作成/削除して実行中プロセスを制御
- 開発用ユーティリティ
  - MonitoringEngine.run_once を使えば各モニタを単発実行して挙動確認が可能（ユニットテストでの活用想定）

5. 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development, paper_trading, live）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必須）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 本番実行時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- LOG_DIR — ログ出力先ディレクトリ（優先順位: 引数 > 環境変数 > default logs/）

6. ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文監視: ファイル内に詳細実装あり）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor の集約とポーリングロジック
    - alert_manager.py       — （通知管理: 実装に応じて LINE 等へ通知）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動は run_execution）
    - order_manager.py
    - order_repository.py
    - broker_factory.py      — Broker クライアントの生成（paper_trading 用 Mock 等）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — レジーム判定
  - data/                   — 実行時生成データ（DB・フラグ・pid 等）
    - monitoring.db (default SQLITE_PATH)
    - kabusys.duckdb (default DUCKDB_PATH)
    - paper_trading.db
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - logs/                   — デフォルトのログ出力先（logs/<app>.log）

7. 運用上の注意
- DB 初期化:
  - run_execution / run_monitoring は起動時に monitoring DB の初期化（スキーマ作成・マイグレーション）を行います。
- paper_trading:
  - 本番 DB と完全に分離されるよう、paper_trading 用 SQLite を別ファイルにしてください（PAPER_TRADING_SQLITE_PATH）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を実行します。psutil の権限や OS により設定できない場合があります（警告が出ますが処理は継続します）。
- Kill Switch:
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨します。自動クリアを許すと誤って Kill を無効化してしまう危険があります。
- AI 呼び出し:
  - OpenAI の使用は API 費用が発生します。レスポンスの妥当性検証・スコアクリップが入っていますが、実運用ではコスト・品質面の検討が必要です。
- 権限:
  - ログディレクトリや data/ 配下への書き込み権限をアプリケーション用実行ユーザーに与えてください。
- 監視の DB 使用:
  - monitoring は run_monitoring が本番 sqlite_path を使って監視情報を永続化します。paper_trading でも monitoring 自体は本番 sqlite_path を参照する設計になっています（run_monitoring ソース参照）。

8. 開発者向けメモ
- 単体関数群は副作用を持たない（pure）設計のものが多く、ユニットテストがしやすい構造です（例: portfolio/*, research/*）。
- DuckDB 接続を渡して SQL を実行する形でファクター計算を行うため、テスト用の DuckDB を用意して固定データで検証すると良いです。
- OpenAI まわりは _call_openai_api を patch してテスト可能。

9. よく使うコマンド例
- .env を作成:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上が本コードベースの概要と利用手順のまとめです。実運用の前に必ず python -m kabusys.validate_config で設定検証を行い、.env に機密情報を含めたままリポジトリへコミットしないでください。