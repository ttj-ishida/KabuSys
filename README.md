# KabuSys — 日本株自動売買システム（README 日本語）

このリポジトリは日本株向けの自動売買（Execution）と監視（Monitoring）、研究・分析（Research）、AI を用いたニュース解析などを含むシステムの一部実装です。本 README ではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

注意: 実装は一部抜粋です。実運用前に .env / config/*.yaml の値や DB のバックアップ、実際のブローカー接続などを十分に検証してください。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 使い方（主要スクリプト・コマンド）
- 環境変数（主要項目）
- 運用時の注意点（停止・Kill Switch 等）
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。
- 主な役割:
  - ExecutionEngine: 発注ロジック・リスク管理・注文管理を担う（本番 / ペーパートレード対応）。
  - Monitoring: システム稼働状況・注文やリスクイベントの監視、アラート発行、Kill Switch（自動停止）機能。
  - Research / Data: DuckDB ベースでファクター計算や特徴量探索を行う。
  - AI: OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント解析や市場レジーム判定。
  - Utilities: ロギング設定・プロセス優先度設定・設定ロード等の共通ユーティリティ。

---

機能一覧（抜粋）
- Execution
  - 実際のブローカークライアントと接続して注文実行（KABUSYS_ENV=live）
  - Paper trading（KABUSYS_ENV=paper_trading）では MockBrokerClient を利用し、paper_trading 用の DB に記録（本番 DB と分離）
  - リスク管理（最大ポジション比率、利用率、回路遮断など）
- Monitoring
  - CPU / メモリ / ディスク使用率、Execution プロセスの稼働確認、データ鮮度チェック
  - トレード関連ログ（trade_logs）、リスクログ（risk_logs）、ダッシュボード集計（dashboard）を SQLite に永続化
  - Kill Switch：ドローダウンやポジション上限超過などの条件で ExecutionEngine 停止フラグを作成
  - アラート送信（LINE 等のトークンを設定すれば通知可能）
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC 計算・特徴量サマリ
- AI
  - ニュースをまとめて LLM に投げ、銘柄ごとのセンチメント（ai_scores）を生成・保存
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定でペーパートレード DB を解析）
- Utilities
  - 統一的なロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env の対話式生成ウィザード / 設定検証 CLI

---

前提条件
- Python 3.10 以上（コード内で X | Y 型アノテーションを使用しているため）
- 主要依存パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の内容チェック用）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- ネットワーク接続（OpenAI API を利用する場合）

例（依存インストール）:
pip install duckdb psutil openai pyyaml

※ 実際の requirements.txt があればそちらを使ってください。

---

セットアップ手順（ローカル開発用の例）
1. リポジトリをクローン / ワークツリーに移動
2. Python 仮想環境作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
3. 依存インストール
   pip install duckdb psutil openai pyyaml
4. .env の作成（ウィザード推奨）
   python -m kabusys.config_setup
   → 対話形式で .env を生成します（重要なシークレットは表示がマスクされます）
5. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります:
   python -m kabusys.validate_config --strict
6. 必要なディレクトリ作成
   - data/ : データベース・フラグファイル等を配置（SQLite ファイルはデフォルトで data/ 配下）
   - logs/ : ログ出力先（自動作成されますが権限に注意）

---

使い方（主要コマンド・実行例）
- ExecutionEngine を起動する（発注エンジン）
  python -m kabusys.run_execution

  動作モードは KABUSYS_ENV 環境変数で切替:
  - development: 実発注なし（開発用）
  - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録
  - live: 本番ブローカーに接続して実発注

- Monitoring（監視ループ）を起動する
  python -m kabusys.run_monitoring

  ポーリング間隔を環境変数で上書き可能:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  監視は Settings に定義された sqlite_path（デフォルト data/monitoring.db）へログを書きます。
  run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を使用します（監視は単一 DB に集約）。

- .env 対話ウィザード
  python -m kabusys.config_setup

- 設定検証 CLI
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを上書き可能:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ログ:
- ログファイルはデフォルトで logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）に日次ローテーションで出力されます。
- ロギングは stdout にも出力されます。

停止・Kill Switch:
- 手動停止（run_execution / run_monitoring を安全に終了）:
  - プロセス内部で定期的に data/stop_requested.flag の存在をチェックしています。ファイルを作成すると次回ループで終了します。
    例: touch data/stop_requested.flag
- Kill Switch（Monitoring が条件を満たした場合、Execution に停止を要求）:
  - Monitoring 内の KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path で上書き可能）。
  - Execution 側は Kill Switch の存在等を参照して発注を止めるよう設計されています（詳細は ExecutionEngine の実装参照）。

---

主要な環境変数（抜粋）
- 必須（最低限セット推奨）
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- モード・ログ等
  - KABUSYS_ENV : execution モード（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL   : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

- DB / ファイルパス
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH : Execution の PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH : Kill Switch のフラグファイルパス（デフォルト data/kill.flag）

- Paper trading 固有
  - PAPER_FILL_MODE : instant / partial / never / reject（MockBroker の約定挙動）

- Monitoring
  - MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒。run_monitoring で使用。デフォルト 60）

- OpenAI
  - OPENAI_API_KEY : OpenAI API を使う場合に必要（AI モジュールで使用）

- LINE（通知）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

詳細は kabusys.config.Settings のプロパティ定義を参照してください。

---

運用上の注意点
- paper_trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。本番口座での誤発注を避けるため、KABUSYS_ENV の設定を必ず確認してください。
- 本番モード（KABUSYS_ENV=live）の場合は LINE トークンなど通知設定を必ず確認し、validate_config の警告を無視しないでください。
- Kill Switch 関連の設定（KILL_FLAG_CLEAR_ON_START 等）は本番では慎重に扱ってください。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると Kill Switch が自動クリアされ、重大イベントを見逃す可能性があります。
- ログディレクトリや data/ のパーミッションに注意。ログファイル・DB ファイルへの書込み権限が必要です。

---

ディレクトリ構成（主要ファイル説明）
（リポジトリルートの src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
    - パッケージ定義（__version__ 等）
  - config.py
    - 環境変数 / 設定の読み込み・ラッパー（Settings クラス）
    - .env 自動読み込みロジックを持つ（プロジェクトルート検出）
  - config_setup.py
    - .env を対話的に生成・更新するウィザード
  - validate_config.py
    - .env や config/*.yaml の整合性チェック CLI（--strict オプションあり）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じた DB 選択、プロセス優先度設定、停止フラグ検知）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数対応）
  - utils/
    - logging_setup.py : ログ設定ユーティリティ（stdout + 日次ローテートファイル）
    - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ（Windows / POSIX 対応）
  - execution/  (発注周りの実装群)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - monitoring/
    - monitoring_db.py : SQLite 永続化層（テーブル作成・マイグレーション・読み書きヘルパ）
    - system_monitor.py  : CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py など
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py : 銘柄選定・重み付け・株数決定・セクター上限等
  - research/
    - factor_research.py, feature_exploration.py : DuckDB を使ったファクター計算・IC・統計サマリ等
  - ai/
    - news_nlp.py : ニュースを LLM でセンチメントスコア化して ai_scores に書き込む
    - regime_detector.py : ETF MA200 とマクロニュースを組合せた市場レジーム判定
  - tools/
    - paper_verification_report.py : ペーパートレード検証レポートを生成するスクリプト

その他:
- data/ : DB ファイル（data/monitoring.db, data/paper_trading.db 等）、フラグファイル（data/kill.flag, data/stop_requested.flag）、PID ファイルなどを配置（実行時に作成）。
- logs/ : ログ出力先（logs/<app>.log）

---

補足（開発者向け）
- DuckDB 接続を渡して純粋関数的に研究（research）処理を行う設計になっています。研究用関数は外部副作用を行わない前提です。
- AI 周りは OpenAI SDK（OpenAI の新しい SDK を使う設計）を使います。テスト用に API 呼び出し関数をモック出来るように分離設計されています。
- monitoring の DB スキーマは init_monitoring_db() で冪等的に作られ、必要に応じて簡単なマイグレーション（カラム追加）を行います。

---

問題報告・貢献
- バグ報告・改善提案は issue を立ててください。大きな変更は事前に相談してください。

---

以上。必要であれば README に載せる具体的な例（.env.example の内容、実行フロー図、より詳しい設定項目の説明など）を追加で作成できます。どの情報を詳しく増やすか教えてください。