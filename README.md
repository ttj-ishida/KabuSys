README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン (ExecutionEngine) — 発注、注文管理、リスク制御（paper/live 切替対応）
- 監視 (Monitoring) — システム稼働監視、注文監視、リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ — 候補選定・重み付け・株数計算・セクター制約など
- リサーチ用モジュール — ファクター計算、将来リターン、IC、統計サマリー
- AI ユーティリティ — ニュースの NLP スコアリング、レジーム判定（OpenAI 利用）
- 開発支援ツール — .env 作成ウィザード、設定検証、ペーパートレード検証レポート

特徴
----
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切替。paper_trading は paper 専用の SQLite を使用して本番 DB と分離します。
- フェイルセーフ: AI 呼び出しや外部 API エラーは基本的にフェイルセーフ（失敗時はフォールバックして継続）を志向。
- 冪等性・簡易マイグレーション: monitoring DB 初期化やカラム追加に対応。
- ロギング統一: 全スクリプトで共通の setup_logging を使用し、コンソール＋日次ローテーションログを出力。
- 簡単な CLI: 環境設定ウィザード、設定検証、ペーパートレード検証レポートを CLI で提供。

動作要件
-------
- Python 3.10 以上（ソースで | 型やモダンな構文を使用しているため）
- 必要 Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML のパースを行う場合）
- SQLite（Python 標準ライブラリの sqlite3 を利用）
- ネットワークアクセス（kabuステーション API、J-Quants、OpenAI を使う場合）

セットアップ手順
--------------
1. リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   pip install duckdb psutil openai PyYAML

   ※プロジェクトに requirements.txt がある場合はそれを使用してください:
   pip install -r requirements.txt

4. .env を作成（対話式ウィザード推奨）:
   python -m kabusys.config_setup

   ウィザードで作成した .env に最低限設定が必要な環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）

5. 設定検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

主要な環境変数（代表）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う機能（ai.news_nlp / ai.regime_detector）の API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------

環境設定
- 対話式 .env 作成:
  python -m kabusys.config_setup

設定検証
- 設定を検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

監視プロセス起動
- SystemMonitor のポーリングループを起動:
  python -m kabusys.run_monitoring

  振る舞い:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使います（環境にかかわらず）
  - data/stop_requested.flag が存在するとループを終了します

実行エンジン起動
- ExecutionEngine を起動:
  python -m kabusys.run_execution

  振る舞い:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動を中止
  - 実行中に stop flag を検知すると engine.stop() を呼んで停止します
  - 実行時は data/execution.pid が利用されます（PID ファイルの扱いは Settings.pid_file_path で制御）

ペーパートレード検証レポート
- ペーパートレードの検証レポートを生成:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 機能
- ニュース NLP スコアリング:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY 環境変数または api_key 引数でキーを指定する必要があります。
- レジームスコア:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

Kill Switch / 停止フラグ
- KillSwitch は data/kill.flag を生成して ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path）。
- 管理側で明示的に kill.flag を削除（clear）するまで残るため、本番運用時は KILL_FLAG_CLEAR_ON_START の扱いに注意してください（本番では自動クリアを無効化することを推奨）。

ログ
- 共通ロギング: kabusys.utils.logging_setup.setup_logging を使用
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションログ: logs/<app_name>.log（デフォルト、30 日保持）
- LOG_DIR 環境変数でログディレクトリを変更可能

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py                 — パッケージ定義
    config.py                   — Settings / .env 自動ロード
    config_setup.py             — .env 対話ウィザード
    validate_config.py          — 起動前の設定検証 CLI
    run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
    run_execution.py            — ExecutionEngine 起動スクリプト
    tools/
      paper_verification_report.py — ペーパートレード検証レポート
    utils/
      logging_setup.py          — 共通ロギング設定
      process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
    monitoring/
      monitoring_db.py          — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
      monitoring_engine.py      — 各 Monitor を束ねるエンジン
      system_monitor.py         — システム状態・データ鮮度監視
      risk_monitor.py           — ドローダウン・ポジション上限監視
      kill_switch.py            — kill.flag の書き込みロジック
      (trade_monitor.py 等)    — 注文監視コンポーネント（参照される）
    execution/
      (broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager) — 実行系コンポーネント
    portfolio/
      portfolio_builder.py      — 候補選定・重み計算
      risk_adjustment.py        — セクターキャップ・レジーム乗数
      position_sizing.py        — 株数算出・上限・丸め・スケーリング
    research/
      factor_research.py        — Momentum/Value/Volatility ファクター計算
      feature_exploration.py    — 将来リターン / IC / 統計サマリー
    ai/
      news_nlp.py               — ニュース NLP スコアリング（OpenAI）
      regime_detector.py        — レジーム判定（OpenAI + ETF MA 合成）
    data/                        — 実行時に生成されることが想定されるディレクトリ（DB・flag・pid 等）
    logs/                        — デフォルトのログ出力先

開発者向けメモ / 注意点
----------------------
- プロジェクトルート判定: config._find_project_root() は .git または pyproject.toml を基準にルートを特定します。配布パッケージ化後も動くように CWD に依存しない設計です。
- .env 自動ロード: デフォルトで .env と .env.local を自動読み込みします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db() は既存カラムが無ければ ALTER TABLE で追加する簡易マイグレーションを行います。
- OpenAI 呼び出しはリトライ・JSON 検証を行い、失敗しても例外を上位にあげないフォールバック実装が多く含まれます（フェイルセーフ設計）。

ライセンス / 貢献
-----------------
（ここにライセンスと貢献方法を記載してください）

以上。README に記載した各 CLI / モジュールを参照し、実際の運用前には必ず python -m kabusys.validate_config で設定を検証してください。