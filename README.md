KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）の実装です。  
モジュール構成は、発注実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・リサーチ、AI（ニュース NLP / レジーム判定）などで構成されています。

概要
----
KabuSys は以下の責務を持つコンポーネント群で構成されます。

- ExecutionEngine: ブローカークライアント経由での発注・注文管理・リスク管理・和解（reconciler）。
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite DB に記録します（本番 DB と分離）。
- Monitoring: システム状態・データ鮮度・注文ログ・リスク制御を定期チェックし、必要に応じてアラート送信や Kill Switch（停止フラグ）を発動します。
- Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群。
- Research: DuckDB 上の価格・財務データからファクター計算・特徴量探索を行うモジュール。
- AI: OpenAI API を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- Tools: レポート生成スクリプトなど（例: ペーパートレード検証レポート）。

主な機能
--------
- System monitoring: CPU/MEM/DISK、Execution プロセスの生存、株価データ鮮度の監視（system_monitor）。
- Trade monitoring: 注文の滞留／約定異常検出、取引ログの永続化（monitoring_db）。
- Risk monitoring: ドローダウン、ポジション上限などの監視とリスクログ記録。
- Kill Switch: 重大リスク時に data/kill.flag を作成して ExecutionEngine に停止シグナルを送信。
- Paper trading サポート: paper_trading 環境は本番 DB と分離（data/paper_trading.db）。
- AI スコアリング: news_nlp により銘柄別センチメントを ai_scores テーブルに書き込み。
- Research utilities: momentum/volatility/value ファクター計算、IC/ランク相関、統計サマリー。
- ロギング: stdout と日次ローテートファイル出力（logs/）を統一的に設定。

前提条件
--------
- Python 3.9+
- 主要依存パッケージ（例）
  - duckdb
  - openai (AI 機能を使う場合)
  - psutil
  - PyYAML（設定検証で YAML の検証を行う場合）
- SQLite（標準ライブラリに含まれます）
- ネットワーク接続（ブローカー API / OpenAI を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - 実運用時はプロジェクトに合わせて必要パッケージを追加してください。

4. 環境変数 (.env) の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートの .env を作成できます（.env を絶対にリポジトリにコミットしないでください）。
   - 必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY（news_nlp / regime_detector で使用）
   - 主要な環境変数の例:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - data/ と logs/ は自動作成される場合が多いですが、権限問題がある環境では事前に作成してください。

使い方
------
- Execution Engine の起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を出します。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルを操作します。
    - 監視ループが停止するには data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - デフォルト DB: data/paper_trading.db

- .env 作成 / 検証
  - .env の対話作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config

- AI 機能（news_nlp, regime_detector）
  - OPENAI_API_KEY が必要です（引数からも渡せます）。
  - コスト・レート制限に注意して運用してください。API エラー時はフォールバック処理（例: スコア未取得やデフォルト値）があります。

停止 / Kill Switch
------------------
- 停止・シャットダウンのためのフラグ:
  - data/stop_requested.flag — 実行ループ（run_execution/run_monitoring）が存在を検知して順次終了します。
  - data/kill.flag — KillSwitch が作成するファイル。ExecutionEngine 側で検知して安全に停止します（設定により起動時に自動クリアするオプションあり）。
- Settings で以下を制御可能:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）。

設定の主要ポイント
------------------
- KABUSYS_ENV
  - development: 開発用（発注なし）
  - paper_trading: ペーパートレード（発注はモック、DBは paper_trading 用）
  - live: 本番（実際に発注）
- PAPER_FILL_MODE（paper_trading 用）
  - instant / partial / never / reject
- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒、デフォルト 60）
- ログ
  - logs/<app_name>.log に日次ローテートで出力
  - LOG_LEVEL 環境変数でログレベルを指定

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定読み込みロジック（Settings クラス）
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 起動前設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring 起動スクリプト

サブパッケージ（主な内容）
- ai/
  - news_nlp.py                 — ニュース NLP（OpenAI）による銘柄センチメント
  - regime_detector.py          — マクロ + ETF MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py            — SQLite 永続化層（テーブル初期化・CRUD）
  - system_monitor.py           — システム監視・データ鮮度チェック
  - trade_monitor.py            — 注文ログ・滞留注文検出（存在）
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — Kill Switch 実装（flag 書込）
  - monitoring_engine.py        — 各 Monitor を統合するエンジン
  - alert_manager.py            — （アラート送信機構、実装ファイルを参照）
- execution/
  - execution_engine.py         — ExecutionEngine 本体
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py          — momentum/volatility/value 計算
  - feature_exploration.py      — forward returns / IC / summary
- utils/
  - logging_setup.py            — 統一ログ設定ユーティリティ
  - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

運用上の注意・トラブルシューティング
------------------------------------
- 本番運用時は KABUSYS_ENV=live の設定に十分注意してください（validate_config は live 設定時に警告を出します）。
- AI 機能は API レート制限やコストが発生するため運用設計を行ってください。失敗時はフォールバックロジックがありますが、繰返し失敗する原因はログで確認してください。
- ログディレクトリや data/ 以下のファイルに対するファイル権限に注意してください。logging_setup はログディレクトリ作成に失敗した場合、ファイル出力をスキップして stdout のみで継続します。
- MONITOR_POLL_INTERVAL は小さく設定しすぎると過負荷や無駄な API 呼び出しにつながるため適切に設定してください。

ライセンス / 貢献
-----------------
（このテンプレートではライセンス情報や貢献規約は省略しています。実際のプロジェクトでは LICENSE 文件や CONTRIBUTING.md を追加してください。）

以上が KabuSys の概要・セットアップ・基本的な使い方です。詳細は各モジュールの docstring と実装を参照してください。必要であれば README に README の追加項目（例: 具体的な設定例、CI/CD、デプロイ手順）を追記します。