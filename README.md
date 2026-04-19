# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリ群（モジュール群）。  
このリポジトリは自動売買エンジン、監視・キルスイッチ、ポートフォリオ構築ユーティリティ、リサーチ/ファクター計算、OpenAI を使ったニュース NLP などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要要件（依存関係）
- セットアップ手順
- 使い方（起動 / CLI）
- 主要環境変数
- ディレクトリ構成（概略）
- よくある注意点 / トラブルシューティング

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムを構成する Python モジュール群です。
- 構成要素として、実行エンジン（ExecutionEngine）、監視サブシステム（Monitoring）、リスク管理、注文管理、ポートフォリオ構築ユーティリティ、リサーチ/ファクター計算、AI（ニュースのセンチメント等）モジュールを含みます。
- Paper trading（検証用のモックブローカーと専用 DB）と Live（実際の発注）の切り替えを想定した設計です。
- ロギング・プロセス優先度制御・監視ログ永続化（SQLite）・分析用 DuckDB などを組み合わせて運用を支援します。

主な機能（抜粋）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、本番 DB と分離した data/paper_trading.db へ記録。
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視（stop_requested.flag / kill.flag）対応。
- Monitoring（run_monitoring.py / monitoring モジュール群）
  - SystemMonitor：CPU/メモリ/DISK、データ鮮度、プロセス生存などの監視。
  - TradeMonitor / RiskMonitor：滞留注文・約定異常・ドローダウン・ポジション上限などの監視。
  - KillSwitch：条件に基づいて data/kill.flag を書き込み、ExecutionEngine 停止を促す仕組み。
  - MonitoringEngine：各 Monitor をまとめて定期実行（ポーリング間隔は環境変数で調整可能）。
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化。必要なテーブルは起動時に自動作成／マイグレーションされます。
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分／スコア加重配分、位置サイズ計算（単元株丸め・リスク制限）、セクターキャップ適用、レジーム乗数。
- リサーチ（kabusys.research）
  - ファクター（Momentum / Value / Volatility / Liquidity）計算、将来リターン、IC 計算、統計サマリー。
  - DuckDB を使った SQL ベースの高速処理を想定。
- AI（kabusys.ai）
  - news_nlp: raw_news を OpenAI API に送り銘柄ごとのセンチメントスコアを計算し ai_scores テーブルへ保存。
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定を行い market_regime テーブルへ保存。
  - API 呼び出しはリトライやフォールバック（失敗時は安全側のデフォルト値）を行う実装。
- 開発用ユーティリティ
  - .env インタラクティブセットアップ（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

必要要件（想定）
- Python 3.10 以上（| 型ヒント等を使用）
- 推奨パッケージ（requirements.txt がある場合はそちらを使用してください）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワークアクセス（OpenAI / 外部 API を使う場合）

セットアップ手順（概略）
1. リポジトリを取得
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも次を入れる:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を作成してルートに配置。
   - .env の主な必須値:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV（development/paper_trading/live）
     - OPENAI_API_KEY（AI モジュールを使う場合）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります。

6. 初期ディレクトリ作成
   - data/ , logs/ などは多くの場合自動作成されますが、必要に応じて手動で作成して権限を確認してください。

使い方（起動 / CLI）
- 実行エンジン（ExecutionEngine）起動
  - 簡易:
    - python -m kabusys.run_execution
  - Paper trading モードにするには KABUSYS_ENV=paper_trading を .env または環境変数で設定
  - ExecutionEngine は data/execution.pid に PID を書き、 data/stop_requested.flag / data/kill.flag の存在を監視して停止します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring  （単位: 秒、1 以上）
  - 監視は常に「本番用の sqlite_path」を使用して監視ログを記録します（環境に依らず同一の監視 DB を使う設計）。

- .env を対話式で編集 / 生成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict（警告があると exit(1)）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能（デフォルト: data/paper_trading.db）。

主要な環境変数（抜粋）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込む flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動で削除する (0/1、デフォルト 0)

ディレクトリ構成（主要ファイルのみ、src/kabusys 配下）
- src/kabusys/
  - __init__.py
  - config.py               —— .env 読み込み・Settings クラス
  - config_setup.py         —— .env 対話式ウィザード
  - validate_config.py      —— 起動前設定検証 CLI
  - run_execution.py        —— ExecutionEngine 起動スクリプト
  - run_monitoring.py       —— Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py      —— 共通ログ設定
    - process_priority.py   —— プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      —— SQLite テーブル作成・永続化 API
    - system_monitor.py     —— CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py      —— （注文監視: 滞留/約定異常等）※実装あり
    - risk_monitor.py       —— ドローダウン / ポジション上限監視
    - kill_switch.py        —— kill.flag 書き込み / クリア
    - monitoring_engine.py  —— 各 Monitor を束ねる
    - alert_manager.py      —— （通知管理: LINE 等への送信を想定）
  - execution/
    - execution_engine.py   —— 実行エンジン本体（起動・注文処理）
    - broker_factory.py     —— ブローカークライアント生成（モック/実ブローカー）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           —— OpenAI を使ったニュースセンチメント
    - regime_detector.py    —— マクロ + MA200 でレジーム判定
  - tools/
    - paper_verification_report.py

補足・運用上の注意
- Paper trading と Live はデータベースを分離することを強く推奨します（run_execution は環境に応じて paper_sqlite_path を使用します）。
- OpenAI を利用する機能は API キーが必要です。API 利用はコストが発生します。呼び出し失敗時は安全側のフォールバック（0.0 等）が働きますが、結果が欠落することがあります。
- 監視用 SQLite（data/monitoring.db）は起動時にテーブルの作成・軽微なマイグレーションを行います。既存の DB に対して後方互換性のための列追加処理が含まれます。
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。ログディレクトリに書き込み権限があるか確認してください。
- stop_requested.flag / kill.flag:
  - run_monitoring と run_execution はプロセス停止のためのフラグファイル（stop_requested.flag / data/stop_requested.flag）を監視します。ファイルを作成するとポーリングループが停止へ移行します（安全にシャットダウンしたい場合に利用）。
  - KillSwitch は条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込み、管理者が kill.flag を確認して Execution を停止（または手動クリア）できます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動的にクリアする挙動が有効になる可能性があります（本番では 0 を推奨）。

トラブルシューティング（簡易）
- 起動時に DB/ログディレクトリ作成エラー:
  - 権限を確認し、必要に応じてディレクトリを作成してください（例: mkdir -p data logs && chown ...）。
- OpenAI 呼び出しでエラーが出る:
  - OPENAI_API_KEY が設定されているか確認。ネットワーク接続と API レート制限に注意。
- .env の読み込みがおかしい:
  - config.py はプロジェクトルート（.git / pyproject.toml）を探索して .env/.env.local を自動読み込みします。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視データが見つからない / 指標が N/A になる:
  - DuckDB 側の prices_daily / raw_news 等のデータが不足している可能性があります。データ取り込みパイプラインやテーブル内容を確認してください。

---

その他
- この README はコードベース（src/kabusys/*）の現状実装に基づいて作成されています。細かな CLI 引数や追加設定はソースコード内の docstring / 関数コメントを参照してください。
- 貢献 / バグ報告: プロジェクトの issue tracker にお願いします。

以上。必要であれば README を README.md ファイルとして出力する形で整形し（ライセンス記載など）、より詳細な運用手順（例: systemd / supervisor 用のユニットファイル、docker-compose など）を追加できます。どの情報を拡張しますか？