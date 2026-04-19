# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築、リスク管理、発注実行（本番 / ペーパートレード分離）、監視、リサーチ、ニュースNLP（OpenAI 利用）などのコンポーネントを含みます。

## プロジェクト概要
KabuSys は以下の目的を持つモジュール群で構成された小型の自動売買基盤です。

- 市場データ（DuckDB）に基づくファクター算出・リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- 発注実行エンジン（本番 / ペーパートレード分離）
- 実行中システムの監視 / Kill Switch（フラグによる停止）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- 各種ユーティリティ（設定ウィザード、検証、ログ設定 等）

## 主な機能一覧
- Portfolio:
  - 候補選定（スコア降順）、等金額／スコア重み付け
  - ポジションサイズ計算（リスクベース・等分配・スコアベース）
  - セクター上限適用、レジーム乗数
- Execution:
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モードでは MockBroker により data/paper_trading.db を使用して本番 DB と完全分離
- Monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite）
  - Kill Switch（data/kill.flag）で安全に ExecutionEngine を停止
- Research:
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC 計算・統計サマリー
- AI:
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア生成
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ツール:
  - 設定ウィザード（.env の対話作成）
  - 設定検証 CLI（config/*.yaml の存在や必須環境変数をチェック）
  - Paper Trading 検証レポート生成

## 前提条件
- Python 3.10+
- 必要なサードパーティライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml の検証を行う場合）
- OS に依存する機能（プロセス優先度設定など）は管理者権限やプラットフォームにより制限を受けることがあります。

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（例）
   - pip install -r requirements.txt
     （requirements.txt が無い場合は個別に duckdb, psutil, openai, pyyaml 等をインストール）
4. 初期設定（.env 作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする: python -m kabusys.validate_config --strict

注意: config.py はデフォルトでプロジェクトルートの `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 主要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: OpenAI を使う機能を動かす場合に必須
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード用）
- PID_FILE_PATH: data/execution.pid（ExecutionEngine の PID）
- KILL_FLAG_PATH: data/kill.flag（Kill Switch のフラグ）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- LOG_LEVEL / LOG_DIR

サンプル（.env の最低限）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO

## 実行方法（コマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します
    - 停止フラグファイル data/stop_requested.flag が作成されていると起動せず終了します
    - PID ファイルは data/execution.pid に書かれます

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング周期を変更可能（秒）
  - 監視は常に production 用 sqlite_path（SQLITE_PATH）を使用します
  - 停止は data/stop_requested.flag を作成することで行えます

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチ機能（Python から呼び出し）
  - DuckDB 接続を作成して関数を呼ぶ例:
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.research import calc_momentum
    - records = calc_momentum(conn, datetime.date(2026, 4, 10))
  - ニュース NLP / レジーム判定:
    - OpenAI API キーを環境変数 OPENAI_API_KEY に設定してから、該当関数を呼び出してください
    - 例: from kabusys.ai import score_news; score_news(conn, target_date, api_key=None)

## 停止・Kill Switch の仕組み
- 単純停止要求:
  - プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します
- Kill Switch（危険事象による自動停止）:
  - リスク監視で閾値超過（ドローダウン、ポジション上限等）が検出された場合、KillSwitch が data/kill.flag に理由を書き込みます
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合は自動クリアします（本番では 0 推奨）

## ロギング
- ログは標準出力（stdout）とファイル（デフォルト logs/<app_name>.log）へ出力します
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で決定します
- 日次ローテーション（30 日保持）が有効です

## ディレクトリ構成
主要ファイル / 重要モジュールを抜粋して説明します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py          — .env 対話ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視ログ永続化層
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （発注関連監視）※（ファイル一覧に依存）
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — フラグファイルによる停止シグナル
    - alert_manager.py       — 通知管理（LINE 等）※（実装参照）
  - execution/
    - execution_engine.py    — 発注エンジン本体（EngineConfig 等）
    - order_manager.py       — 注文管理ロジック
    - order_repository.py    — 発注ログ等の永続化
    - broker_factory.py      — ブローカークライアント生成（本番 / Mock）
    - risk_manager.py        — 発注時のリスクチェック
    - reconciler.py          — ブローカ状態とレポジトリの差分調整
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数計算・スケーリング
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py — forward returns / IC / summary 等
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 利用）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

その他:
- data/                     — デフォルト DB やフラグファイル（手動作成される）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag, stop_requested.flag, execution.pid など
- logs/                     — ログファイル出力先（デフォルト）

## 使い方のヒント・運用ノウハウ
- 本番（live）に切り替える前に必ず validate_config で設定をチェックしてください
- paper_trading モードは本番 DB と完全分離して動くためテストに便利です
- OpenAI を使う機能は API キーが必要で、利用コストとレイテンシを考慮してください
- Kill Switch は重要なセーフティーネットです。運用時は KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します
- ログディレクトリ権限・ディスク容量の監視も実運用では必須です

---

この README はコードベースの主要点をまとめた概要です。各モジュールの詳細な使用法・パラメータはソースコードの docstring / 関数コメントを参照してください。必要があれば特定モジュール（例: ExecutionEngine の設定や AI モジュールの呼び出し例）についてさらに詳しいドキュメントを作成します。