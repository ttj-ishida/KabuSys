# KabuSys — 日本株自動売買システム

このリポジトリは、日本株向けの自動売買システム（実運用 / ペーパートレード / 解析ツール群）を提供します。  
README は本コードベース（src/kabusys/*）の主要コンポーネントと使い方をまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド例）
- 環境変数（主要）
- 停止・Kill Switch の運用
- ディレクトリ構成

---

プロジェクト概要
- 本プロジェクトは、注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュース NLP、各種ツール（ペーパートレード検証レポート等）を含む自動売買フレームワークです。
- DB は主に SQLite（監視・注文ログ等）と DuckDB（分析用時系列データ）を併用します。
- 環境に応じて実運用（live）、ペーパートレード（paper_trading）、開発（development）を切り替え可能です。

主な機能一覧
- Execution
  - ExecutionEngine を使った注文実行（kabuステーションクライアントを利用）
  - paper_trading モードでは MockBrokerClient を使用し、発注データは別 DB に記録（完全分離）
  - リスク管理（RiskManager）、OrderManager、Reconciler などの実行ロジック
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk, 実行プロセス存在チェック, データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件により data/kill.flag を書いて ExecutionEngine を停止
  - MonitoringEngine: 上記をまとめて定期実行（ポーリング）
- Portfolio construction
  - 銘柄選定、等重／スコア重み、ポジションサイズ算出（lot 単位切り捨て、aggregate cap）
  - セクターキャップ、レジーム乗数計算
- Research / Data
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント集約（ai_scores テーブルへ書き込み）
  - regime_detector: ma200 とマクロニュースから市場レジーム（bull/neutral/bear）判定
- Tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定レポートを生成
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 対応の Settings / config_setup（対話式ウィザード）/ validate_config（設定検証 CLI）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / パッケージを入手
2. 仮想環境を作成・有効化（推奨）
   - python >= 3.10 を想定
3. 依存パッケージをインストール
   - 主要依存例: duckdb, psutil, openai, pyyaml（YAML 検証用）など
   - 例: pip install -r requirements.txt
     - （requirements.txt が無い場合は上記を個別にインストール）
4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または .env を直接作成（.env.example を参考に）
5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告を FAIL と扱う）:
     - python -m kabusys.validate_config --strict
6. データディレクトリ（data/）等を作成（必要に応じて）
   - 例: mkdir -p data

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境切替
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DB パス（デフォルト値）
  - DUCKDB_PATH — data/kabusys.duckdb
  - SQLITE_PATH — data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 用、上書き可）
- AI / OpenAI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp/regime_detector が使用）
- その他
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
  - PID_FILE_PATH — execution.pid の保存先（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag の保存先（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）※ run_monitoring の環境変数

使い方（コマンド例）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 起動（注文実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します
- Monitoring 起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視データを記録します（KABUSYS_ENV に依存しない）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 指定期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI スコア / レジーム判定（ライブラリ呼び出し）
  - Python コード中から利用:
    - from kabusys.ai import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは OpenAI API キー（OPENAI_API_KEY）を必要とします

停止・Kill Switch 運用
- 実行中の ExecutionEngine を停止させる方法:
  - Kill Switch を使う: data/kill.flag に理由テキストを書き込むと ExecutionEngine は次のチェックで停止します
  - run_execution / run_monitoring が使っている停止フラグ:
    - data/stop_requested.flag は run_execution/run_monitoring のループを止めるために使用（デプロイ固有）
    - 実運用では stop / restart を行うためのオペレーション手段を定義してください
- run_execution は起動時に kill flag を検出した場合は起動を中止します
- run_monitoring は stop_requested.flag を検知すると監視ループを終了します

注意点 / 運用上の留意事項
- .env は絶対にバージョン管理にコミットしないこと（config_setup のヘッダにも明示）
- KABUSYS_ENV=live の場合は特に LINE 通知や kill flag の設定を慎重に確認してください（validate_config にチェックあり）
- paper_trading は本番 DB と分離されます。PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI 利用時は API のレート制限・課金に注意してください。news_nlp / regime_detector はリトライ・フォールバックの実装を含みますが、運用設計で十分な配慮を行ってください。
- プロセス優先度設定と CPU affinity は utils.process_priority の set_process_priority / set_cpu_affinity を介して行います。権限や OS により設定が失敗する場合があります（警告でスキップ）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動読み込みロジック
  - config_setup.py          — 対話式 .env 作成ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     — 市場レジーム判定（ma200 + macro NLP）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & MonitoringDB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信の管理、実装ファイルあり）
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - ...（実行ロジック関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py            — DuckDB prices_daily 等へのアクセスユーティリティ
    - stats.py               — 正規化ユーティリティ等
  - utils/
    - process_priority.py
  - その他: 多数の内部ユーティリティと DB/分析関数

最後に
- まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で設定を検証してください。  
- 開発では KABUSYS_ENV=development / paper_trading を用いて、実データや API 呼び出しを分離して検証することを推奨します。

必要であれば、README に含めるサンプル .env のテンプレートや systemd / supervisor 用の起動ユニット例、Docker/Herd のデプロイ手順も作成します。どれが必要か教えてください。