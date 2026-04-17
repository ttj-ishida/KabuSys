# KabuSys

日本株向け自動売買システムのコアライブラリ群（ドキュメント用簡易 README）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・分析ツール・LLM を用いたニュース評価などの機能を含みます。

主なポイント
- Python パッケージ名: kabusys
- 実行モード: development / paper_trading / live（環境変数 KABUSYS_ENV）
- DB: DuckDB（分析用）と SQLite（監視 / ペーパートレード用）
- フラグファイルで外部からエンジン停止を制御（data/kill.flag, data/stop_requested.flag）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動 / CLI）
- ディレクトリ構成（主要ファイル説明）
- 追加注意事項（環境変数・依存関係）

---

プロジェクト概要
- KabuSys は日本株自動売買のためのライブラリ群です。ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視・アラート、ペーパートレード検証、LLM を用いたニュースセンチメント評価などを含みます。
- 実行時の設定は主に環境変数（.env）で管理します。対話式ウィザードや設定検証ツールが用意されています。

---

機能一覧
- 設定管理
  - .env 自動読み込み / Settings クラス（kabusys.config）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 発注・実行
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モード時は MockBrokerClient を利用し、data/paper_trading.db に記録（本番 DB と分離）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめる MonitoringEngine（run_monitoring.py 起動）
  - 監視ログ保存（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
  - Kill Switch: drawdown やポジション数などで kill.flag を書き込みエンジン停止
  - AlertManager: LINE push による通知（トークン未設定だとログのみ）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、ポジションサイジング、セクター制限、レジーム乗数 等
- リサーチ / ファクター計算
  - モメンタム・ボラティリティ・バリュー等のファクター（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）連携
  - ニュース記事を OpenAI (gpt-4o-mini) でセンチメント評価し ai_scores に書き込み（kabusys.ai.news_nlp）
  - マクロ + ETF MA 乖離を組み合わせた市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

セットアップ手順（簡易）
1. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - 以下は本プロジェクトで参照される主要パッケージ例：
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（config 検証時に YAML ファイルのパースを行う場合に必要）
   - 例:
     - pip install duckdb psutil openai requests pyyaml

   （本リポジトリに requirements.txt がある場合はそれを使ってください。なければ上記を目安にインストールしてください。）

3. .env 作成
   - 対話式ウィザードを実行して .env を作成できます:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - オプション/重要:
     - KABUSYS_ENV (development / paper_trading / live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知を有効化する場合）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

---

使い方（起動 / CLI）
- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV により paper_trading の場合はペーパートレード DB を使います。
    - 実行時に data/execution.pid を作成しプロセス存在を管理。
    - 実行前に data/stop_requested.flag が存在する場合は起動をスキップします。
    - 停止は data/stop_requested.flag または kill.flag によって行います（kill.flag は KillSwitch による停止トリガー）。

- Monitoring（監視）ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60秒）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依らず）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 機能（関数呼び出し）
  - kabusys.ai.score_news（ニューススコアリング）
    - 必要: OPENAI_API_KEY（引数で渡すことも可能）
    - DB: DuckDB 接続（raw_news, news_symbols, ai_scores テーブル）
  - kabusys.ai.regime_detector.score_regime（市場レジーム判定）
    - 必要: OPENAI_API_KEY（引数で渡すことも可能）
    - DB: DuckDB 接続（prices_daily, raw_news, market_regime）

---

重要なファイル / フラグ
- data/execution.pid — 発注エンジンの PID を保存
- data/kill.flag — Kill Switch が書き込む停止フラグ（存在すれば ExecutionEngine を停止する設計）
- data/stop_requested.flag — run_* スクリプトの外部停止トリガー（run_* はこのファイルが出現するとループを終了）
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - monitoring SQLite: data/monitoring.db
  - paper trading SQLite: data/paper_trading.db

---

ディレクトリ構成（主要モジュールと略説）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings クラス、自動 .env ロードロジック
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度設定、CPU affinity ユーティリティ（psutil）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブルの初期化および永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込ロジック
    - monitoring_engine.py — Monitor をまとめてポーリングする Engine
    - alert_manager.py — LINE Push による通知送信（クールダウン管理）
  - execution/ (発注関連: Engine, BrokerFactory, OrderRepository 等) — 発注ロジック（ソースの一部は省略）
  - portfolio/
    - portfolio_builder.py — 候補選定、重みづけ
    - position_sizing.py — 株数計算、ロット丸め、aggregate cap
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメント評価
    - regime_detector.py — マクロ + MA によるレジーム判定（OpenAI を利用）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（上記は主要ファイルの抜粋です。実コードでは execution 以下に多くの発注関連モジュールが存在します。）

---

追加注意事項 / 運用ヒント
- KABUSYS_ENV:
  - development: 開発用（発注抑止など）
  - paper_trading: ペーパートレード（MockBroker を使用し paper DB に記録）
  - live: 本番（実際の発注）
- process priority / CPU affinity の設定は psutil を利用。権限不足時は警告を出してスキップします。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）を必ず設定してください。API 呼び出しはリトライ・フォールバック等の耐障害措置が組み込まれていますが、コストに注意してください。
- 監視の閾値（CPU/MEM/DISK、ドローダウン閾値 等）は環境変数や config ファイルで調整できます（Settings クラス / config/*.yaml を参照）。
- データベースのスキーマは monitoring_db.init_monitoring_db() で冪等に作成・簡単なマイグレーションを行います。

---

トラブルシュート（よくある質問）
- .env が読み込まれない:
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行われます。配布パッケージ化した環境では自動ロードがスキップされる場合があります。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。
- Monitoring が想定どおり動作しない:
  - MONITOR_POLL_INTERVAL を調整しているか、data/stop_requested.flag が存在していないか確認してください。
- LINE 通知が届かない:
  - LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を .env に設定してください。未設定時はログのみ出力されます。

---

開発・拡張
- 各モジュールはユニットテスト可能な純粋関数（特に portfolio, research）を多く含みます。DuckDB 接続を受け取る設計のため、テスト用のインメモリ DB を用意して検証できます。
- AI 周りの API 呼び出し関数はテスト時に差し替え（mock）できるように設計されています。

---

以上。実運用時は .env の管理（絶対に Git にコミットしない）、データベースのバックアップ、API キーの厳重管理、監視アラートの定期テストを行ってください。質問や追加の README 内容（例: systemd ユニットファイル、Docker 化手順など）が必要なら教えてください。