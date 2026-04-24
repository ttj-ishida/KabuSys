README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine: 発注・リスク管理・注文管理の実行エンジン（本番 / ペーパートレード対応）
- Monitoring: システム状態・注文・リスクをポーリングしてログ・アラート・Kill Switch を管理
- Research: DuckDB を用いたファクター計算・リターン分析・IC 計算などの研究用モジュール
- AI 補助機能: ニュースセンチメント解析（OpenAI）やマーケットレジーム判定
- ユーティリティ: 設定ウィザード、設定検証、ペーパートレード検証レポート生成、ログ設定等

特徴
----
- 本番 / ペーパートレードを明確に分離（環境変数 KABUSYS_ENV）
- DuckDB（分析用）、SQLite（監視・トレース用）を併用
- OpenAI を用いたニュース NLP（任意）・レジーム検出（任意）
- kill.flag による外部からの安全停止（Kill Switch）
- ログはコンソール + 日次ローテーションでファイルに出力（logs/）

主な機能一覧
---------------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録。
  - 起動時にプロセス優先度を high に設定。PID ファイルを data/execution.pid に出力。
- run_monitoring.py
  - SystemMonitor をポーリングして system_status 等を SQLite に書き込む。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず production 用 sqlite_path を使用。
- validate_config.py
  - .env と config/*.yaml（存在する場合）を起動前に検証。--strict で警告をエラー扱いに。
- config_setup.py
  - 対話式に .env を生成 / 更新するウィザード。
- tools/paper_verification_report.py
  - ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを作成。
- ai/news_nlp.py / ai/regime_detector.py
  - ニュースを LLM（OpenAI）でセンチメント化して ai_scores に書き込む、レジーム判定を行う（どちらも API キー必須）。
- portfolio/*, research/*, monitoring/* 等
  - ポートフォリオ構築、ポジションサイズ計算、ファクター計算、モニタリングの実装群。

セットアップ手順
----------------
前提:
- Python 3.10+ を推奨（コードで | 型注釈を使用）
- システムに DuckDB / psutil のビルド要件が満たされていること

1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows (PowerShell/CMD)

3. 必要パッケージをインストール:
   pip install duckdb psutil openai
   # オプション: YAML を検証したい場合は PyYAML
   pip install pyyaml

   （注）requirements.txt が無い場合は上記を手動でインストールしてください。

4. ディレクトリ作成:
   mkdir -p data logs

5. .env の準備:
   - 対話式で作る（推奨）:
     python -m kabusys.config_setup
   - またはテンプレートを参考に .env を作成（.env.example がある想定）。
   - 自動ロード: デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。不要なときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能の API キー（任意）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時のみ使用）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動 / ツール）
---------------------

設定検証:
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い:
  python -m kabusys.validate_config --strict

環境設定ウィザード:
- python -m kabusys.config_setup

ExecutionEngine を起動:
- 本番 / 開発:
  python -m kabusys.run_execution
- ペーパートレード:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  （ペーパートレード時は PAPER_TRADING_SQLITE_PATH に記録）

Monitoring を起動:
- python -m kabusys.run_monitoring
- ポーリング間隔を変更したい場合:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

Paper Trading 検証レポート:
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 機能（ニュース NLP / レジーム判定）:
- OPENAI_API_KEY 環境変数を必ず設定してください。
- 実行は該当モジュールの関数を呼ぶ形（例: kabusys.ai.score_news）。CLI ラッパーは含まれていないためスクリプトやジョブから呼び出します。
- モデル: gpt-4o-mini を利用する想定。API 呼び出しはレート制限・5xx に対して再試行を行います。

停止・Kill Switch
- 外部からの安全停止:
  - KillSwitch は data/kill.flag を作成すると ExecutionEngine に停止トリガーを投げる仕組みになっています（ExecutionEngine 側で定期的にチェックして停止）。
- run_monitoring/run_execution は data/stop_requested.flag を検出すると起動ループを終了します（停止フラグ）。

ログ
----
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存されます（例: logs/execution.log, logs/monitoring.log）。
- 環境変数 LOG_DIR で変更可能。LOG_LEVEL でログレベル指定。

ディレクトリ構成
-----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパー検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + 1321 MA）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視）
    - system_monitor.py
    - trade_monitor.py        — （trade_monitor 実装あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信ロジック）
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

補足 / 注意事項
--------------
- Monitoring は「環境に関係なく」settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視ログを保存します。ExecutionEngine は KABUSYS_ENV に応じて専用の PAPER_TRADING_SQLITE_PATH を使います（ペーパートレードと本番を分離）。
- .env の自動読み込み: プロジェクトルートを .git または pyproject.toml で検出し .env/.env.local を読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しは外部 API 依存のため、API キーが必要です。API 呼び出しの失敗時にフェイルセーフ（スコア 0.0 など）で継続する設計の部分がありますが、本番では鍵・レート制御に注意してください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（ファイル出力スキップ）。

貢献
----
- バグ報告や改善提案は Issue を作成してください。
- コードスタイル: type hints を多用しています。ユニットテストを追加するときは明示的に環境変数の影響を排除するようにしてください（KABUSYS_DISABLE_AUTO_ENV_LOAD 等）。

ライセンス
----------
リポジトリに別途ライセンスファイルがある想定です。適切なライセンスを参照してください。

以上。必要ならセットアップ用の requirements.txt や systemd/サービスユニット例、具体的な .env.example を追加で作成できます。どの情報が欲しいか教えてください。