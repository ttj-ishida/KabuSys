# KabuSys — README

簡潔な説明書（日本語）

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / 実行例）
- 主要な環境変数
- 停止・Kill スイッチについて
- ディレクトリ構成（主要ファイルの概観）
- 開発メモ / 依存関係

---

プロジェクト概要
- KabuSys は日本株向けの自動売買・研究プラットフォームの一部を構成する Python パッケージです。
- 発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リスク管理ロジック、リサーチ（ファクター計算 / 特徴量解析）、AI を使ったニュースセンチメント評価などを含みます。
- 本リポジトリのコードは、SQLite（監視 / ペーパートレード DB）、DuckDB（分析 / 研究用 DB）、OpenAI（ニュース / マクロ評価）などと連携して動作します。

---

主な機能一覧
- ExecutionEngine 起動/管理（実取引 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、本番 DB と分離された paper_trading DB に記録
- Monitoring（System / Trade / Risk）および Kill Switch
  - システムリソース、データ鮮度、滞留注文、ドローダウンなどの監視と永続化
  - 条件に応じた kill.flag の書き込みによるエンジン停止
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ決定）
- リサーチ機能
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ
- AI モジュール
  - ニュース NLP（OpenAI）による銘柄別センチメント評価と market regime 判定
- 運用ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

---

セットアップ手順（ローカル開発用）
1. Python 環境
   - 推奨: Python 3.9+
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   - 必須想定パッケージ（プロジェクトに明示された主な依存）
     - duckdb, psutil, openai
     - （オプション）PyYAML（config/*.yaml の検証で使用）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がない場合は上記を目安にしてください）

3. 環境変数 / .env の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - ウィザードで最低限設定すべき項目:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH / SQLITE_PATH（デフォルトあり）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 作成後、設定検証:
     - python -m kabusys.validate_config
     - --strict フラグを付けると警告も失敗扱い（exit 1）

4. データディレクトリの作成
   - デフォルト DB / pid / flag のパスは data/ 以下に置かれることを想定
   - 必要であれば手動で作成:
     - mkdir -p data logs

---

使い方（起動 / 実行例）
- ExecutionEngine（実行エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - process priority を "high" に設定し、SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は paper_trading SQLite（PAPER_TRADING_SQLITE_PATH）を使う
    - 停止フラグ（data/stop_requested.flag）が既にあれば起動せず終了

- Monitoring（常駐監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は本番 sqlite_path を環境にかかわらず使用（監視ログは単一の monitoring.db に記録）

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- .env 作成ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート（ローカル実行）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）

- 研究機能 / ライブラリの呼び出し（Python スクリプト内）
  - 例: from kabusys.research import calc_momentum
  - DuckDB の接続オブジェクトを渡して関数を呼ぶ

ログ
- ログは logs/<app_name>.log に日次ローテートで保存されます（デフォルト: 30日保持）。
- setup_logging(app_name="execution") のように各起動スクリプトで統一的に設定されます。

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker + data/paper_trading.db を使用
  - live: 本番取引（注意して設定すること）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の Fill 挙動（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

停止・Kill スイッチについて
- 実行エンジン / 監視ループの停止は主に以下のフラグファイルで制御されます:
  - data/stop_requested.flag — run_execution / run_monitoring が検知して安全に停止
  - data/kill.flag — KillSwitch が書き込む（条件を満たした場合に ExecutionEngine に停止シグナルを送る）
- KillSwitch はリスクモニタ（ドローダウン、ポジション上限等）による判定で kill.flag を書きます。
- ExecutionEngine 起動時には KILL_FLAG_CLEAR_ON_START の値に応じて kill.flag を自動消去する設定があるため、本番では 0 を推奨します。

---

ディレクトリ構成（主要ファイルの概観）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み（.env / .env.local）と Settings クラス
  - config_setup.py
    - .env を対話式に作成・更新するウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリング開始スクリプト
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - （注文管理・エンジン本体）
  - monitoring/
    - monitoring_db.py — SQLite 永続層
    - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    - ポートフォリオ構築・ポジションサイズ計算・セクターキャップなど
  - research/
    - factor_research.py, feature_exploration.py
    - ファクター計算・IC・統計機能
  - ai/
    - news_nlp.py, regime_detector.py
    - OpenAI を用いたニュース・マクロ評価
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py, process_priority.py, ほかユーティリティ
  - monitoring_db / data などのデータファイル（プロジェクトルートの data/、logs/ を想定）

補足（開発メモ）
- DuckDB への接続は各モジュールに渡して SQL と Python を組み合わせて処理します。prices_daily / raw_financials 等のテーブルを想定しています。
- OpenAI SDK のエラー（429、タイムアウト、5xx）は指数バックオフでリトライする実装になっていますが、APIキーや料金には注意してください。
- run_execution / run_monitoring はプロセス優先度を上げようとします（psutil が必要）。権限不足や未対応 OS の場合は警告を出してスキップします。
- SQLite DB のマイグレーション（簡易）は monitoring_db.init_monitoring_db に組み込まれています（列追加など）。

---

よくある操作フロー（例）
1. 仮想環境作成、依存インストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定をチェック
4. python -m kabusys.run_execution を起動（本番は systemd 等で管理）
5. 別プロセスで python -m kabusys.run_monitoring を常駐させ監視・アラートを行う
6. ペーパートレードの結果解析は python -m kabusys.tools.paper_verification_report を実行

---

サポート / 注意点
- 本 README はリポジトリ内のコードから抽出した仕様の要約です。実際に運用する際は .env の値、DB パス、ログ設定等を必ず確認してください。
- KABUSYS_ENV=live の場合は本番取引に関わる設定が有効になるため、LINE 通知や kill flag の扱いなど十分に注意してください。
- セキュリティ: .env は機密情報を含むため絶対にバージョン管理システムにコミットしないでください。

---

必要であれば、この README をベースに「環境変数一覧を表形式で詳述」「systemd / Docker 用の起動例」「CI テストのセットアップ」等の追加ドキュメントを作成します。どの部分を詳しくしたいか教えてください。