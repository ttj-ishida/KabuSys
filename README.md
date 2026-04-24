# KabuSys — 日本株自動売買システム (README)

バージョン: 0.1.0

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリおよび運用用スクリプト群を含みます。  
README ではプロジェクト概要、主な機能、セットアップ手順、起動/利用方法、ディレクトリ構成を日本語でまとめます。

※ 本 README はソースコード中の docstring / コメントを元に作成しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要な依存パッケージ（目安）
- セットアップ手順
- 環境変数 / .env の扱い
- 使い方（コマンド例）
- 停止・Kill スイッチについて
- ディレクトリ構成（主要ファイル一覧）
- 補足・注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたシステムで、戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視 (Monitoring) 、および AI を使ったニュース解析などの機能を備えています。
- DuckDB を分析用 DB、SQLite を監視や注文ログ用に利用します。実行環境（開発 / ペーパー / 本番）を切り替えられる設計です。

主な機能一覧
- 環境設定ウィザード (.env 生成): kabusys.config_setup
- 設定検証 CLI: kabusys.validate_config
- Execution エンジン起動スクリプト: kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と分離された data/paper_trading.db に記録
- Monitoring ポーリングループ起動スクリプト: kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視機能群:
  - SystemMonitor: CPU / メモリ / ディスク監視、データ鮮度、実プロセスの生存確認等
  - TradeMonitor: 発注ログや滞留注文/約定異常の検出（詳細はコード参照）
  - RiskMonitor: ドローダウン監視・ポジション数上限監視、リスクイベント記録
  - KillSwitch: リスク条件発動時に data/kill.flag を書き込み Execution を安全停止
  - MonitoringEngine: 上記をまとめて定期実行、AlertManager 経由で通知
- ポートフォリオ構築ユーティリティ:
  - 候補選択、等配分/スコア加重、セクターキャップ、レジーム乗数、ポジションサイズ計算
- 研究用モジュール:
  - ファクター計算 (momentum/value/volatility)
  - 将来リターン / IC / 統計サマリ
- AI 関連:
  - news_nlp によるニュースのセンチメント解析（OpenAI を使用）
  - regime_detector: ETF MA とマクロニュースを統合して市場レジーム判定
- ツール:
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを出力

必要な依存パッケージ（目安）
- duckdb
- psutil
- openai
- PyYAML（config 検証時にあると詳細検査が可能）
- （お使いの environment にあわせて）sqlite3 は標準ライブラリ
※ requirements.txt はプロジェクトに含めてください（この README はソースから推測した依存を列挙しています）。

セットアップ手順（ローカル・開発向け）
1. リポジトリをクローンし、作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは最低限: pip install duckdb psutil openai pyyaml
4. .env を作成
   - 自動で読み込みを行う設計だが、.env がない場合はウィザードを利用:
     - python -m kabusys.config_setup
   - その後、設定を検証:
     - python -m kabusys.validate_config
     - --strict オプションを付けると警告もエラー扱い
5. data/ ディレクトリ等の作成（必要なら）
   - 多くのスクリプトは起動時に data/ や logs/ を作成しますが、権限等の理由で手動で作ると安全です。

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live
- DB パス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring 用
  - PAPER_TRADING_SQLITE_PATH (paper_trading 時の専用 DB、デフォルト: data/paper_trading.db)
- ログ:
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- OpenAI:
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）
- その他:
  - MONITOR_POLL_INTERVAL（run_monitoring ポーリング間隔秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START（本番環境での Kill Flag 自動クリア制御: 0/1）
- 自動 .env ロード:
  - デフォルトではプロジェクトルートの .env / .env.local を自動で読み込みます。
  - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（コマンド例）
- 環境セットアップウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict
- ExecutionEngine 起動（通常はサービス/daemon として起動）
  - python -m kabusys.run_execution
  - paper_trading モードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Execution は起動時に data/execution.pid へ PID を書くことがあります。起動前に data/stop_requested.flag があると起動しません。
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変える例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に参照します（環境にかかわらず）。
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- AI 系 (プログラムから呼ぶ)
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key 省略時は OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

停止・Kill スイッチについて
- 実行中の ExecutionEngine / Monitoring は次のようなフラグファイルで制御されます:
  - data/stop_requested.flag: run_monitoring / run_execution のループを検知して安全に停止します。ファイルを作成すると次回のポーリング/ループで停止します。
  - data/kill.flag: KillSwitch（リスク条件）により書き込まれ、ExecutionEngine 側で停止トリガーとして扱われます。
- KillSwitch は RiskMonitor の判定（例: ドローダウン閾値超過やポジション上限超過）で kill.flag を作成します。kill.flag があると Execution は停止する設計です。必要に応じて kill.flag を手動で消去できます（Settings.kill_flag_clear_on_start が 1 の場合は起動時に自動クリアされますが、本番では 0 推奨）。

ログ
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存されます（TimedRotatingFileHandler、30 日保持）。
- app_name に応じて logs/<app_name>.log が作られます（例: execution.log, monitoring.log）。
- コンソール出力は stdout に出ます（daemon/systemd からのリダイレクトに配慮）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite による監視ログ永続化層
    - system_monitor.py      — システム監視
    - trade_monitor.py       — （存在する前提）発注監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （存在する前提）通知管理
  - execution/
    - execution_engine.py    — ExecutionEngine コア
    - order_manager.py       — 発注管理
    - order_repository.py    — 注文リポジトリ
    - reconciler.py          — 発注整合処理
    - broker_factory.py      — ブローカークライアント生成
    - risk_manager.py        — 実行時リスク管理
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・規模調整
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - data/                    — 実行時に使用する DB / flag / pid など（data/*.db, *.flag, *.pid）
  - logs/                    — ログ出力先（デフォルト）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

補足・注意点
- paper_trading モードは本番 DB と分離され、発注はモックブローカーを通じて処理します。PAPER_TRADING_SQLITE_PATH を指定し、本番 DB と完全に分離してください。
- OpenAI を利用する機能（news_nlp, regime_detector）を使う場合は OPENAI_API_KEY の設定が必要です。API 呼び出しはリトライやフォールバックを備えていますが、API キー未設定だと例外を出す箇所があります。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を基準に行われます。CWD に依存せず設計されています。
- ローカルで試す場合はまず config_setup → validate_config を実行して設定を確認してください。
- 実運用では systemd 等のプロセスマネージャで run_execution / run_monitoring を監視・再起動する形が想定されます。ログや data/stop_requested.flag による手動制御も可能です。

ライセンス、コントリビューション、テスト等についてはリポジトリ上の該当ファイル（LICENSE, CONTRIBUTING.md, tests/）を参照してください（存在する場合）。

以上。README を読んで不明点があれば、実行したいユースケース（ローカル検証 / ペーパートレード / 本番運用）を教えてください。セットアップや systemd ユニットの例など、より具体的に補足します。