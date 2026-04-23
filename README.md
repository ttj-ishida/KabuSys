KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買（および研究/監視）用ライブラリ兼実行スクリプト群です。  
主要な機能は戦略研究、ポートフォリオ構築、発注エンジン（実運用・ペーパートレード両対応）、監視・アラート、AI を使ったニュースセンチメント評価などを含みます。

要点
- 設計は「本番 DB とペーパートレード DB を明確に分離」「ルックアヘッドバイアスを防ぐ」「フェイルセーフ（API失敗時は安全側で継続）」を重視しています
- ログは共通の logging_setup を使って stdout と日次ローテートファイルに出力します
- .env を使った設定（config_setup による対話的生成、validate_config による検証）を想定しています

主な機能一覧
- 実行（ExecutionEngine）: run_execution.py から起動。paper_trading モードでは MockBroker を使用して data/paper_trading.db に記録
- 監視（Monitoring）: run_monitoring.py から起動。システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）などを定期チェック
- Kill Switch: 監視で閾値超過を検知すると data/kill.flag を書き、発注エンジンを停止させる仕組み
- ポートフォリオ構築: 候補選定、等配分・スコア配分、リスク調整（セクターキャップ、レジーム乗数）、株数決定（単元丸め・aggregate cap）
- 研究モジュール: ファクター計算（momentum／value／volatility 等）、将来リターン、IC 計算、統計サマリ等（DuckDB を利用）
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込む機能、マクロニュースと ETF MA 乖離から市場レジーム判定
- ツール: Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順（開発環境）
- 前提: Python 3.10+ を想定（typing 構文などから）
1. リポジトリをクローンしてワークディレクトリへ
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 必須ライブラリ（コードからの推定）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML は validate_config の YAML 検証で使われる
   - 例:
     - pip install duckdb psutil openai pyyaml
   - 注: requirements.txt は付属していないため、適宜プロジェクトに合わせて固定してください
4. .env の用意
   - 対話式ウィザードで生成: python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成

主要な環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / オプション（デフォルト）
  - KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- .env の初期作成推奨手順:
  - python -m kabusys.config_setup
  - 生成後、設定を検証: python -m kabusys.validate_config
    - --strict をつけると警告も失敗扱いで exit(1)

使い方（主要コマンド）
- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag の存在をチェックし、既にあれば起動をスキップ
    - エンジンは別スレッドで run_session を実行し、stop フラグで停止可能
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings に従い SQLite（監視DB）・DuckDB に接続
    - set_process_priority("high") を試み、SystemMonitor を定期実行
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を設定可能（デフォルト 60）
    - 停止は data/stop_requested.flag を作成して制御
- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告を FAIL として扱う）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- 研究 / ユーティリティ関数
  - duckdb 接続を作り、kabusys.research.calc_momentum 等の関数を呼ぶ
  - AI 機能は OPENAI_API_KEY を設定して kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用

重要な運用ノート
- 監視（monitoring）は Settings.env の値にかかわらず監視用 SQLite（設定された sqlite_path）を使用します
- ペーパートレードモードでは発注処理が本番口座に到達しないよう DB を分離しています
- Kill Switch（data/kill.flag）:
  - RiskMonitor 等が閾値を越えると KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では推奨されません（安全上の理由）
- ログ:
  - デフォルトのログディレクトリは logs/
  - setup_logging(app_name="execution") を呼ぶことで logs/execution.log に日次ローテーションで出力
- OpenAI 関連:
  - OPENAI_API_KEY が未設定だと AI 機能は動作しません。score_news と score_regime は引数でキーを渡すことも可能
  - API 呼び出しはリトライ・バックオフ等の安全処理がありますが、レート制限や鍵の設定ミスに注意してください

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor 起動スクリプト
  - config.py                       — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前設定検証 CLI
  - utils/
    - logging_setup.py              — 共通ログ設定
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                       — 発注関連（Engine, OrderManager 等）※詳細実装は本 README 省略
  - monitoring/
    - monitoring_db.py              — 監視用 SQLite の初期化と永続化 API
    - system_monitor.py             — CPU/memory/disk/データ鮮度/プロセス監視
    - trade_monitor.py              — 注文滞留・約定異常等の監視（※ファイル内実装あり）
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — Kill Switch 実装
    - monitoring_engine.py          — 各 Monitor を束ねるループ
    - alert_manager.py              — （通知管理・LINE 等）※実装に依存
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数決定・aggregate cap
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py            — momentum/value/volatility 等のファクター計算（DuckDB）
    - feature_exploration.py        — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）で銘柄ごとのスコアを生成
    - regime_detector.py            — ETF MA 乖離 + マクロセンチメントでレジーム判定
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成ツール

よくある操作・例
- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視を起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジンを起動（ペーパー/本番は KABUSYS_ENV で制御）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

開発・拡張のヒント
- DuckDB を使って大量データを高速に集計する設計になっています。prices_daily / raw_financials 等のテーブル定義に合わせてデータを用意してください
- AI（OpenAI）機能は API のレスポンス形式に依存するため、mock 化（ユニットテスト）やリトライ挙動の確認を推奨します
- monitor 側は監視 DB（SQLite）に依存するため、運用では適切なバックアップやファイルローテーションを検討してください

ライセンス・バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）

問題・質問
- 実行時に必要な追加情報・依存があれば、README に requirements.txt を追加する or Docker コンテナ化を検討してください
- 具体的なモジュール（ExecutionEngine の外部 API 実装や OrderRepository）の詳細な使い方は該当モジュールの docstring を参照してください

以上を参考にして環境を整え、まずは .env を作成 → validate_config で確認 → run_monitoring / run_execution を順に起動してみてください。必要なら README を実運用向けにさらに拡張（systemd ユニット例、Dockerfile、requirements.txt、運用手順書）できます。