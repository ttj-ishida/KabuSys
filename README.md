# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントはコードベースに含まれる主要な起動スクリプト・設定フロー・ユーティリティの使い方をまとめたものです。

注意: 実行には外部 API キー（J-Quants / kabuステーション / OpenAI など）が必要です。開発・本番を問わず設定を慎重に扱ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の機能群を含むモジュール化されたシステムです。

- 戦略（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定・配分・株数決定）
- 実行エンジン（発注・リスク管理・注文管理）
- 監視（プロセス稼働・データ鮮度・リスク監視）
- AI モジュール（ニュースセンチメント、レジーム判定）
- ペーパートレーディング検証・レポート生成
- 環境設定ウィザード / 設定検証ツール

設計方針として、データベース（DuckDB / SQLite）とファイルフラグでプロセス制御・状態永続化を行い、外部 API 呼び出しは明示的に分離してフェイルセーフにしています。

---

## 主な機能一覧

- 環境設定ウィザード
  - `python -m kabusys.config_setup` : 対話式で .env を作成・更新
- 設定検証
  - `python -m kabusys.validate_config` : .env と config/*.yaml の検証（--strict オプションあり）
- 実行エンジン（ExecutionEngine）
  - `python -m kabusys.run_execution` : 実際の発注ループを起動（paper_trading ではモックブローカーを使用）
  - Paper trading は本番 DB と分離して `data/paper_trading.db` に記録
- 監視プロセス（Monitoring）
  - `python -m kabusys.run_monitoring` : SystemMonitor をポーリングして監視ログを記録、Kill Switch 判定などを実行
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート
  - `python -m kabusys.tools.paper_verification_report` : SQLite の履歴から PASS/FAIL レポートを生成
- AI 関連
  - ニュースセンチメント（OpenAI を使用して ai_scores テーブルへ書き込み）
  - レジーム検出（ETF とマクロニュースを組み合わせて日次で判定）
- ポートフォリオ構築ユーティリティ
  - 候補選定・重み計算・ポジションサイズ決定・セクター制限など純粋関数群
- ロギング / プロセス優先度ユーティリティ
  - 統一的なログ設定（コンソール + 日次ローテーション）
  - プロセス優先度 / CPU affinity の設定（psutil ベース）

---

## セットアップ手順（開発向け）

1. Python 環境を準備
   - Python 3.9+ を想定（プロジェクトの pyproject.toml / CI を参照してください）
2. 依存パッケージをインストール
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）
3. リポジトリを配置し、初期ディレクトリを作成
   - data/ や logs/ はスクリプトが自動作成しますが、権限等に注意してください。
4. .env を作成
   - 対話式で作成:
     - python -m kabusys.config_setup
   - あるいは手動で環境変数を設定（下の「環境変数」セクション参照）
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正して再実行
6. DB 初期化は各スクリプト起動時に行われます（monitoring / execution 起動スクリプト内で init_monitoring_db を呼び出します）

---

## 環境変数（主なもの）

必須（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

その他（任意や上書き可能）
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し DB は data/paper_trading.db に切り分けられます
- DUCKDB_PATH — DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレーディング専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行プロセス管理・Kill Switch に関連

（.env を作成する際は .env.example を参考に、.env を Git にコミットしないでください）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
    - 起動時に data/stop_requested.flag があると起動せず終了
    - 実行中は data/execution.pid を使用（設定で上書き可）

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor をポーリングして system_status 等を monitoring DB に記録
    - MONITOR_POLL_INTERVAL で間隔を制御（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path を使う（環境に依存せず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

ログ出力:
- ログはデフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。

停止フラグ / Kill Switch:
- 実行エンジンは data/stop_requested.flag（および Kill Switch により data/kill.flag）を監視して動作を停止します。
- kill.flag は KillSwitch によって書き込まれ、ExecutionEngine の停止トリガーになります。既存の旗は冪等的に扱われます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアが有効になります（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリ中の主要モジュール／ファイルを抜粋して示します（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス。自動でプロジェクトルートの .env/.env.local を読み込みます（無効化可）。
  - config_setup.py
    - .env を対話式に作成・更新するウィザード。
  - validate_config.py
    - 起動前に設定不備を検出する CLI。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
  - monitoring/
    - monitoring_db.py : SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py  : システム資源・データ鮮度・プロセス生存監視
    - trade_monitor.py   : （注文滞留・約定異常等の監視 — 実装参照）
    - risk_monitor.py    : ドローダウン / ポジション上限監視
    - kill_switch.py     : kill.flag の作成 / クリア
    - monitoring_engine.py : 各 Monitor を束ねるエンジン
    - alert_manager.py   : （通知管理 — LINE 等）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 実行ロジック・ブローカー抽象化・リスク制御等
  - portfolio/
    - portfolio_builder.py, risk_adjustment.py, position_sizing.py
      - 候補選定・重み計算・ポジションサイジング等の純粋関数
  - research/
    - factor_research.py : モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を利用）
    - feature_exploration.py : 将来リターン計算、IC/統計サマリ等
  - ai/
    - news_nlp.py : ニュースを LLM でスコアリングして ai_scores へ保存
    - regime_detector.py : ETF MA + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py : ペーパートレードの検証レポート生成
  - utils/
    - logging_setup.py : 共通ログ初期化（stdout + 日次ファイルローテーション）
    - process_priority.py : プロセス優先度 / CPU affinity の設定（psutil 利用）

（上記以外にも補助モジュールやデータパイプライン用モジュール等があります）

---

## 実運用上の注意点

- 本番（KABUSYS_ENV=live）では全ての設定（API トークン・通知先等）を慎重に管理してください。validate_config は live の場合に警告を出します。
- .env は絶対に Git へコミットしないでください。
- run_monitoring は監視用 DB として本番 sqlite_path を参照します。Paper trading でも監視は本番 DB を見る設計です（監視データは分離されません）。
- Paper trading の注文履歴は paper_trading 用 DB に記録され、本番 DB と完全分離されています。
- OpenAI や外部 API 呼び出しは障害時にフェイルオープン/フェイルセーフの挙動を組み込んでいますが、API キーやレート制限、コストに注意してください。
- データベースやログディレクトリのパーミッションを適切に設定してください。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。

---

## 追加情報 / トラブルシュート

- ログレベルの変更
  - 環境変数 `LOG_LEVEL` を設定（例: LOG_LEVEL=DEBUG）
- ログ出力先変更
  - 環境変数 `LOG_DIR` で logs ディレクトリを上書き可能
- ポーリング間隔変更（監視）
  - MONITOR_POLL_INTERVAL に秒数を指定（例: MONITOR_POLL_INTERVAL=30）
  - 0 以下の値は無効でデフォルト 60 秒にフォールバックします
- Kill Switch をクリアしたい場合
  - data/kill.flag を手動で削除、または実行時に KillSwitch.clear() を呼ぶロジックを使う
  - 起動時に自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定（本番では 0 推奨）

---

この README はコードベースの主要な利用方法と注意点をコンパクトにまとめたものです。詳細な設計や挙動は各モジュールの docstring / ソースコメントを参照してください。必要であれば、特定モジュール向けのより詳しいドキュメント（利用例・パラメータ説明・入出力フォーマットなど）を追加で作成します。