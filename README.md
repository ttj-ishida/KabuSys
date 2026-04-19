README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（本番 / ペーパートレード）、監視・アラート、ニュースの NLP スコアリングなどの機能を備えています。設計上は以下を重視しています。

- 本番とペーパートレードの分離（DB、ブローカーモック）
- DuckDB を用いたリサーチ / ファクター計算
- SQLite による監視・ログ永続化
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントやレジーム判定（オプション）
- 環境変数 / .env による設定管理と対話式セットアップ・検証ツール

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードの切替
  - BrokerClientFactory によるブローカー分離
  - OrderManager / RiskManager / Reconciler を組み合わせた実行ロジック
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス生存確認）
  - TradeMonitor（発注ログ監視・滞留注文検出）
  - RiskMonitor（ドローダウン監視、ポジション上限検出）
  - KillSwitch（条件で data/kill.flag を書き込むことで Execution を停止）
  - MonitoringEngine によるポーリングとアラート連携
- Portfolio モジュール
  - 候補選定、等重/スコア加重配分、位置づけサイズ計算、セクターキャップ、レジーム乗数
- Research モジュール
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリ
- AI モジュール（オプション）
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを用いた日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力
- 設定ユーティリティ
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前の設定検証 CLI

前提 / 必要なパッケージ
---------------------
必須（最低）:
- Python 3.9+（利用する型ヒント・一部ライブラリに依存するため高めのバージョンを推奨）
- pip

主要 Python パッケージ（プロジェクトに応じてインストール）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML を検証したい場合）
これらは次のようにインストールできます:
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install duckdb psutil openai PyYAML

.env / 設定について
-------------------
- 環境変数で設定を行います。推奨はリポジトリルートに .env を置くことです。
- 自動ロード順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 必須環境変数の一例:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要設定:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視DB）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用）
  - OPENAI_API_KEY: OpenAI を使う場合必須
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用、デフォルト 60）
- 設定支援:
  - python -m kabusys.config_setup で対話式ウィザードを実行して .env を生成できます。
  - python -m kabusys.validate_config で設定（.env や config/*.yaml）の検証ができます。

セットアップ手順
--------------
1. リポジトリをクローン
    git clone <repo-url>
    cd <repo-root>

2. 仮想環境を作成して有効化
    python -m venv .venv
    source .venv/bin/activate  # Windows の場合は .venv\Scripts\activate

3. 必要パッケージをインストール
    pip install duckdb psutil openai PyYAML

   ※ requirements.txt があれば
    pip install -r requirements.txt

4. .env を作成
   - 対話式: python -m kabusys.config_setup
   - または .env.example を参考に手動で作成

5. 設定検証（任意）
    python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

6. データディレクトリの確認
   - デフォルトで data/ と logs/ を使います。起動時に自動作成される場合があります。

基本的な使い方
--------------
実行（ExecutionEngine）
- 本番 / ペーパートレードの起動:
  - 本番: KABUSYS_ENV=live を .env に設定してから:
        python -m kabusys.run_execution
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ
    発注ログは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。

- 停止:
  - Execution は data/stop_requested.flag または data/kill.flag 等のフラグで制御できます。
  - KillSwitch は条件を満たすと data/kill.flag に理由を書き込み、次回起動で停止シグナルを送ります。

監視（Monitoring）
- 監視ループ起動:
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使います（環境に依存せず）。

ツール: Paper Trading レポート
- ペーパートレード DB の検証レポートを生成:
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 機能
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）が必要です。
- 使用モデル: gpt-4o-mini（コード中にハードコーディング）
- 失敗時はフェイルセーフ（スコア 0.0 or スキップ）で動作するよう設計されています。

ログ
----
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- デフォルトログディレクトリ: logs/
- アプリ名ごとにファイルを出力（例: logs/execution.log, logs/monitoring.log）
- 標準出力（stdout）にも出力されます。

停止・Kill フラグの仕組み
-----------------------
- data/stop_requested.flag: run_execution/run_monitoring の外部停止用（スクリプト内で参照）
- data/kill.flag: KillSwitch が書き込む実行停止フラグ（ExecutionEngine に停止シグナルを送る）
- PID ファイル: data/execution.pid にプロセス ID を書き出して管理します

トラブルシューティング（よくある問題）
----------------------------
- 環境変数未設定エラー:
  - JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD などが未設定だと validate_config や起動時にエラーになります。
- 権限関連:
  - プロセス優先度設定（psutil による nice()/Windows 優先度設定）は権限不足で警告が出ますが、動作自体は継続します。
- DuckDB / SQLite のパス:
  - 指定したパスの親ディレクトリが存在しないと警告が出ます。起動時に自動作成される場合がありますが、必要に応じて事前に作成してください。
- PyYAML 未インストール:
  - validate_config は PyYAML が無い場合、config/*.yaml の中身検証をスキップします（警告）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールと役割の簡易一覧です（src/kabusys を想定）。

- kabusys/
  - __init__.py                     — パッケージ初期化（バージョン等）
  - config.py                        — 環境変数・設定管理（.env 自動読み込み・Settings）
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — ペーパートレード検証レポート
  - data/ (モジュール想定; 実装により存在)
    - pipeline.py                    — get_last_price_date 等（参照される）
    - stats.py                       — zscore_normalize 等（research で参照）
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み
    - position_sizing.py             — 株数決定・資金割当
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — momentum/volatility/value 計算
    - feature_exploration.py         — forward returns, IC, summary
  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング
    - regime_detector.py             — 市場レジーム判定
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層（init + MonitoringDB）
    - system_monitor.py              — システム状態監視
    - trade_monitor.py               — 発注ログ監視（参照）
    - risk_monitor.py                — ドローダウン監視
    - kill_switch.py                 — KillSwitch 実装
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - alert_manager.py               — アラート送信（実装依存）
  - execution/
    - execution_engine.py            — ExecutionEngine 本体（run_session 等）
    - broker_factory.py              — BrokerClientFactory（実ブローカー / モック）
    - order_manager.py               — Order 管理ロジック
    - order_repository.py            — DB 永続化（orders）
    - reconciler.py                  — 差分整合処理
    - risk_manager.py                — リスク判定ロジック
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ

ライセンス / 貢献
----------------
- この README ではライセンス情報は含めていません。リポジトリの LICENSE を参照してください。
- 貢献やバグ修正は Pull Request / Issue を通じてお願いします。

最後に
------
本ドキュメントはコードベースの主要な使い方と構成をまとめたものです。実際の運用では本番環境（KABUSYS_ENV=live）での設定は慎重に行い、validate_config による事前検証、ログ・監視の確認、KillSwitch の動作確認を行ってください。