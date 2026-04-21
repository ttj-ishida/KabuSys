# KabuSys

日本株自動売買システムのコードベース（最低限のドキュメント）。  
この README はプロジェクト概要・主な機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

概要
- KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。
- 発注実行（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ（DuckDB を用いたファクター計算）、および AI を用いたニュースセンチメント/レジーム判定機能を備えています。
- 設定は .env ファイル / 環境変数で管理され、Settings クラス（kabusys.config）で参照されます。

主な特徴（機能一覧）
- Execution
  - ExecutionEngine（発注の実行・リスク管理・注文管理・照合）
  - paper_trading モード（本番 DB と分離して data/paper_trading.db に記録）
  - BrokerClientFactory によるブローカークライアントの切替
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor：発注ログの監視（滞留注文・異常約定など）
  - RiskMonitor：ドローダウン・ポジション上限監視。kill.flag の発行
  - MonitoringEngine：各モニタを束ねて定期ポーリング（MONITOR_POLL_INTERVAL で間隔変更可）
  - 永続化は SQLite（監視用）を使用（monitoring.db）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア重み付け、セクター制限、ポジションサイズ計算（単元株処理付き）
- Research
  - DuckDB を使ったファクター計算（Momentum/Volatility/Value 等）
  - 特徴量探索（将来リターン、IC、統計サマリ）
- AI 系
  - news_nlp：OpenAI を使ったニュースの銘柄別センチメントスコア付与（ai_scores へ保存）
  - regime_detector：ETF（1321）MA とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

前提 / 依存パッケージ（代表）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合、任意）
- 標準ライブラリの sqlite3, threading, logging 等

セットアップ（ローカル開発用の簡易手順）
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo>
   - cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （PyYAML が必要な場合）pip install pyyaml

   ※ 実際のプロジェクト配布では requirements.txt を用意している場合があります。無ければ上記を最低限インストールしてください。

4. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って J-Quants トークン、Kabu API パスワード、KABUSYS_ENV などを設定します。
   - .env を直接作る場合は .env.example を参考にしてください。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

主要環境変数（よく使うもの）
- KABUSYS_ENV: execution 環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL / LOG_DIR: ログ出力レベルとログディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト用途）

使い方（代表的なスクリプト）
- 実行エンジンを起動（実際の取引 or paper_trading）
  - python -m kabusys.run_execution
  - 実行時、Settings.env により paper_trading なら MockBroker を使用し、data/paper_trading.db に記録されます。
  - 実行はスレッドで Engine.run_session を開始し、data/stop_requested.flag が作成されると安全停止します。
  - PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用 SQLite（Settings.sqlite_path）を使用します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視ループは data/stop_requested.flag を検知して終了します。

- .env の対話式設定
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションでデータベースパスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

停止・Kill Switch（安全停止）
- 実行/監視の強制停止（簡易）
  - プロセスに SIGINT（Ctrl+C）を送ると終了処理が行われます。
- data/stop_requested.flag
  - run_execution/run_monitoring はこのファイルの存在を監視しており、存在するとループを終了します（外部から停止シグナルを与える手段として利用）。
- Kill Switch（data/kill.flag）
  - RiskMonitor / KillSwitch が条件を満たすと data/kill.flag を書き込んで ExecutionEngine に停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアできますが、本番では推奨されません。

ログ
- ログは標準出力とログファイル（logs/<app_name>.log）へ出力されます（kabusys.utils.logging_setup.setup_logging を全スクリプトで呼び出しています）。
- LOG_DIR 環境変数でログ保存ディレクトリを変更可能。
- ログは日次ローテート（30 日分保持）。

データベース（デフォルトパス）
- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- SQLite（paper_trading）: data/paper_trading.db

注意事項 / 実運用上のポイント
- paper_trading モードは本番 DB と完全に分離されています（Settings.is_paper を参照）。
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使う設計になっています（run_monitoring の仕様）。
- OpenAI を利用する機能（news_nlp/regime_detector）は API キー（OPENAI_API_KEY）が必要です。API 失敗時はフェイルセーフ（無効値や既定値にフォールバック）する実装が多く組み込まれています。
- process_priority（kabusys.utils.process_priority）で起動時にプロセス優先度を "high" にセットします。アクセス権限によっては失敗する場合がありますが、その場合は警告を出して続行します。
- .env の自動ロード: Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主なファイル）
- src/
  - kabusys/
    - __init__.py                — パッケージ初期化（バージョン）
    - config.py                  — 環境変数 / Settings 管理（.env 自動読み込み含む）
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - utils/
      - logging_setup.py         — ログ設定ユーティリティ
      - process_priority.py      — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py         — SQLite モニタリング DB 永続化層
      - system_monitor.py        — システム監視
      - trade_monitor.py         — （省略：注文監視）
      - risk_monitor.py          — ドローダウン・ポジション上限監視
      - kill_switch.py           — kill.flag の管理
      - monitoring_engine.py     — 各 Monitor を束ねるエンジン
      - alert_manager.py         — （省略：通知ラッパー）
    - execution/
      - execution_engine.py      — 実行エンジン本体（EngineConfig など）
      - order_manager.py         — 注文管理
      - order_repository.py      — 注文 repository（SQLite）
      - reconciler.py            — 注文照合
      - risk_manager.py          — 発注前リスクチェック
      - broker_factory.py        — BrokerClient の生成
    - portfolio/
      - portfolio_builder.py     — 候補選定・重み計算
      - position_sizing.py       — 株数計算・集計制限
      - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py       — ファクター計算（Momentum/Value/Volatility）
      - feature_exploration.py   — 将来リターン・IC 等
    - ai/
      - news_nlp.py              — ニュース NLP（OpenAI）による ai_scores 書込
      - regime_detector.py       — 市場レジーム判定（OpenAI + MA200 等）
    - data/                      — 実行時に使用するデータファイル（DB やフラグファイル）
      - monitoring.db (デフォルト)
      - paper_trading.db (paper)
      - kill.flag, stop_requested.flag, execution.pid, ...
- pyproject.toml / setup.py 等（パッケージ配布設定）

簡単なコマンド例
- .env の対話設定
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動（60 秒ポーリング）
  - python -m kabusys.run_monitoring
- 監視間隔を 30 秒に変更して起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート（DB を指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

トラブルシューティングのヒント
- ログが出力されない / ファイルが作成されない:
  - LOG_DIR 権限やパス作成権限を確認してください（logging_setup はディレクトリ作成に失敗するとファイルハンドラをスキップします）。
- OpenAI API エラー:
  - OPENAI_API_KEY が正しく設定されているか、API 利用制限 / ネットワークを確認してください。AI モジュールはリトライやフォールバックを行いますが、キー未設定時は例外を投げます。
- DB のマイグレーション（カラム追加等）は monitoring_db.init_monitoring_db が起動時に行います。権限やファイルロックに注意してください。

最後に
- この README はコードベースの主要点を要約したものです。各モジュールの docstring や関数コメントには実装の意図・注意事項が詳細に書かれていますので、実装を読むときはそちらも参照してください。

必要であれば、この README を英語版に翻訳したり、運用手順（systemd / supervisor 用の unit サンプルや Dockerfile）を追加で作成します。どの形式が必要か教えてください。