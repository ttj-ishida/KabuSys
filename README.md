# KabuSys — README

KabuSys は日本株向けの自動売買 / リサーチ / モニタリング用ライブラリ群です。本リポジトリは発注エンジン、監視エンジン、ポートフォリオ構築・リスク管理ロジック、リサーチ用ファクター計算、LLM を使ったニュース NLP 等を含むモジュール群で構成されています。

バージョン: 0.1.0

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・コマンド）
- 環境変数（主要な設定）
- 停止・Kill スイッチの挙動
- ディレクトリ構成（抜粋）
- 注意事項

---

## プロジェクト概要
KabuSys は取引エンジン（ExecutionEngine）とそれを監視する MonitoringEngine、ポートフォリオ構成／サイズ決定ロジック、リサーチ（ファクター計算・特徴量解析）、および OpenAI を利用したニュースセンチメント／レジーム判定モジュールを含むパッケージです。

設計上の特徴:
- 本番用／ペーパートレード用を分離（paper_trading モードでは専用 SQLite DB を使用）
- DuckDB を分析用途、SQLite を監視・発注履歴用に利用
- .env / .env.local を使った環境変数管理（自動ロード機能）
- プロセス優先度設定、ログ出力設定、ファイルベースの Kill/Stop フラグによる安全停止機構

---

## 主な機能（一覧）
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
  - プロセス優先度の設定、PID ファイル管理、停止フラグ監視
- MonitoringEngine / SystemMonitor（run_monitoring）
  - CPU / メモリ / ディスク / データ鮮度 / Execution プロセスの生存監視
  - SQLite（monitoring.db）へ履歴を保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能
- KillSwitch（自動停止トリガー）
  - ドローダウンやポジション上限等の条件で data/kill.flag を書き込み ExecutionEngine を停止させる
- RiskMonitor / TradeMonitor
  - ドローダウン検出、ポジション上限、滞留注文・約定異常の検出
- ポートフォリオ構築ユーティリティ
  - 銘柄選定、等金額/スコア加重、リスクベースのポジションサイズ計算、セクターキャップ、レジーム乗数
- Research（ファクター計算）
  - Momentum / Volatility / Value 等のファクターを DuckDB 経由で計算
  - forward returns、IC（情報係数）、統計サマリ等
- AI モジュール
  - news_nlp: OpenAI を用いたニュースのセンチメントスコアリング（ai_scores 書き込み）
  - regime_detector: MA200 とマクロニュースセンチメント合成による市場レジーム判定
- ユーティリティ
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前の設定チェック（.env / config/*.yaml）
  - tools.paper_verification_report: ペーパートレードログからの検証レポート生成

---

## セットアップ手順（開発 / 実行環境）
前提:
- Python 3.10+
- system に sqlite3（標準ライブラリ）、DuckDB、psutil、openai 等をインストール

推奨パッケージ例:
pip install duckdb psutil openai

（validate_config の YAML 検証を有効化する場合）
pip install PyYAML

1. リポジトリをクローンして作業ディレクトリを移動
2. .env を用意する
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
3. 主要な環境変数を設定（下記「環境変数」参照）
4. 設定検証:
   python -m kabusys.validate_config
   （警告を失敗扱いにしたい場合は --strict を付ける）
5. DuckDB / SQLite のデフォルトパスは data/ 以下。必要ならディレクトリを作成

---

## 使い方（主なコマンド）
- ExecutionEngine（本番／ペーパー）起動:
  python -m kabusys.run_execution

  実行時の挙動:
  - KABUSYS_ENV が paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
  - 起動時に data/stop_requested.flag が存在すると起動を停止
  - 実行中は data/execution.pid に PID を書き、停止は data/stop_requested.flag を作成することで行う

- Monitoring 起動（ポーリング監視）:
  python -m kabusys.run_monitoring

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）

- 設定ウィザード（.env 生成）:
  python -m kabusys.config_setup

- 設定検証 CLI:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db PATH で SQLite ファイルを指定可能（デフォルト: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

ログ:
- デフォルトログディレクトリ: logs/
- アプリ名ごとにファイルを出力（例: logs/execution.log, logs/monitoring.log）
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御

実行例（Unix シェル）:
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution &

停止（手動でループを止める場合）:
touch data/stop_requested.flag

KillSwitch をトリガーして ExecutionEngine に停止させる場合は KillSwitch が data/kill.flag を書き込む（Monitoring から自動的に）。

---

## 環境変数（主要）
自動読み込み:
- プロジェクトルートにある .env と .env.local を自動で読み込み（OS 環境変数が優先）
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション（抜粋）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（例: INFO）
- OPENAI_API_KEY — OpenAI API Key（news_nlp / regime_detector で利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート用（任意）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading 時の fill 動作（instant | partial | never | reject）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- PID_FILE_PATH — execution の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

validate_config では .env や config/*.yaml の存在や基本整合性をチェックします（PyYAML があれば YAML 内容のパース検証も実施）。

---

## 停止・Kill スイッチの挙動
- stop_requested.flag
  - run_monitoring / run_execution のループがこれを検知すると正常に終了する（グレースフルシャットダウン）
  - パス: data/stop_requested.flag（スクリプト内で相対参照）

- kill.flag
  - Monitoring の KillSwitch により条件を満たすと data/kill.flag が書き込まれる
  - ExecutionEngine は起動時や監視ループ内で kill.flag を検知し停止する
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアされる（本番では危険）

- PID ファイル
  - run_execution は data/execution.pid に PID を書きます。外部ツールからの監視や stale PID の検出に利用されます。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 下の主要ファイルとモジュールの抜粋です。

src/kabusys/
- __init__.py
- config.py                — 環境変数・.env 自動ロードロジック、Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — OpenAI ベースのニューススコアリング
  - regime_detector.py     — マクロ + MA200 によるレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite の監視ログ永続化層
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

data/ 以下（実行時に使用／作成される想定）
- data/monitoring.db         — デフォルトの監視 SQLite DB
- data/paper_trading.db      — paper_trading 用 DB（設定次第）
- data/kabusys.duckdb        — DuckDB ファイル（デフォルト）
- data/execution.pid         — ExecutionEngine の PID
- data/kill.flag             — KillSwitch が書き込むフラグ
- data/stop_requested.flag   — 手動停止用フラグ

logs/（ログ出力先のデフォルト）

---

## 注意事項 / 運用上のポイント
- KABUSYS_ENV=live を使用する場合は設定ミスが重大被害に直結します。validate_config で入念にチェックしてください。
- .env は機密情報を含むため Git にコミットしないでください（config_setup は生成時にこの点を注意喚起します）。
- OpenAI を使うモジュールは API キーが必要です。API 呼び出しは外部サービス依存であり、失敗時の処理やレート制限に注意しています（リトライ・フェイルオープンの設計あり）。
- paper_trading モードは本番 DB と完全分離されるよう設計されています。ペーパー取引データは data/paper_trading.db に保存されます。
- MONITOR_POLL_INTERVAL などのパラメータで監視感度を調整できます。短くしすぎると負荷や API レートに影響する可能性があるため注意してください。
- ログディレクトリの作成に失敗した場合はコンソール（stdout）出力のみになります。ログディレクトリ権限等を確認してください。

---

この README はコードベースの現状に基づく概要ガイドです。より詳細な設計やアルゴリズム仕様は各モジュール内の docstring / コメントを参照してください。必要であれば、README に具体的な運用手順（systemd ユニット例、cron / Supervisor 設定例、Dockerfile など）を追記できます。希望があれば教えてください。