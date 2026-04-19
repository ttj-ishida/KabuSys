KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買に向けたモジュール群です。本リポジトリは以下の主要機能を備えます。

- 実行エンジン（ExecutionEngine）の起動スクリプト（run_execution）  
  — 実際の発注（live）またはペーパートレード（paper_trading）を行う。
- 監視ループ（MonitoringEngine）の起動スクリプト（run_monitoring）  
  — システム状態・注文状態・リスクを定期チェックし、アラートや Kill Switch を管理。
- ポートフォリオ構築 / ポジションサイジング / リスク調整（portfolio）  
  — 候補選定・重み付け・ロット丸め・セクターキャップなど。
- リサーチ・ファクター計算（research）  
  — モメンタム、バリュー、ボラティリティ等を DuckDB 上で計算。
- AI 補助（ai）  
  — ニュース NLP による銘柄センチメント、レジーム判定（OpenAI）など。
- 監視用永続層（monitoring/monitoring_db）と各種モニタ（system/trade/risk）  
- CLI 補助ツール  
  - 環境設定ウィザード: python -m kabusys.config_setup  
  - 設定検証: python -m kabusys.validate_config  
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

主な機能一覧
--------------
- 実行／監視プロセスの起動スクリプト（run_execution, run_monitoring）
- .env と環境変数の自動ロード（config）
- 環境設定ウィザード（config_setup）と事前検証ツール（validate_config）
- DuckDB / SQLite を用いたデータ処理（research, ai, monitoring）
- OpenAI との連携を考慮した堅牢な API 呼び出し（リトライ、パース検証、バッチ処理）
- ポートフォリオ構築・リスク管理ロジック（等重配分、スコア配分、リスクベース等）
- 監視ログ（system_status, trade_logs, risk_logs, positions, dashboard）永続化 API

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>
   - 例: git clone https://example.com/your/repo.git

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows PowerShell: .venv\Scripts\Activate.ps1）

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要なパッケージ（明示的な requirements がない場合）:
     - pip install duckdb psutil openai
   - 任意（YAML 検証を行う場合）:
     - pip install PyYAML

4. ディレクトリ作成（初回）
   - mkdir -p data logs

5. 環境変数の設定（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または .env を直接作成し、例（必須/重要）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=... （AI 機能を使う場合）
     - PAPER_FILL_MODE=instant|partial|never|reject
     - KILL_FLAG_CLEAR_ON_START=0

   - 自動ロードはプロジェクトルートの .env / .env.local を読み込みます。
   - 自動ロードを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------

基本的な CLI 実行例（パッケージを src 配下に置いている場合はプロジェクトルートから実行）:

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で切替（paper_trading では MockBrokerClient を使用し paper DB に記録）。

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: export MONITOR_POLL_INTERVAL=30
  - 監視は常に（環境にかかわらず）本番 sqlite_path を使用します（監視 DB を分離しない設計）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止／フラグ制御
- 実行ループ停止（run_execution, run_monitoring）:
  - プロジェクト内 data/stop_requested.flag を作成すると監視ループ・エンジンは安全に終了します。
- Kill Switch（監視による ExecutionEngine の強制停止）:
  - data/kill.flag を書き込むと ExecutionEngine 側で検出して停止します。
  - KillSwitch API は冪等で既存ファイルの二重書き込みは行いません。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ログ
- ログは logs/ ディレクトリに保存されます（日次ローテーション、30 日保持）。
- ログファイル名はアプリ名プレフィックス（例: execution.log, monitoring.log）。
- コンソールは stdout に出力されます（stderr ではない点に注意）。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development, paper_trading, live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring で使用）
- PAPER_FILL_MODE — paper_trading の注文約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主要ファイル）
--------------------------------

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数読み込み / Settings クラス、自動 .env ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の環境検査 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（PID/停止フラグ管理）
  - run_monitoring.py — SystemMonitor ポーリングスクリプト（MONITOR_POLL_INTERVAL）
  - utils/
    - logging_setup.py — 共通ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出・丸め・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースから銘柄センチメントを OpenAI で評価して ai_scores に書込
    - regime_detector.py — ma200 + マクロセンチメントで市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化 API（テーブル作成・マイグレーション含む）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス存否のチェック
    - trade_monitor.py — （注）trade_monitor の実装がプロジェクト内にある想定
    - risk_monitor.py — ドローダウン、ポジション上限の監視と dashboard 更新
    - kill_switch.py — kill.flag 書込みロジック
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行ロジック
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

設計上の注意点 / 運用メモ
-------------------------
- 監視（monitoring）は環境にかかわらず本番 sqlite_path を参照します。環境分離が必要なら設定でパスを分けてください。
- run_execution は KABUSYS_ENV=paper_trading の時に MockBrokerClient を使用し、paper 専用 DB に記録します（本番 DB と分離）。
- OpenAI を使用する機能は API キーが必須です。API 呼出しはリトライ・レスポンス検証を行いますが、API 失敗時はフェイルセーフ（0.0 相当）で継続する実装箇所があります。
- SQLite / DuckDB ファイルはデフォルトで data/ 配下に作成されます。バックアップやロック対策（同一ファイルへの同時アクセス等）を運用で考慮してください。
- ログディレクトリ作成やファイル作成権限がない場合、ログはコンソール出力のみになります（utils/logging_setup.py の挙動）。

開発・テスト
-------------
- モジュール単位で関数が純粋関数（DB 参照無し）として実装されている箇所が多く、ユニットテストが書きやすい設計です（portfolio 系など）。
- OpenAI 呼び出しや外部 API はモック可能な分離設計になっています（内部 _call_openai_api を patch する等）。

問い合わせ / 貢献
------------------
バグ報告、改善提案は Issue を開いてください。プルリクエストは歓迎します。README に未記載の運用ポリシーや外部依存があれば合わせてドキュメント化してください。

以上。必要であれば README に含める技術的詳細（API スキーマ、DB スキーマ例、起動スクリプトの systemd ユニット例 など）を別途作成します。どの情報を追加したいか教えてください。