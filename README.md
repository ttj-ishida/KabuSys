KabuSys — 日本株自動売買システム
=================================

この README はリポジトリ内の主要スクリプト／モジュール群を説明する開発者向けドキュメントです。
コードベースは自動売買エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、研究ツール、AI 補助処理等で構成されています。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買システム（バックエンドライブラリ）です。主な責務は以下です。

- 注文の発行・管理（ExecutionEngine / OrderManager 等）
- システム稼働状況・注文ログ・リスクの監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（portfolio パッケージ）
- ファクター計算・特徴量探索（research パッケージ）
- ニュース NLP を利用した銘柄センチメント評価・レジーム判定（ai パッケージ）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

主な機能一覧
-------------
- 実行環境切替（KABUSYS_ENV: development / paper_trading / live）
  - paper_trading では MockBrokerClient を使用し、本番 DB と分離された SQLite に記録
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話的に生成
- 設定検証 CLI（python -m kabusys.validate_config）で .env や config/*.yaml を事前検証
- 監視ループ（python -m kabusys.run_monitoring）
  - システムメトリクス収集、プロセス生存チェック、データ鮮度チェック、Kill Switch 判定、アラート送信
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 実行エンジン起動（python -m kabusys.run_execution）
  - ExecutionEngine を別スレッドで実行、stop フラグ / PID 管理、paper_trading 用 DB 分離
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
  - 稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL 判定
- AI 機能
  - news_nlp: OpenAI を使ったニュースセンチメントスコアの算出・ai_scores への書込み
  - regime_detector: ETF（1321）やマクロニュースを用いた市場レジーム判定
- ポートフォリオ構築系（純粋関数）
  - 候補選定、重み計算（等金額・スコア加重）、セクターキャップ適用、ポジションサイズ計算

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意します。
2. 必要なパッケージをインストールします（主要な依存例）:
   - duckdb, psutil, openai, PyYAML（config 検証用） など
   例:
     pip install duckdb psutil openai PyYAML
   実際の requirements.txt がある場合はそれを使用してください。

3. プロジェクトルートに移動し、.env を作成します（対話式推奨）:
     python -m kabusys.config_setup
   生成後、設定を検証:
     python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

4. データディレクトリ（デフォルト: data/）やログディレクトリ（デフォルト: logs/）は自動作成されますが、必要に応じて手動で作成してください。

主な環境変数（代表）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 省略可:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
  - LOG_LEVEL — デフォルト INFO
  - OPENAI_API_KEY — AI 機能を使う場合に必須
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか (0/1)

使い方（代表コマンド）
--------------------
- 環境設定ウィザード（.env 生成）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
    python -m kabusys.run_monitoring
  補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定できます（例: export MONITOR_POLL_INTERVAL=30）
    - 監視は .env の環境（KABUSYS_ENV）に関わらず、本番用 sqlite_path（settings.sqlite_path）を使用します
    - stop フラグ: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します

- 実行エンジン起動（Execution）
    python -m kabusys.run_execution
  補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と完全分離）
    - 実行エンジンは別スレッドで動作し、プロセス優先度を high に設定します
    - stop フラグ / PID 管理:
        - プロジェクトルート/data/stop_requested.flag を作成するとエンジンを停止します
        - PID ファイルは data/execution.pid（既定）に書き込まれます

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI スコアリング（プログラムから呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY を環境変数に設定するか、api_key を渡してください
  - regime_detector.score_regime(conn, target_date, api_key=None)

運用に関する注意点
------------------
- 本番（KABUSYS_ENV=live）では .env の設定（LINE 通知等）を必ず確認してください。validate_config が警告を出します。
- Kill Switch: risk に基づく Kill Switch（data/kill.flag）によって Execution を停止できます。kill.flag は既存なら上書きしません。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアしますが、本番では 0 を推奨します。
- ログ: kabusys.utils.logging_setup.setup_logging は logs/ ディレクトリに日次でログをローテーションして出力します。ログディレクトリに書き込み権限がない場合はコンソール出力のみになります。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼びます。権限や OS によっては設定できない場合があり、その場合は警告ログが出ます。
- DuckDB / SQLite のパスは Settings クラスで管理されます。paper_trading では DB を分離しています。

ディレクトリ構成（抜粋）
----------------------
リポジトリの主要モジュール/ファイル構成（src/kabusys 配下の代表）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理 (.env 自動読み込み含む)
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・スケール調整
    - risk_adjustment.py           — セクターキャップ・レジーム補正
  - research/
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py             — 監視 DB（SQLite）初期化 + 永続化 API
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文ログ監視（該当箇所はコード参照）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 管理
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください）

補足（開発者向け）
-----------------
- 設定自動ロード: config.py はプロジェクトルート（.git または pyproject.toml を探索）を基に .env/.env.local を自動ロードします。テスト時等に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は必要なカラムが足りない場合に ALTER TABLE を試みる簡易マイグレーションを行います。
- AI 呼び出し: OpenAI 呼び出しはリトライ・バックオフや JSON パースの堅牢化を考慮して実装されています。API バージョン差分に備えてステータスコードや例外種別を安全に扱う設計です。

ライセンス・貢献
----------------
- ライセンス・貢献フロー等は本 README に含まれていません。公開・配布時は別途 LICENSE ファイルや貢献ガイドを追加してください。

以上。リポジトリの各モジュールには詳細な docstring が付与されています。実装の確認やカスタマイズ時は個別モジュールのコメントを参照してください。