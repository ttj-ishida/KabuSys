README
======

概要
----
KabuSys は日本株向けの自動売買および研究ツール群をまとめた Python パッケージです。本リポジトリは以下の主要機能を含みます:

- 実行エンジン（ExecutionEngine）起動スクリプト（発注／リスク管理／注文管理）
- 監視（Monitoring）コンポーネント（システム状態・注文・リスク監視、Kill Switch）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- 研究用モジュール（ファクター計算・特徴量探索）
- ニュース NLP / 市場レジーム判定（OpenAI を使ったスコアリング）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定、プロセス優先度 等）
- Paper Trading 用検証レポート生成ツール

特徴一覧
--------
主な機能と特長:

- Execution / Monitoring を分離して常駐監視と発注を管理
- Paper Trading（KABUSYS_ENV=paper_trading）時は実際のブローカーとは分離された専用 SQLite DB を使用
- Kill Switch による安全停止（data/kill.flag）
- 監視ログは SQLite（デフォルト data/monitoring.db）に永続化。DuckDB は分析用（data/kabusys.duckdb）
- AI モジュール（news_nlp, regime_detector）は OpenAI を利用し、失敗時はフェイルセーフで継続
- ポートフォリオ構築 / リスク調整 / ポジションサイズ決定は純粋関数でテスト容易
- config_setup.py による対話式 .env 生成支援、validate_config による設定検証
- ロギングは統一的に設定（TimedRotatingFileHandler と stdout 両対応）

セットアップ手順
----------------

1. 開発環境（推奨）
   - Python 3.10+ を推奨（型ヒントに | 演算子を使用しているため）
   - 仮想環境を作成して有効化する（venv / poetry 等）

    例:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil openai
   - YAML を使う機能を使うなら PyYAML も: pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env の作成
   - 対話式ウィザードで作成:
       python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要なオプション・デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
   - .env の自動読み込み:
     - デフォルトで .env / .env.local を自動で読み込みます（OS 環境変数が優先）
     - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. ディレクトリ作成（必要なら）
   - data/ と logs/ は自動作成されますが、権限や環境によっては手動で用意してください。

使い方
------

起動スクリプト（常駐系）
- ExecutionEngine を起動（実行環境により挙動が変わる）:
    - python -m kabusys.run_execution
  説明:
    - 起動時にプロセス優先度を "high" に設定し、Settings から環境変数を読み込みます。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。
    - data/stop_requested.flag があると起動せず終了。実行中に stop_requested.flag が作成されるとエンジンの停止をトリガーします。
    - 実行中は data/execution.pid に PID を書きます（設定によりパスは変更可能）。

- Monitoring を起動（定期ポーリング）:
    - MONITOR_POLL_INTERVAL を秒数で指定可能（デフォルト 60 秒）
    - python -m kabusys.run_monitoring
  説明:
    - 監視ループは MONITOR_POLL_INTERVAL 環境変数で間隔を変更可。
    - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを操作します。
    - data/stop_requested.flag を検知すると監視ループは終了します。

設定ツール / 検証
- 対話式 .env ウィザード:
    - python -m kabusys.config_setup
- 設定検証:
    - python -m kabusys.validate_config
    - --strict を付けると警告も FAIL 扱いで exit code 1 を返します

分析 / ツール
- Paper Trading 検証レポート生成:
    - python -m kabusys.tools.paper_verification_report
    - オプション:
      --from YYYY-MM-DD
      --to   YYYY-MM-DD
      --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数で指定可能）
    - Paper Trading 用の SQLite DB（デフォルト data/paper_trading.db）を解析して稼働率・約定率・レイテンシ等を出力します。

ライブラリ API（例）
- AI スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)  # api_key が None の場合は OPENAI_API_KEY を参照
- 市場レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
- 研究用 / ファクター:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

監視・停止仕組み（Kill Switch / Flag）
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止指示を与えます。
  - ExecutionEngine 側では起動時にこのフラグの存在を確認し、存在する場合は起動しません（安全策）。
- stop_requested.flag:
  - run_execution.py / run_monitoring.py のトップレベルで参照される停止フラグ（data/stop_requested.flag）。存在するとループを終了します。
- PID ファイル: data/execution.pid（実行時に書き込まれる）。

ログ
----
- ログはデフォルトで logs/ に出力されます（アプリ名ごとに daily ローテーション: <app_name>.log）。
- コンソール出力は stdout に書かれます。ログレベルは環境変数 LOG_LEVEL（または .env）で制御可能。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はパッケージの主要構成（src/kabusys 配下）です。省略して要点のみ記載しています。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理 (.env 自動ロード含む)
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - logging_setup.py      — ログ初期化ユーティリティ
    - process_priority.py   — プロセス優先度／CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — SQLite テーブル定義・永続化層
    - system_monitor.py     — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py      — 注文監視（存在ファイル参照）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — Kill Switch 実装（kill.flag 書込）
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
  - execution/              — 発注関連（Engine / OrderManager 等）※詳細はコード参照
  - portfolio/
    - portfolio_builder.py  — 候補選定 / 等重 / スコア重み
    - position_sizing.py    — 株数計算・キャップ・lot 切り捨て
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
    - feature_exploration.py— 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py    — 市場レジーム判定（MA + LLM 合成）
  - data/ (実行時に作成されることが想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - stop_requested.flag / kill.flag / execution.pid など

注意事項 / 運用上のヒント
-----------------------
- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。API 失敗時はフェイルセーフで処理を継続するよう設計されていますが、結果の信頼性に注意してください。
- Paper Trading モードは本番 DB と分離されるため、検証目的で安心して使用できます。
- DuckDB は分析用（prices_daily / raw_financials / raw_news 等のテーブル参照）です。事前にデータ投入が必要です。
- ログディレクトリや data ディレクトリへの書き込み権限を確認してください。権限不足でファイル出力ができない場合、ログは stdout のみになります。

よく使うコマンド例
------------------
- .env を対話式で作る:
    python -m kabusys.config_setup
- 設定を検証する:
    python -m kabusys.validate_config
- Execution を起動する:
    python -m kabusys.run_execution
- Monitoring を起動する（ポーリング間隔を 30 秒にする例）:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート生成（期間指定）:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（この README ではソースリポジトリのライセンスや貢献ガイドは明記していません。必要なら LICENSE / CONTRIBUTING ファイルを追加してください。）

補足
----
ここに記載している内容はコードベース（src/kabusys 配下）を参照してまとめた概要です。実際の運用前には必ず python -m kabusys.validate_config で設定を検証し、必要なデータベース・テーブル・OpenAI キー等が整っていることを確認してください。もし README に追加してほしい操作例や CI / デプロイ手順の要望があれば教えてください。