# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群。シグナル生成・ポートフォリオ構築・発注（本番／ペーパートレード）・監視・AI を用いたニュース解析／レジーム判定等の機能を含みます。

> バージョン: 0.1.0

## プロジェクト概要
- DuckDB / SQLite を使った時系列データ・メタデータ管理と、発注エンジン（ExecutionEngine）・監視コンポーネント（MonitoringEngine）・研究用モジュール（research）・ポートフォリオ構築（portfolio）・AIベースのニュース解析（ai）を提供します。
- ペーパートレード環境（KABUSYS_ENV=paper_trading）では本番 DB と分離された専用 SQLite（data/paper_trading.db）を利用する設計です。
- ログは統一的に設定され、コンソール出力＋日次ローテーションファイル（logs/<app_name>.log）に保存されます。

## 主な機能一覧
- 環境設定管理
  - .env の自動読み込み / 対話式生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 起動スクリプト
  - 実行エンジン起動: run_execution.py（本番 / ペーパー分離、PID / stop フラグ対応）
  - 監視ループ起動: run_monitoring.py（SystemMonitor をポーリング）
- 監視（monitoring）
  - system_status / trade_logs / positions / risk_logs / dashboard 用の永続化（SQLite）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働・データ鮮度の監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: 条件に基づく停止フラグ生成（data/kill.flag）
  - AlertManager（通知管理）を介したアラート送信（LINE などの設定に依存）
- 発注ロジック（execution）
  - BrokerClientFactory によるブローカークライアントの抽象化（本番は kabuステーション、ペーパーは Mock）
  - ExecutionEngine / OrderManager / Reconciler / RiskManager 等による発注管理
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等分・スコア加重）、ポジションサイズ計算、セクター集中制限、レジーム乗数
- 研究／解析（research）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、統計要約
- AI 関連（ai）
  - ニュース NLP スコアリング（OpenAI 使用、gpt-4o-mini を想定）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM 解析を合成）
- ツール
  - paper_verification_report: ペーパートレード検証レポート生成（稼働率・成功率・レイテンシ等の評価）

## 必要条件（推奨）
- Python 3.10+
- SQLite（標準ライブラリ）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- ネット接続（OpenAI を使う場合）
- kabuステーション API を使う場合はローカル or 実環境で kabu API が稼働していること

例（pip インストール）:
pip install duckdb psutil openai PyYAML

※requirements.txt がある場合はそれを使用してください。

## セットアップ手順
1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt  または  pip install duckdb psutil openai PyYAML
4. .env ファイルの作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成してください。
   - 注意: .env は絶対に Git にコミットしないでください。
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告をエラーとして扱いたい場合: python -m kabusys.validate_config --strict
6. 初回起動時の DB 作成
   - 監視スクリプト / 実行スクリプトを起動すると init_monitoring_db により必要テーブルが自動作成されます。

## 使い方（主なコマンド）
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV により本番／paper_trading を切替
    - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）を使用
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid に PID を書き込み、停止は stop_required.flag を監視して行います

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor を初期化しポーリングループを実行
    - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可（例: MONITOR_POLL_INTERVAL=30）
    - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依存せず本番用 path を使用）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式で作成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - YAML の構文検証には PyYAML が必要（未インストールでも実行できますが警告になります）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールの利用（研究・運用コード内で）
  - ニューススコア付与:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="OPENAI_KEY")

## 環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨／デフォルトあり:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO / DEBUG / ...
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings で確認できます
- 自動読み込み:
  - プロジェクトルートにある .env / .env.local は自動で読み込まれます（OS 環境変数が優先）。
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## 停止・操作フラグ
- 停止フラグ（run_monitoring / run_execution が監視）
  - data/stop_requested.flag を作成するとループが検知して終了します。
- Kill Switch（安全停止）
  - 条件（ドローダウンやポジション上限）が満たされると data/kill.flag が書き込まれ、ExecutionEngine の停止シグナルとして使用されます。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 に設定されていると自動クリアされます（本番では 0 推奨）。

## ディレクトリ構成（主要）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装による通知管理)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイム生成想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db
    - kill.flag, stop_requested.flag, execution.pid などのフラグ/管理ファイル
- logs/
  - <app_name>.log* 日次ローテーションログ（作成時に生成）

## 注意事項 / 運用上のヒント
- .env の取り扱い:
  - 機密情報（API トークン）は .env に保存して運用しますが、決して Git にコミットしないでください。
- 本番設定:
  - KABUSYS_ENV=live に設定する際は validate_config で警告事項を確認してください（LINE 通知設定など）。
  - KILL_FLAG_CLEAR_ON_START=1 は本番で危険です（自動で kill flag をクリアしてしまうため）。
- OpenAI 使用:
  - API 利用に伴うコストとレイテンシに注意してください。リトライ・バックオフは組み込まれていますが、API 側の制限や料金は別途管理してください。
- ログ / ディスク:
  - ログディレクトリ権限やディスク容量に注意してください。TimedRotatingFileHandler によりログは日次ローテーションされますが、バックアップ数が溜まると容量を消費します。
- テスト:
  - 自動ロードを抑止してユニットテストを実行する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと便利です。
  - AI 呼び出し部分はテスト時に差し替えられる設計（_call_openai_api のモック）になっています。

## トラブルシューティング
- 起動後テーブルが見つからない／スキーマエラー:
  - run_* スクリプトは起動時に必要な監視テーブルを自動生成します。パス（SQLITE_PATH など）を確認してください。
- ログファイルが作成できない:
  - permissions や LOG_DIR の設定を確認。作成に失敗するとコンソール出力のみになります。
- psutil による優先度設定で警告が出る:
  - 権限不足や OS 非対応のケースがあります。安全にスキップされます（警告ログ）。

---

追加で README に追記したい項目（例: 実行フロー図、API スキーマ、設定項目の詳細など）があれば教えてください。必要に応じてサンプル .env.example のテンプレートや systemd / supervisor 用のサービス定義の例も作成します。