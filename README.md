# KabuSys

日本株自動売買システム（KabuSys） — 戦略生成・ポートフォリオ構築・実行エンジン・監視・検証ツールを含む軽量フレームワーク  
バージョン: 0.1.0

概要
- KabuSys は日本株の自動売買ワークフローをサポートする Python ライブラリ兼実行フレームワークです。
- 主な機能はシグナルの評価 → ポートフォリオ構築 → 発注（実取引 or ペーパートレード）→ 監視・リスク管理 → レポート／研究機能、さらに OpenAI を用いたニュース NLP / レジーム判定を含みます。
- データ永続化には DuckDB（分析用）と SQLite（監視・注文ログ用）を使用します。Paper trading は本番 DB と分離されます。

主な機能一覧
- Execution
  - ExecutionEngine を使った発注実行ループ（本番/ペーパートレード両対応）
  - BrokerClientFactory によるブローカークライアント切替（KABUSYS_ENV に応じて MockBrokerClient を使用）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等による堅牢な発注管理
- Monitoring
  - SystemMonitor（プロセス稼働・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（注文滞留・約定異常検出 等）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（閾値到達時に data/kill.flag を書き込み ExecutionEngine を停止）
  - MonitoringEngine：複数モニタの束ねとアラート発行
- Portfolio
  - 候補選定、等金額/スコア加重配分、リスク調整（セクター上限・レジーム乗数）
  - 単元株丸め、リスクベースの数量決定（position sizing）
- Research
  - DuckDB を用いたファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - news_nlp: OpenAI を用いたニュースセンチメント評価（ai_scores テーブルへの書込）
  - regime_detector: MA200 とマクロニュースの LLM 結果を合成して日次レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前チェック（必須環境変数・config/*.yaml の存在等）
  - paper_verification_report: ペーパートレードの検証レポート生成
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

必要要件
- Python 3.10+
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML 検証を行う場合、任意）
- （推奨）仮想環境: venv / pyenv / poetry 等

セットアップ手順（開発用・ローカル）
1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd repo
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - config 検証用に PyYAML を使う場合: pip install pyyaml
4. 環境変数設定（.env）
   - 対話式ウィザードで .env を生成する:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（リポジトリルートに置く）。最低限必要なキー:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 便利なキー（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合必須
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict
6. ログディレクトリ自動作成（デフォルト logs/）と DB ファイル用ディレクトリ（data/）が必要
   - これらは起動時に自動生成されることもありますが、アクセス権の確認を推奨

基本的な使い方（よく使うコマンド）
- 環境変数を設定（例: bash）
  - export KABUSYS_ENV=paper_trading
  - export OPENAI_API_KEY="sk-..."
  - export MONITOR_POLL_INTERVAL=60  # 監視ループのポーリング間隔（秒）
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動（発注ループ）
  - python -m kabusys.run_execution
  - 注意: data/stop_requested.flag が存在すると起動を行わない / 実行中に作成されると停止する
  - ペーパートレード切替: KABUSYS_ENV=paper_trading（この場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録）
- Monitoring を起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）
  - 監視は常に本番用 sqlite_path を参照（環境にかかわらず monitoring DB は production path を使う設計）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定や DB パス指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
- AI 機能（プログラム内 API）
  - ニューススコア付け: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照

重要ファイル / フラグ（運用注意点）
- data/kill.flag
  - KillSwitch が書き込むファイル。存在すると ExecutionEngine に停止シグナルを送る（起動時の自動クリア設定に注意）。
- data/stop_requested.flag
  - run_execution / run_monitoring のループを優雅に停止させるためのフラグ。存在するとループを終了する。
- data/execution.pid（デフォルト）
  - ExecutionEngine の PID ファイル（存在/パスは Settings.pid_file_path により変更可）。
- ログ
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）日次ローテート、30日分保持

サンプル .env（最低限の例）
- .env.example の参考を推奨。簡易例:
  JQUANTS_REFRESH_TOKEN=your_token_here
  KABU_API_PASSWORD=your_kabu_password
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  OPENAI_API_KEY=sk-...

ディレクトリ構成（主なモジュールと説明）
- src/kabusys/
  - __init__.py  — パッケージ定義（__version__ 等）
  - config.py  — 環境変数/.env の自動ロードおよび Settings クラス
  - config_setup.py  — .env 対話式作成ウィザード
  - validate_config.py  — 起動前設定検証 CLI
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースのセンチメント評価 / ai_scores への書込
    - regime_detector.py — 市場レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite の永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — （注文滞留・約定異常を検出するモジュール：コードベースに実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限のチェック
    - kill_switch.py — kill.flag の読み書き
    - monitoring_engine.py — 複数 Monitor の束ね
    - alert_manager.py —（アラート送信ロジック：実装により外部通知を行う）
  - execution/
    - execution_engine.py — 発注ループ / セッション管理
    - broker_factory.py — Broker クライアント生成（本番 / モック切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注関連コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計要約
  - data/
    - pipeline.py / stats.py  — データ取り込み・統計ユーティリティ（prices_daily 等の扱い）
  - utils/
    - logging_setup.py — ルートロガー設定（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ

運用上の注意
- KABUSYS_ENV の取り扱い:
  - development: 発注なし（検証・ローカル開発向け）
  - paper_trading: MockBroker を使って data/paper_trading.db に記録（本番 DB と分離）
  - live: 実取引を行う。本番環境では LINE 通知などの設定を必ず確認すること
- OpenAI API を利用する機能は API キーが必要。呼び出し頻度に注意（レート制限）。エラー時はフェイルセーフにより継続することが多い設計です。
- kill.flag や stop_requested.flag の扱いは慎重に。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険（自動クリアされてしまう）。
- データのルックアヘッドバイアス防止設計が多くの分析コードに組み込まれているため、target_date の扱いに注意。

開発・拡張
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news, etc.）に従ってデータをロードすることで、research/ai モジュールをローカルで再現可能です。
- AI モジュールの通信部（_call_openai_api）をテスト用にモックすることでテストが容易です。
- monitoring_db.init_monitoring_db は冪等にテーブルを作成し、簡易的なマイグレーション（カラム追加）ロジックを持っています。

ライセンス・貢献
- （ここにライセンス情報や貢献ガイドラインを記載してください）

お問い合わせ・補足
- 実運用前に必ず validate_config を実行し、.env の値や DB パス、LINE 通知等の設定を確認してください。
- 不明点があれば使用するモジュール名や実行しようとしているコマンドを添えて質問してください。

以上。README に含めてほしい追加情報（例：実際の config/*.yaml の内容、運用手順書、CI/CD 指示等）があれば教えてください。