README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究用ツール群です。本リポジトリには以下の主要コンポーネントが含まれます:

- 発注エンジン（ExecutionEngine）起動スクリプト — 本番 / ペーパートレードを切り替えて起動できます
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor） — システム稼働・注文状況・リスク監視と Kill Switch を提供
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）関数群
- 研究用ファクター計算・特徴量解析モジュール（DuckDB を利用）
- AI 連携モジュール（OpenAI を用いたニュースセンチメント / レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証、レポート生成 等）

主な設計方針は「本番口座に影響を与えない分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API障害時は安全側にフォールバック）」です。

機能一覧
--------
- 実行エンジン起動:
  - KABUSYS_ENV に応じて本番 / ペーパートレードを切替
  - paper_trading 時は MockBrokerClient を使用し、専用 DB（data/paper_trading.db）へ記録
  - 起動時にプロセス優先度を高く設定
- 監視:
  - システムリソース（CPU / メモリ / ディスク）監視、プロセス死活確認、データ鮮度チェック
  - 注文ログ監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止）
  - MONITOR_POLL_INTERVAL 環境変数で監視間隔を変更可能（デフォルト 60 秒）
- ポートフォリオ構築:
  - 候補選定（スコア順）、等金額 / スコア加重配分、リスクベースのポジションサイズ計算
  - セクター集中制限、レジーム乗数
- 研究用:
  - Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）連携:
  - ニュースを集約して銘柄別センチメントを算出し ai_scores テーブルへ書き込み
  - マクロニュース + ETF ma200 乖離で市場レジーム判定（market_regime テーブルへ書き込み）
  - API 呼び出しは堅牢なリトライ / バックオフ、失敗時の安全側フォールバックあり
- ツール:
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ手順
--------------
前提:
- Python 3.10 以上（型アノテーションの | 等を使用）
- Git 等でリポジトリをクローン済み

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須パッケージの例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (設定ファイルの YAML 検証を行う場合に任意)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用してください。）

3. 環境変数設定（.env）
   - 対話式ウィザードを実行して .env を作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - (OpenAI を使う場合) OPENAI_API_KEY=sk-...

   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject; デフォルト instant)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリの作成
   - ログディレクトリや data ディレクトリは自動作成されますが、必要に応じ手動で作成:
     - mkdir -p data logs

使い方
------
主要なコマンド例:

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - 本番/開発/ペーパーは KABUSYS_ENV に依存:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 実行時の挙動:
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/execution.pid に PID を書き込む
    - 起動前に data/stop_requested.flag が存在する場合は起動をスキップ

- Monitoring / 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - 監視プロセスも起動時にプロセス優先度を高く設定します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を .env または環境変数に設定しておく
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出す

停止 / Kill / フラグについて:
- プロセスを優雅に停止するにはプロジェクトルート下の data/stop_requested.flag を作成します（多くの起動スクリプトがこれを検知してループを終了します）。
- Kill Switch は条件を満たすと data/kill.flag を作成し ExecutionEngine を停止させます。起動時の KILL_FLAG_CLEAR_ON_START=1 により自動クリアできますが、本番では 0 を推奨します。

ログ:
- ログは標準出力および logs/<app_name>.log（日次ローテーション、デフォルト 30 日保持）へ出力されます。
- ログレベルは環境変数 LOG_LEVEL または .env の設定で制御します。

トラブルシューティングのヒント
- 必須環境変数が不足している場合は validate_config でエラーが出ます。
- OpenAI 関連は API キーが未設定だと例外を投げます（AI 機能を呼ぶ関数で）。
- DuckDB / SQLite の親ディレクトリがない場合は自動作成されますが、権限エラーなどがあるとファイル作成に失敗することがあります。
- プロセス優先度 / CPU affinity の設定は OS や権限により失敗することがあり、その場合は警告ログが出力されます（例外は発生しない）。

主要ファイル・ディレクトリ構成
----------------------------
（src/kabusys 以下の概要）

- __init__.py
- config.py
  - Settings クラス: 環境変数や .env 自動ロードのロジック
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV により挙動切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- monitoring/
  - monitoring_db.py — SQLite ベースの永続層（テーブル作成・読み書き）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文ログ監視（コード参照）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — data/kill.flag 管理
  - monitoring_engine.py — 複数モニタを束ねるエンジン
  - alert_manager.py — アラート送信（LINE等）実装（コード参照）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・丸め
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — 市場レジーム判定（OpenAI + ma200）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity

デフォルトパス（環境変数で変更可）
- DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
- SQLite（監視DB）: data/monitoring.db (環境変数 SQLITE_PATH)
- Paper Trading SQLite: data/paper_trading.db (環境変数 PAPER_TRADING_SQLITE_PATH)
- PID ファイル: data/execution.pid (Settings.pid_file_path)
- Kill フラグ: data/kill.flag (Settings.kill_flag_path)
- Stop フラグ: data/stop_requested.flag
- ログ: logs/<app_name>.log

最終メモ
--------
- 本リポジトリの多くのコンポーネントは外部資源（市場データ、OpenAI、kabuステーション 等）に依存します。デプロイ前に validate_config で設定を確認し、テスト環境（paper_trading）で動作確認を行ってください。
- AI 機能は外部 API 呼び出しを伴うため、レート制限や料金に注意してください。失敗時は安全側にフォールバックする設計になっていますが、期待どおりの結果が出るかは運用で確認してください。