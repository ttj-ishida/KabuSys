KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群です。
アルゴリズム研究（ファクター計算・特徴量解析）、ポートフォリオ構築、発注エンジン（ExecutionEngine）周辺のヘルパー、監視（Monitoring）や AI を使ったニュース解析などを含みます。

要点
- 簡潔に言うと: DuckDB/SQLite をデータ層として、発注ロジック・リスク管理・監視・レポート生成・LLM を用いたニュースセンチメントやレジーム検出などの機能を提供します。
- 実行スクリプト:
  - 実取引／模擬取引エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring
  - .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

機能一覧
- 環境設定管理
  - .env 自動読み込み（.env / .env.local、OS 環境変数優先）
  - 対話式ウィザード (kabusys.config_setup)
  - 設定検証ツール (kabusys.validate_config)
- 発注実行（ExecutionEngine）
  - 本番 / ペーパートレード切替（KABUSYS_ENV=paper_trading で MockBrokerClient を使用）
  - Paper Trading は専用 SQLite（デフォルト: data/paper_trading.db）に記録
  - エンジン停止はフラグファイルで制御（data/stop_requested.flag / data/kill.flag）
- 監視（Monitoring）
  - システム状態監視（CPU/メモリ/ディスク/プロセス生存・データ鮮度）
  - 注文ログ・リスクログ・ダッシュボードの永続化（SQLite）
  - Kill Switch（ドローダウン・ポジション上限検出時に kill.flag を書き込み ExecutionEngine を停止）
  - 監視ループの間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等重／スコア重み、ポジションサイズ計算（単元丸め・リスクベース等）
  - セクター上限フィルタ、レジーム乗数
- 研究用モジュール
  - ファクター計算（momentum/volatility/value）: DuckDB 接続を受け SQL で計算
  - 将来リターン・IC 計算、ファクター統計サマリ
- AI（LLM）連携
  - ニュースセンチメントスコアリング（OpenAI API、gpt-4o-mini を想定）
  - 市場レジーム判定（ETF ma200 + マクロニュースセンチメントの合成）
  - API エラーに対するリトライ・フォールバック設計
- ユーティリティ
  - ロギングセットアップ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity の設定ユーティリティ

セットアップ手順（開発 / ローカル実行向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML を検査したい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （本リポジトリに requirements.txt がある場合は pip install -r requirements.txt）

4. .env を作成
   - 対話的ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して .env を手動作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルト値）
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)
     - OPENAI_API_KEY: OpenAI を使用する場合に必要

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. 必要なディレクトリを作成（通常は起動時に自動作成されます）
   - data/ （DB・フラグファイル保存）
   - logs/ （ログ出力）

使い方（コマンド例）
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作ポイント:
    - 起動時にプロセス優先度を "high" に設定しようとします（権限がない場合は警告）。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
    - 起動前に data/stop_requested.flag が存在すると起動しません。
    - エンジンはデーモンスレッドで run_session を実行、stop フラグで停止できます。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 動作ポイント:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定できます（デフォルト 60）。
    - Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視ログは本番 DB に保存する設計）。
    - 監視ループは stop_requested.flag の存在を検知して優雅に停止します。

- Kill Switch（自動停止トリガ）
  - KillSwitch はリスク条件（ドローダウン、ポジション数上限）を満たすと settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。
  - ExecutionEngine は kill.flag を検知して安全に停止する設計になっています。
  - kill.flag を手動でクリアするにはファイルを削除するか KillSwitch.clear() を呼ぶ。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照されます。

AI / OpenAI 利用
- ニューススコアリング: kabusys.ai.score_news (内部で OpenAI を呼びます)
  - OPENAI_API_KEY 環境変数、もしくは関数引数で API キーを渡す必要があります。
  - LLM 呼び出しは retries/backoff を備え、失敗時は対象銘柄をスキップするフェイルセーフ設計です。
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime
  - 同様に OpenAI キーが必要です。マクロ記事がない場合はフォールバックで macro_sentiment=0.0。

ロギング
- 共通のロギング設定ユーティリティがあり、stdout（StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）を設定します。
- LOG_DIR 環境変数または setup_logging の引数でログ出力先を指定可能です。

停止・制御ファイル
- data/stop_requested.flag: run_* スクリプトがこのファイルの存在をチェックし、存在するとループを終了します（外部から優雅に停止させたいときに有用）。
- data/kill.flag: KillSwitch が安全のため書き込むフラグ。ExecutionEngine はこれを検出して停止します。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py      — レジーム判定（ma200 + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義・永続化 API
    - system_monitor.py
    - trade_monitor.py        — （TradeMonitor 実装を想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （通知管理：LINE などを想定）
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - data/                     — （実行時に data/*.db, flag ファイルを置く場所）
  - logs/                     — （ログファイル出力先、デフォルト）
  - utils/
    - logging_setup.py
    - process_priority.py

設計上の注意点 / 運用上のポイント
- 本番環境フラグ:
  - KABUSYS_ENV=live は特別な注意が必要です。validate_config は本番向けの追加チェック・警告を出します。
- DB 分離:
  - paper_trading モードでは paper_trading 用 SQLite を使い、本番の monitoring.db とは分離しています。
  - ただし Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト monitoring.db）を使用します。監視ログの保存先を分離したい場合は設定で上書きしてください。
- フォールトトレランス:
  - OpenAI 呼び出しや外部 API 呼び出しはリトライ・フォールバック設計になっています。致命的な例外は上位に伝播させますが、多くは警告ログ記録後スキップして継続します。
- 権限:
  - set_process_priority は OS により失敗することがあります（権限不足や未サポート OS）。失敗した場合はログに警告が出ますが実行は継続します。
- ログローテーション:
  - 日次・30世代保持。ログディレクトリ作成に失敗するとファイル出力をスキップして stdout のみになります。

よく使うコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring (MONITOR_POLL_INTERVAL=30 などで上書き可)
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

補足
- ここに書かれている実行方法・環境変数の詳細はコードの docstring / Settings クラスを参照すると最新のデフォルト値・振る舞いが確認できます。
- 実運用前には必ず python -m kabusys.validate_config を実行し、設定漏れや本番用の注意点をチェックしてください。

問題や改善提案があれば、リポジトリの issue に記載してください。