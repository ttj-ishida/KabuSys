# KabuSys — 日本株自動売買システム

この README はリポジトリ内の主要スクリプト / モジュール群（ExecutionEngine、Monitoring、Research、AI、Portfolio 等）についての概要、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な役割は以下です。

- 取引の実行（ExecutionEngine） — ブローカークライアント経由で注文を送信、リスク管理、オーダーの調停など
- 監視（Monitoring） — システム状況・データ鮮度・注文ログをポーリングしてログ化、Kill Switch による安全停止
- 研究（Research） — DuckDB に保存した時系列データを用いたファクター計算・特徴量解析
- AI（ニュース NLP / レジーム検出） — OpenAI を利用したニュースセンチメントや市場レジーム判定
- ポートフォリオ構築ユーティリティ — 候補選定、重み計算、株数決定、セクターキャップ等
- ツール群 — Paper Trading の検証レポート生成など

設計上のポイント：
- 環境変数 / .env で設定を管理。自動ロード機能あり（テスト時は無効化可能）。
- DuckDB（分析用）と SQLite（監視／発注履歴用）を併用。
- Paper Trading 用 DB を分離しているため、本番 DB と混ざらない設計。
- OpenAI 連携部はフェイルセーフ設計（API失敗時は安全側フォールバック）。

---

## 主な機能一覧

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（本番 / Mock）
  - オーダー管理・リスク管理・照合（reconciler, risk_manager, order_manager）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に system_status, trade_logs, positions, risk_logs, dashboard を永続化
  - Kill Switch（閾値到達で data/kill.flag を書き込み ExecutionEngine を止める）
- 研究・分析
  - ファクター計算（Momentum / Volatility / Value）
  - Forward returns / IC / 統計サマリー
- AI
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（MA200 + マクロセンチメント）
- ポートフォリオ
  - 候補選定、等加重 / スコア加重、リスクベースの株数計算
  - セクターキャップやレジーム乗数適用
- ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## セットアップ手順（開発 / ローカル）

以下は一般的なセットアップ手順です。プロジェクトによって依存関係ファイルがある場合は適宜読み替えてください。

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化（venv / conda 等）

3. 依存関係をインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 明示的に必要なパッケージ（コードから推測）:
     - duckdb
     - psutil
     - openai（OpenAI Python SDK）
     - （オプション）PyYAML（config 検証時に使用）

4. データディレクトリの作成（ログ / DB 保存先）
   - デフォルトはプロジェクト下の data/ と logs/。必要に応じて作成:
     - mkdir -p data logs

5. 環境変数設定
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - もしくは .env を直接作成（例は下に記載）

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いする場合:
     - python -m kabusys.validate_config --strict

---

## 主要環境変数一覧（代表）

- 必須（本番・テストで必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録
    - live: 本番モード（注意深く設定すること）

- データベース / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution エンジンの pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR — ログファイル保存ディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector に必要）

- その他
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE — Paper Trading の注文約定モード（instant | partial | never | reject）

自動 .env 読み込み:
- デフォルトでプロジェクトルートの `.env` / `.env.local` が自動で読み込まれます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例（.env の抜粋）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要コマンド / スクリプト）

全ての起動スクリプトはモジュール実行形式で提供されています（python -m kabusys.<module>）。

- 環境設定ウィザード（.env の対話式作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実際の売買／ペーパートレード）
  - python -m kabusys.run_execution
  - 振る舞い:
    - 起動時にプロセス優先度を "high" に設定
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH を使用
    - 停止フラグ: プロジェクトの data/stop_requested.flag を置くとエンジンを停止
    - PID を data/execution.pid に書き出す（設定により変更可）

- Monitoring 起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - プロセス優先度を "high" に設定
    - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き（デフォルト 60s）
    - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path（SQLITE_PATH）を使用
    - 停止フラグ: data/stop_requested.flag が存在するとループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- ライブラリ関数の利用（Python REPL / スクリプト内で）
  - AI ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - 研究関数:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

---

## 停止 / Kill スイッチについて

- 外部からの停止指示:
  - デーモン風に実行しているスクリプト（run_execution / run_monitoring）はプロジェクトの data/stop_requested.flag ファイル存在を監視しており、存在するとループをクリーンに終了します。停止したいときはこのファイルを作成してください。
- Kill Switch:
  - Monitoring がリスク条件（ドローダウン閾値超過等）を検出すると、設定された kill_flag_path（デフォルト data/kill.flag）に理由文字列を書き込みます。ExecutionEngine は起動時や実行中にこの kill.flag を検出して停止します（安全停止機構）。
  - 注意: KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

---

## ロギング / DB / ファイル場所

- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイルは app_name 別に日次ローテーションで保持（例: logs/execution.log, logs/monitoring.log）
  - 環境変数 LOG_DIR で変更可
- DB
  - DuckDB（分析用）: デフォルト data/kabusys.duckdb
  - SQLite（監視）: デフォルト data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（paper_trading 時に使用）
- その他ファイル
  - PID: data/execution.pid（実行時書き出し）
  - stop フラグ: data/stop_requested.flag（プロセス停止用）
  - kill フラグ: data/kill.flag（監視による停止シグナル）

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル / パッケージ構成（本 README 作成時点のソースに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env の自動読み込み / Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ・DB 操作用ユーティリティ
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - system_monitor.py     — システム・データ鮮度監視
    - trade_monitor.py      — （省略: trade 関連監視）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag 操作
    - alert_manager.py      — （省略: 通知送信）
  - execution/               — ExecutionEngine、order_manager、risk_manager 等（省略されているが起点あり）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py      — 統一ログ設定
    - process_priority.py   — プロセス優先度・CPU affinity 設定
    - __init__.py

（上記はリポジトリ内の主要モジュール抜粋です。完全なファイル一覧はリポジトリツリーを参照してください。）

---

## 開発者向けメモ / 注意点

- 自動 .env 読み込みは .env / .env.local の順に行われます。OS 環境変数は上書きされません（保護）。
- Monitoring は KABUSYS_ENV に係らず本番用の sqlite_path を参照する仕様です。これにより監視ログは常に本番 DB に書き込まれます（paper_trading と分離したい場合は設定を調整してください）。
- Paper Trading モードでは MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
- OpenAI API 呼び出し部分はリトライ・エラーハンドリングが実装されていますが、API キーやクォータに注意してください。テスト時は _call_openai_api をモックできます（ユニットテストを推奨）。
- ログディレクトリの作成に失敗するとファイルロギングはスキップされ、コンソール出力のみになります。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python から関数呼び出し（例）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, date(2026,4,1), api_key="sk-...")

---

必要に応じてこの README をローカル環境・運用手順に合わせてカスタマイズしてください。README の補足や特定モジュールの詳細ドキュメント化（例えば ExecutionEngine の起動オプションや order_manager の挙動の説明）が必要であれば、対象箇所を指定していただければ追記します。