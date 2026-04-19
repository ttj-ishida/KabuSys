# KabuSys

日本株自動売買システムの一部モジュール群 (ライブラリ + 起動スクリプト)。  
このリポジトリはトレード実行エンジン、監視（Monitoring）、リサーチ、ポートフォリオ構築、AI を用いたニュース評価などを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動スクリプト / CLI）
- 環境変数（主要項目）
- ディレクトリ構成
- 運用・トラブルシューティングの注記

---

プロジェクト概要
- KabuSys は日本株向けの自動売買基盤のコンポーネント集合です。
- 発注エンジン（Execution）、実行監視（Monitoring）、リサーチ（ファクター計算等）、ポートフォリオ構築、AI ベースのニュースセンチメント評価などを含みます。
- 設定は .env ファイル（または環境変数）で与え、SQLite / DuckDB をデータ永続化に利用します。
- Paper Trading モードでは本番 DB と分離された専用 SQLite（デフォルト: data/paper_trading.db）を使用します。

---

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory を用いたブローカークライアント抽象化
  - リスク管理、注文管理、補正 (reconciler) を含む実行フロー
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）による安全停止
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager など（監視・アラート・Kill Switch）
  - SQLite ベースの監視ログ（monitoring_db）
  - MONITOR_POLL_INTERVAL によるポーリング間隔設定
- 設定支援ツール
  - 対話式 .env 生成: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- Research（research パッケージ）
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - DuckDB を用いたデータ集計
- Portfolio（portfolio パッケージ）
  - 候補選定、重み付け（等分／スコア）、ポジションサイズ計算、セクター制約、レジーム調整
- AI（ai パッケージ）
  - news_nlp.score_news: OpenAI を用いたニュースのセンチメント集約 → ai_scores へ書き込み
  - regime_detector.score_regime: ETF の MA とマクロニュースで市場レジーム判定
- ユーティリティ
  - ログ設定: kabusys.utils.logging_setup.setup_logging
  - プロセス優先度/CPU affinity: kabusys.utils.process_priority
  - Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report

---

セットアップ手順（開発環境向け）
1. Python 仮想環境を作成・有効化（例: Python 3.9+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須パッケージ例（requirements.txt が無い場合の目安）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で必要 / optional）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成した .env は絶対に Git にコミットしないでください。

4. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit code 1 にします。

5. データディレクトリ準備
   - デフォルトの DB / ファイル:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite: 監視用)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - data/execution.pid (エンジン PID)
     - data/kill.flag / data/stop_requested.flag (停止/kill フラグ)
   - 必要に応じてディレクトリを作成（通常は起動時に自動作成されます）。

---

使い方（主要コマンド例）
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト: 60）
  - 停止フラグ: data/stop_requested.flag を作成すると監視ループを終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  (PAPER_TRADING_SQLITE_PATH 環境変数で指定可)

- AI / リサーチ系はモジュール API として呼び出す
  - 例（Python コンソール内）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - これらは DuckDB 接続や OpenAI API キーを引数として受け取る設計です。

---

主要な環境変数
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の填埋モード（instant / partial / never / reject。デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。run_monitoring で参照）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

自動 .env ロードの挙動
- プロジェクトルート（.git または pyproject.toml を基準）から自動で .env を読み込みます。
- 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env 読み込み含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート生成スクリプト
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & 永続化層
    - system_monitor.py      — CPU/MEM/DISK/データ鮮度監視
    - trade_monitor.py       — (省略されたが監視ロジック想定)
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — モニター統合 / ポーリング実行
    - alert_manager.py       — (省略されたが通知管理想定)
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定 / weight 計算
    - position_sizing.py     — 株数決定 / 投資額スケーリング
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - utils/
    - __init__.py
    - logging_setup.py       — 共通ログ設定（console + 日次ローテート）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

（実装上はさらに execution/*、data/* 等のモジュールが存在する想定です）

---

運用・注意点
- Paper Trading モード:
  - KABUSYS_ENV=paper_trading とすると run_execution は MockBrokerClient を使用し、paper_trading 用 DB に記録します（本番 DB とは分離）。
- Kill Switch / Stop フラグ:
  - KillSwitch は data/kill.flag に理由を書き込むことで ExecutionEngine に停止シグナルを出します。
  - run_execution / run_monitoring 停止フラグは data/stop_requested.flag を監視して安全に終了します。
- ログ:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼んでいます。ログは stdout と logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリは作成されますが、失敗時はコンソールのみ動作）。
- OpenAI 関連:
  - API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で指定）。
  - レートリミット・タイムアウト・5xx はリトライロジックが入っていますが、API 費用やレイテンシに注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存スキーマに対して idempotent にテーブルとカラム追加を行います（例: peak_value, latency_ms カラム追加）。
- 権限・優先度設定:
  - 起動時に set_process_priority("high") を呼んでいます。環境により設定に失敗することがあり、その場合は警告が出ます。

---

トラブルシューティング（よくある問題）
- .env を読み込まない / 環境変数が反映されない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。自動ロードを無効化していると .env が読み込まれません。
- DB ファイルが見つからない
  - PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH の設定を確認し、必要に応じてファイルパスを作成してください。
- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY を確認、ネットワークアクセスやレート制限も考慮してください。news_nlp と regime_detector にはリトライとフェイルセーフが組み込まれています。
- ログファイルが作成されない
  - logs ディレクトリの作成権限を確認してください。作成に失敗するとコンソール出力のみになります（警告が stderr に出ます）。

---

開発者向け補足
- テスト時は環境副作用を避けるため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、必要な環境値をテストコード内で注入することを推奨します。
- AI 呼び出し（_call_openai_api 等）は内部で小さなラッパー関数に分離されており、ユニットテストではパッチ差し替えが容易です（unittest.mock.patch を想定）。
- DuckDB 接続は多くのリサーチ関数で直接受け取り SQL を発行する設計です。テスト用に in-memory DuckDB 接続を使うことができます。

---

以上。README の内容に追加してほしい項目（例: 実行例のログ抜粋、requirements.txt、実装されている API の詳細仕様など）があれば教えてください。必要に応じて英語版 README も作成できます。