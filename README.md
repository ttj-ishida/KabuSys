# KabuSys

日本株自動売買システム（ライブラリ / 実行コンポーネント群）

このリポジトリは、シグナル生成、ポートフォリオ構築、発注実行、監視、研究ツール、AI（ニュースセンチメント／レジーム判定）などを含む自動売買基盤の実装群です。モジュールは可能な限り副作用を避けて設計され、実行時は環境変数 / .env による設定で挙動を切り替えます。

主な特徴
- ExecutionEngine：本番 / ペーパートレード両対応（paper_trading では MockBrokerClient を使用し、専用 SQLite に記録）
- Monitoring：システム稼働性・データ鮮度・注文状態・リスク（ドローダウン / ポジション上限）を定期チェック。Kill Switch により安全に Execution を停止可能
- Portfolio Construction：候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整（純粋関数群）
- Research：DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）や特徴量探索（IC 等）
- AI：ニュース記事を LLM（OpenAI）でセンチメント評価し ai_scores に保存、マクロニュースとETF MA を組み合わせた市場レジーム判定
- ユーティリティ：設定ウィザード（.env 生成）、設定検証 CLI、ログ設定、プロセス優先度制御、paper trading レポート作成ツール

セットアップ手順（開発環境想定）
1. Python バージョンを用意
   - 推奨: Python 3.10+（ソース内の型ヒントに合わせてください）

2. 依存関係をインストール
   - pip install -e . もしくは requirements.txt がある場合はそれを利用
   - 必須（主要）パッケージ例:
     - duckdb
     - psutil
     - openai
     - （開発用）PyYAML（config 検証の追加チェックに使用）
   - 例:
     - pip install duckdb psutil openai

3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に（リポジトリにない場合は README に記載のキーを参照）
   - .env は決して Git にコミットしないこと

4. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit(1)）扱いになります:
     - python -m kabusys.validate_config --strict

5. 必要ディレクトリの準備
   - data/（データベース・フラグファイル）
   - logs/（ログ出力）
   - 例: mkdir -p data logs

主要環境変数（抜粋とデフォルト）
- KABUSYS_ENV: 実行環境
  - 値: development | paper_trading | live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant | partial | never | reject）（デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- OPENAI_API_KEY: AI モジュール利用時の OpenAI API キー
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（development 用。0 または 1）

起動 / 使い方（代表的なコマンド）
- ExecutionEngine を起動（本番 or .env の KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、data/paper_trading.db を使用（本番 DB と分離）
    - data/execution.pid に PID を書く。data/stop_requested.flag があると起動をスキップまたは停止する
    - 起動直後にプロセス優先度を "high" に設定

- Monitoring を起動（ポーリングで監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用（環境に関わらず）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

ログ
- 共通のログ設定ユーティリティを使用（kabusys.utils.logging_setup.setup_logging）
- 出力先:
  - コンソール（stdout）
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
- LOG_DIR 環境変数でログディレクトリを上書き可能

監視 / Kill Switch / 停止方法
- Kill Switch:
  - kabusys.monitoring.kill_switch が条件を満たすと data/kill.flag を書き、ExecutionEngine に停止シグナルを与える設計
  - Execution 起動時は kill.flag を自動クリアしない（KILL_FLAG_CLEAR_ON_START=1 の場合のみクリア）
- 停止フラグ:
  - data/stop_requested.flag を置くと run_execution や run_monitoring のループが終了します（運用時に手動停止したいときに使用）
- PID ファイル:
  - data/execution.pid に ExecutionEngine の PID を書きます

AI モジュールについて（ニュース / レジーム）
- OpenAI API（gpt-4o-mini を想定）を利用してニュースを評価します
- 必要: OPENAI_API_KEY を環境変数か関数引数で指定
- news_nlp.score_news: raw_news / news_symbols を集約して複数銘柄をバッチ評価 → ai_scores に書き込み
- regime_detector.score_regime: ETF (1321) の MA200 とマクロニュースの LLM スコアを合成して market_regime に書き込む
- API エラーはリトライやフォールバックでフェイルセーフ設計（未取得時はデフォルト値で継続）

開発者向けメモ
- 設計方針の一部:
  - 多くのモジュールは副作用を持たない純粋関数（portfolio/*、research/*）として実装
  - DB 書き込みは監視層（monitoring_db.MonitoringDB）や Execution のリポジトリに限定
  - ルックアヘッドバイアス防止のため、日付参照は明示的に引数で渡す（date.today() を使わない設計を目指す）
- テストしやすくするため、OpenAI など外部呼び出しを行う関数は差し替え可能にしている（ユニットテストでのモック容易化）

主要機能一覧（概観）
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（pid 管理、stop flag チェック、paper_trading 分離）
- 監視系
  - run_monitoring.py: SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL で制御）
  - monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py（アラート管理）
  - monitoring_db.py: SQLite スキーマ作成 / CRUD ユーティリティ
- 設定
  - config.py: Settings クラス（環境変数・.env 自動読込、キー取得ユーティリティ）
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 起動前チェック CLI
- ポートフォリオ
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- 研究 / ファクター計算
  - research/factor_research.py, feature_exploration.py
- AI
  - ai/news_nlp.py, ai/regime_detector.py
- ユーティリティ
  - utils/logging_setup.py, utils/process_priority.py
- ツール
  - tools/paper_verification_report.py

ディレクトリ構成（主要ファイルのみ抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (実装ファイルがある想定)
    - execution/ (発注関連コンポーネント群: Engine, Broker, OrderManager 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - data/ （実行時に生成される想定）
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - logs/ （ログファイル出力先）

よくある運用フロー例
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の初期データを用意（データ取り込みパイプライン等）
4. 監視を起動（監視が system_status や trade_logs を維持）
   - python -m kabusys.run_monitoring
5. 実行エンジンを起動（本番または paper_trading）
   - python -m kabusys.run_execution
6. 運用中は logs/ と data/ を監視し、必要に応じて kill.flag を手動で作成して停止

免責・注意
- .env に機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください
- KABUSYS_ENV=live は本番動作です。十分に検証してから使用してください
- OpenAI など外部 API の利用には別途コスト・利用規約が発生します

問い合わせ・貢献
- バグや改善提案は issue を立ててください。簡単な実装補助やユニットテストの追加も歓迎します。

以上がこのコードベースの README 相当のまとめです。必要であれば .env の雛形や運用チェックリスト、詳細なコマンド例（systemd / supervisor / docker-compose での実行例）なども作成します。どの情報がさらに必要か教えてください。