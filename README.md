# KabuSys — 日本株自動売買システム（README 日本語）

概要
---
KabuSys は日本株向けの自動売買・研究基盤ライブラリです。  
このリポジトリには、取引実行エンジン起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、ファクター計算・研究ユーティリティ、AI（ニュース NLP / レジーム判定）連携などが含まれます。設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しは明示的に制御」などを採用しています。

主な特徴
---
- 実行環境の分離
  - KABUSYS_ENV により `development` / `paper_trading` / `live` を切替可能。paper_trading 時は MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用。
- 実行エンジン起動スクリプト（run_execution）と監視ループ（run_monitoring）の提供
- 監視基盤
  - システム状態（CPU/メモリ/ディスク）、プロセス生存、データ鮮度、注文ログ、ダッシュボード、リスクログを SQLite に永続化
  - Kill Switch（条件により data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート発行インフラ（AlertManager 経由）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム乗数）
- 研究用モジュール（DuckDB 経由でファクター計算、IC 計算、特徴量探索）
- AI 統合
  - OpenAI を利用したニュースセンチメント（news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しは失敗耐性（リトライ/フォールバック）あり
- ツール
  - paper_trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定管理
  - .env ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
- 統一ロギング・プロセス優先度設定ユーティリティ

セットアップ手順
---
1. Python 仮想環境を作成・有効化
   - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストール
   - 必要な主なパッケージ（プロジェクトで使われているもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証を行う場合に推奨）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを使用してください）

3. .env の作成（ウィザード推奨）
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - ウィザード後は:
     - python -m kabusys.validate_config で設定検証を実行

重要な環境変数（抜粋）
---
以下は設定でよく使う主要項目（.env に記載）です。config_setup の項目定義がそのまま参考になります。

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1。本番では 0 推奨）
- KILL_FLAG_PATH / PID_FILE_PATH: kill.flag や pid ファイルのパス（Settingsで扱われる）

使い方（主要コマンド）
---
- .env 作成（対話式ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録します
  - 実行中の停止は data/stop_requested.flag（実行スクリプトで監視）や data/kill.flag（KillSwitch）等で制御

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は Settings の sqlite_path（monitoring DB）と duckdb_path を使用

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を指定する（引数で渡すか環境変数で）

ログ・監視・停止制御
---
- ロギングは kabusys.utils.logging_setup.setup_logging で統一設定され、console（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力します。
- プロセス優先度は起動時に set_process_priority("high") を呼んでいる箇所が多くあります（実行権限によっては反映されない場合あり）。
- Kill Switch:
  - risk_monitor / monitoring_engine の判定により data/kill.flag が書き込まれると ExecutionEngine は安全停止する設計です。
  - KILL_FLAG_CLEAR_ON_START を `1` にすると起動時に kill.flag を自動クリアしますが、本番では危険なため `0` を推奨します。
- 停止フラグ:
  - data/stop_requested.flag を置くことで run_monitoring/run_execution のループを終了させる挙動が実装されています。

ディレクトリ構成（抜粋）
---
以下は主要ファイルを含むディレクトリ構成の概要です（src/kabusys 配下）：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status/trade_logs/positions/...）
    - monitoring_engine.py   — 複数モニタを束ねるエンジン
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （注文監視ロジック）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — （アラート送信の抽象）
  - execution/
    - execution_engine.py    — ExecutionEngine（実行ロジック。依存注入でリスク管理等と連携）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み付け
    - position_sizing.py     — 株数決定 / 単元丸め / 集約キャップ
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py            — ニュースセンチメント取得（OpenAI）
    - regime_detector.py     — マクロ + ETF MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

補足・運用メモ
---
- DB
  - DuckDB: 分析・研究用。パスは DUCKDB_PATH で指定（デフォルト data/kabusys.duckdb）。
  - SQLite: 監視ログ等は SQLITE_PATH（data/monitoring.db）へ保存。
  - paper_trading 用の SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）。
- AI
  - OpenAI を使用する機能は API キーの設定が必須。キーは環境変数 OPENAI_API_KEY か関数引数で提供してください。
  - API エラー時はリトライおよびフォールバック（スコア 0.0 やスキップ）が組み込まれています。
- テスト・開発
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト等で有用）。
  - validate_config.py は YAML のパース検証を行うため PyYAML があるとより厳密な検証が可能です。

例（.env の抜粋）
---
例:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

ライセンス・貢献
---
（リポジトリに LICENSE ファイルがあればその指示に従ってください。）  
バグ報告や機能追加は issue / PR を通してお願いします。

最後に
---
この README はリポジトリ内の主要モジュールと運用フローを要約したものです。各モジュールの詳細な挙動や API 仕様はソース（特に docstring）を参照してください。必要であれば、起動スクリプトや各ユーティリティのより詳しい利用ガイドを追記できます。