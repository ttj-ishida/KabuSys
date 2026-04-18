# KabuSys — 日本株自動売買システム (README)

バージョン: 0.1.0

このリポジトリは日本株を対象とした自動売買システムのコアコンポーネント群を含みます。実行エンジン、監視、リサーチ（ファクター計算）、ポートフォリオ構築、AI ベースのニュース NLP などをモジュール化して提供します。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプトの実行例）
- 環境変数 / 設定
- 主要コンポーネントの説明
- ディレクトリ構成
- よくあるトラブルシューティング・注意点

---

## プロジェクト概要
KabuSys は自動売買に必要な以下の主要機能を持つ Python パッケージです。
- 注文実行エンジン（ExecutionEngine） — ブローカークライアント経由での発注管理、リスク管理、リコンサイル。
- 監視（Monitoring） — システム状態、注文の滞留／異常、ドローダウン監視と Kill Switch。
- リサーチ（Research） — DuckDB 上でのファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量解析ユーティリティ。
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、ポジションサイズ算出、セクター制限などの純関数群。
- AI モジュール — OpenAI を用いたニュースセンチメント・市場レジーム判定（オプション）。
- ユーティリティ — ロギング設定、プロセス優先度設定、設定ウィザード/検証ツール 等。
- ツール — ペーパートレードの検証レポート生成等。

---

## 主な機能一覧
- 設定ウィザード: python -m kabusys.config_setup で .env を対話式生成
- 設定検証: python -m kabusys.validate_config で環境変数 / config/*.yaml の検証
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用して本番 DB と分離（data/paper_trading.db）
- 監視ループ起動: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- DuckDB を用いたファクター計算（calc_momentum / calc_volatility / calc_value）
- AI によるニュースセンチメント（OpenAI）とレジーム判定（オプション）
- ログ: stdout と日次ローテートファイル（logs/<app_name>.log）を統一管理
- プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発 / ローカル実行）
1. Python 環境を用意
   - 推奨: Python 3.10+（コードの型ヒント等を想定）
   - 仮想環境を作成してアクティベート
     - python -m venv .venv
     - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール
   - 必要な外部ライブラリ（最低限）
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config で YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （注）requirements.txt は本リポジトリに含まれていないため、上記を適宜揃えてください。

3. リポジトリルートに data/ と logs/ を作成（必要なら）
   - mkdir -p data logs
   - 一部スクリプトは起動時に自動で作成しますが、ログディレクトリ作成権限に注意してください。

4. .env を作成
   - python -m kabusys.config_setup を実行して対話式で .env を生成
   - もしくは .env.example を参考に手動で作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで非ゼロ終了します

---

## 使い方（主要スクリプト例）
- 実行エンジン（ExecutionEngine）起動:
  - KABUSYS_ENV を適切に設定したうえで:
    - python -m kabusys.run_execution
  - 挙動:
    - is_paper (= KABUSYS_ENV == "paper_trading") の際は paper_trading 用 DB に接続し MockBroker を使用
    - data/stop_requested.flag があると起動せず終了
    - プロセス優先度を "high" に設定し、PID を data/execution.pid に記録

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60）
  - 監視は常に本番の sqlite_path（SQLITE_PATH）に対して行います（環境に依らず）
  - data/stop_requested.flag を検知すると監視ループを終了

- .env の生成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH (PAPER_TRADING_SQLITE_PATH より優先)

---

## 環境変数 / 主要設定
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主なオプション（デフォルト値を含む）:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 環境で使用）
- PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）
- LOG_LEVEL: "INFO"（または DEBUG/WARNING/etc.）
- LOG_DIR: デフォルト logs/
- OPENAI_API_KEY: OpenAI を利用する場合に必要（ai.score_news / regime_detector）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: "1" にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: pid/kill flag のパス（Settings で参照）

kill / stop フラグ:
- data/kill.flag — KillSwitch による ExecutionEngine 停止指示（監視から書き込まれる）
- data/stop_requested.flag — 外部から「全プロセスを止める」要求としてスクリプトが監視するファイル

---

## 主要コンポーネントの説明（抜粋）
- kabusys.config — .env 自動読み込み / Settings クラス（環境値取得とバリデーション）
- kabusys.config_setup — .env を対話式に生成・更新するウィザード
- kabusys.validate_config — 起動前の環境検証ツール
- kabusys.run_execution — ExecutionEngine を起動する CLI ラッパ
- kabusys.run_monitoring — SystemMonitor をポーリングで回す起動スクリプト
- kabusys.monitoring.*
  - monitoring_db.py — SQLite による監視ログの永続化・マイグレーション
  - system_monitor.py — CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション上限監視とリスクログ
  - kill_switch.py — 条件に応じて kill.flag を書き込むロジック
  - monitoring_engine.py — 各 Monitor を束ねるポーリング実行クラス
- kabusys.execution.* — 注文実行に関するエンジン・リスクマネージャ・OrderRepository 等（実装本体は該当モジュールを参照）
- kabusys.portfolio.* — 候補選定、重み計算、ポジションサイズ算出、セクター上限、レジーム乗数
- kabusys.research.* — DuckDB 上でファクター算出と特徴量解析（ファクターの正規化ユーティリティ等）
- kabusys.ai.* — OpenAI を用いたニュース NLP（score_news）と regime_detector（市場レジーム判定）
- kabusys.utils.logging_setup — Stream + TimedRotatingFileHandler によるロギング設定
- kabusys.utils.process_priority — psutil を使ったプロセス優先度 / CPU アフィニティ設定

---

## ディレクトリ構成
リポジトリ（src/kabusys 以下）の主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (参照されるがここに含まれる)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照される場合あり)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/ (上記)
    - monitoring/monitoring_db.py
  - (その他スクリプト / config / data / logs)

---

## よくあるトラブルシューティング・注意点
- .env（必須環境変数）が不足していると起動時に ValueError が発生します。まず python -m kabusys.config_setup → python -m kabusys.validate_config を実行してください。
- ログディレクトリ作成に失敗するとファイル出力が無効化され、コンソールのみになります（stderr に警告が出ます）。権限を確認してください。
- run_execution / run_monitoring は起動直後にプロセス優先度を "high" に設定しますが、OS と権限によっては psutil.AccessDenied が発生してスキップされます（警告ログ）。
- MONITOR_POLL_INTERVAL に 0 以下や整数以外を指定すると警告が出てデフォルト 60 秒に戻ります。
- paper_trading 環境では本番 DB と完全分離するため、PAPER_TRADING_SQLITE_PATH を利用してください（デフォルト: data/paper_trading.db）。PAPER_FILL_MODE で約定挙動を制御できます。
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定してください。AI 呼び出しは外部 API のため失敗しうる設計（リトライやフェイルセーフが組まれています）。
- kill.flag / stop_requested.flag による停止制御:
  - 監視は kill.flag を書き込み ExecutionEngine 停止を誘導します（部分失敗時の冪等性に配慮）。
  - 外部から強制停止したい場合は data/stop_requested.flag を作成してください（run_* スクリプトが検知して終了します）。

---

この README はコードの要点をまとめたものです。詳細な設計方針やアルゴリズムの説明は各モジュールの docstring / コメントに記載されています。必要であれば個別モジュールのドキュメント化（API リファレンス、アーキテクチャ図、設計ドキュメント）も追加できます。要望があれば教えてください。