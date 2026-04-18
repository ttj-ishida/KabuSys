KabuSys
=======

日本株向けの自動売買フレームワーク（ライブラリ＋運用用スクリプト群）。  
このリポジトリには、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ユーティリティ・AI を使ったニュース評価など、実運用に耐えるコンポーネント群が含まれます。

概要
----
KabuSys は以下のような機能を備えたモジュール群で構成されています。

- 研究（research）: DuckDB 上の時系列データからファクター算出や特徴量分析を行う。
- ポートフォリオ（portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制約やレジーム乗数など。
- 実行（execution）: Broker クライアントを介した発注エンジン。Paper Trading モードではモックブローカーを利用し、実運用 DB と分離。
- 監視（monitoring）: システム健全性、注文状態、リスク（ドローダウン・ポジション上限）をポーリングしてログ／アラート／Kill Switch を制御。
- AI（ai）: OpenAI を使ったニュースのセンチメント評価や市場レジーム判定。
- ユーティリティ（utils）: ロギング設定、プロセス優先度設定、設定読み込みなど。
- ツール（tools）: Paper Trading の検証レポート生成などの実行スクリプト。

主な特徴
---------
- 開発 / ペーパートレード / 本番 を想定した環境切替（KABUSYS_ENV）。
- 発注ロジックと監視ロジックの分離。監視は本番の監視 DB（SQLite）を用いる。
- Paper Trading 時は発注先と DB を完全に分離（data/paper_trading.db を使用）。
- DuckDB を分析用 DB として利用（prices_daily や raw_financials 参照）。
- OpenAI を利用したニュース NLP、レジーム判定を実装（フェイルセーフ付き）。
- ログはコンソール + 日次ローテートファイル（logs/<app>.log）で管理。
- Kill Switch 機構（data/kill.flag）で安全に ExecutionEngine を停止可能。

セットアップ
-----------

前提
- Python 3.10+ を推奨（型記法や pathlib の活用により 3.10 以降が望ましい）
- SQLite（標準ライブラリ）、DuckDB、psutil、openai 等のパッケージ

開発環境の例
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   - requirements.txt がある場合:
       pip install -r requirements.txt
   - 無い場合の最低限例:
       pip install duckdb psutil openai pyyaml

4. ディレクトリ作成（初回）
   mkdir -p data logs

環境変数 / .env
- 推奨フロー:
  1) python -m kabusys.config_setup を使って対話的に .env を作成
  2) python -m kabusys.validate_config で設定を検証

- 主要な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）

- 運用でよく使う変数（例）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/…）
  - OPENAI_API_KEY: OpenAI API を使う機能で必要
  - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用; デフォルト 60）

使い方（主要コマンド）
--------------------

1. 環境ウィザード（.env の作成）
   python -m kabusys.config_setup
   - 対話式に .env を生成・更新します。
   - 完了後、python -m kabusys.validate_config で検証するのを推奨。

2. 設定検証
   python -m kabusys.validate_config [--strict]
   - 必須環境変数、DB パス、config/*.yaml の存在などをチェック。
   - --strict をつけると警告も失敗扱い（exit code 1）になります。

3. 実行エンジン起動（ExecutionEngine）
   python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込みます。
   - 起動時に data/stop_requested.flag が存在すると起動しません。
   - 停止は data/stop_requested.flag を作成するか（または ExecutionEngine 側の Stop をトリガー）行います。
   - 実行中は data/execution.pid が記録されます（設定で変更可）。

4. 監視プロセス起動（SystemMonitor 単体）
   python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は Settings に基づく sqlite_path（監視 DB）を使用。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照します。
   - 停止は data/stop_requested.flag を作成。

5. Paper Trading 検証レポート生成
   python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
   - 稼働率、注文成功率、P95 レイテンシなどを算出して PASS/FAIL を出力。

6. AI 関連（ライブラリ呼び出し）
   - ニュース NLP（銘柄ごとのスコア算出）:
       from kabusys.ai import score_news
       score_news(duckdb_conn, target_date, api_key="...")

   - レジーム判定:
       from kabusys.ai.regime_detector import score_regime
       score_regime(duckdb_conn, target_date, api_key="...")

注意点 / 運用上の挙動
-------------------
- Paper Trading と本番 DB は分離:
  - 実行エンジン: KABUSYS_ENV=paper_trading の場合、settings.paper_sqlite_path を使う。
  - 監視: monitoring は常に settings.sqlite_path（本番監視 DB）を使用する設計です。

- Kill Switch / Stop フラグ:
  - data/kill.flag: KillSwitch（監視）から実行エンジン停止を通知するために書き込まれる。
  - data/stop_requested.flag: run_monitoring / run_execution のループ終了トリガーとして利用。
  - KillSwitch はドローダウン／ポジション上限等の閾値超過で書き込まれ、Execution 側はこれを検知して安全停止します。

- ロギング:
  - logs/ ディレクトリに app 名ごとのログ（例: logs/execution.log, logs/monitoring.log）を日次ローテーションで保存（30 日保持）。
  - setup_logging() を各スクリプトが呼び出して統一的に設定します。

- OpenAI API:
  - news_nlp / regime_detector は OPENAI_API_KEY（または api_key 引数）を必要とします。API 呼び出しはリトライ・バックオフ・フェイルセーフを備えていますが、API キー未設定はエラーとなります。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール概要です（抜粋）:

- kabusys/
  - __init__.py                      : パッケージ定義
  - config.py                        : Settings クラス（環境変数/.env 読み込み）
  - config_setup.py                  : .env 作成ウィザード
  - validate_config.py               : 設定検証 CLI
  - run_execution.py                 : ExecutionEngine 起動スクリプト
  - run_monitoring.py                : SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                     : ニュースの LLM センチメント化
    - regime_detector.py              : 市場レジーム判定（MA + LLM）

  - monitoring/
    - monitoring_db.py                : SQLite の永続化層（テーブル定義/CRUD）
    - system_monitor.py               : CPU/Mem/Disk/データ鮮度監視
    - trade_monitor.py                : （注文関連の監視ロジック）
    - risk_monitor.py                 : ドローダウン・ポジション上限監視
    - kill_switch.py                  : Kill Switch ロジック（flag 書込み）
    - monitoring_engine.py            : 監視コンポーネント統合（Polling）

  - execution/                        : 発注エンジン、OrderManager 等（詳細省略）
  - portfolio/
    - portfolio_builder.py            : 候補選定、重み付け
    - position_sizing.py              : 株数計算、資金配分ロジック
    - risk_adjustment.py              : セクター上限・レジーム乗数

  - research/
    - factor_research.py              : Momentum / Volatility / Value 等ファクター算出
    - feature_exploration.py          : 将来リターン計算・IC・統計サマリ

  - tools/
    - paper_verification_report.py    : Paper Trading 検証レポート生成 CLI

  - utils/
    - logging_setup.py                : 共通ロギング設定
    - process_priority.py             : プロセス優先度 / CPU affinity

ドキュメント／設計参照
---------------------
- PortfolioConstruction.md や StrategyModel.md 等の設計ドキュメントに準拠した実装方針が各モジュールにコメントとして記載されています（リポジトリ内のドキュメントを参照してください）。

開発メモ / 拡張ポイント
-----------------------
- ファイル・DB パスは Settings 経由で柔軟に上書き可能。
- DuckDB テーブル（prices_daily, raw_financials, raw_news 等）を整備すれば research / ai の機能が動作します。
- 将来的な改良案:
  - 銘柄ごとの lot_size を stocks マスタで管理する設計への拡張（position_sizing）
  - OpenAI レスポンスの厳密検証・再試行の改善
  - systemd / supervisor での自動起動ユニットの提供

ライセンス
---------
（ここにプロジェクトのライセンスを明記してください）

問い合わせ / 貢献
-----------------
バグ報告や改善提案は Issue を立ててください。プルリク歓迎です。

以上。README に不足しているコマンドや環境変数の情報があれば教えてください。必要に応じて実行例（systemd ユニットや docker-compose 等）も追記します。