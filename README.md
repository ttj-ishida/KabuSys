# KabuSys

日本株自動売買システムのライブラリ兼実行スクリプト群（簡易版）。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジン/モニタリング、AI 補助（ニュース NLP / レジーム判定）、および各種ユーティリティを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件（依存）
- セットアップ手順
- 環境設定（.env）と主な環境変数
- 実行方法（主要スクリプト／使い方）
- ライブラリ利用例（AI・研究・ポートフォリオ）
- 監視・停止（Kill Switch / stop フラグ）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコンポーネント群です。
- 戦略の研究（ファクター計算、特徴量解析）、ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）、実行エンジン（発注・リスク管理）および監視（システム状態・注文履歴監視）を含みます。
- ペーパートレード用に発注ロジックをモックし、本番 DB と分離して実行できる仕組みがあります。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント算出やマクロセンチメントによる市場レジーム判定の処理を実装しています（API キーが必要）。

機能一覧
- 環境読み込み / ウィザード（`.env` の対話的作成）
- 設定検証 CLI（.env と config/*.yaml のチェック）
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV による paper_trading / live の切替
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用
- 監視ポーリングスクリプト（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL による間隔変更
- Monitoring DB：SQLite に system_status / trade_logs / positions / risk_logs / dashboard を格納
- AI モジュール
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄別センチメントを ai_scores に書込む
  - regime_detector: ETF（1321）MA とマクロ記事の LLM センチメントを合成して market_regime を算出
- 研究モジュール（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算、統計サマリー
- ポートフォリオ構築（portfolio）
  - 候補選定、等重／スコア重み、セクター上限適用、ポジションサイジング（リスクベース等）
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定を行うレポート生成

必要条件（依存）
- Python 3.9+
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の簡易検証に使用、なくても動くが警告が出ます）
- SQLite（標準ライブラリで利用）
- 上記は環境により変わるので実際は requirements.txt 等を参照してください（本リポジトリには含まれていない想定）。

セットアップ手順
1. リポジトリをクローン
   - git clone … && cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトの requirements.txt がある場合はそれを使用）

4. データディレクトリ作成（実行時に自動作成される箇所もありますが、明示的に作る場合）
   - mkdir -p data logs

5. .env の作成（推奨）
   - python -m kabusys.config_setup
     - 対話式ウィザードで .env を作成・更新できます。
   - もしくは .env を手動で作成（.env.example を参考に）

6. 設定検証（任意だが起動前に推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告をエラー扱い）:
     - python -m kabusys.validate_config --strict

主な環境変数（一覧・説明）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、発注は MockBrokerClient を使いデータは data/paper_trading.db に保存される
- PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル格納ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。本番で 1 は危険）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動で .env を読み込まない

実行方法（主要スクリプト）
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と完全に分離）
    - 実行中は data/execution.pid に PID を書き込み
    - data/stop_requested.flag（または project/data/stop_requested.flag）が存在すると停止します

- 監視ポーリング起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path を使って監視ログを記録します（環境に依らず）

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH が優先されます）

ロギング
- kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出します。
- デフォルトでコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリが作れない場合はコンソール出力のみで継続します。

AI 機能の利用（簡単な例）
- ニューススコアリング（programmatic）
  - from datetime import date
  - import duckdb
  - from kabusys.ai import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")

注意:
- OpenAI 呼び出しには OPENAI_API_KEY が必要です。スクリプトは API エラー時に安全にフォールバックする設計ですが、キー自体が未設定の場合は例外になります。

監視と Kill Switch
- RiskMonitor / SystemMonitor / TradeMonitor を定期実行し、条件により KillSwitch が data/kill.flag を書き込みます（ExecutionEngine は起動時・ループ中にこのフラグを検出して停止できます）。
- kill.flag の自動クリア設定は KILL_FLAG_CLEAR_ON_START で制御します（本番では 0 推奨）。

データベース（Monitoring DB）概要
- SQLite に以下のテーブルを持ちます（init_monitoring_db により作成・マイグレーション実施）:
  - system_status: CPU/メモリ/ディスク/プロセス稼働状況ログ
  - trade_logs: 発注イベントログ（event_type: Created/Sent/Filled など）
  - positions: 現在の保有ポジション
  - risk_logs: リスク関連アラートログ
  - dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / 設定管理
    - config_setup.py         — .env 対話式ウィザード
    - validate_config.py      — 設定検証 CLI
    - run_execution.py        — ExecutionEngine 起動スクリプト
    - run_monitoring.py       — SystemMonitor ポーリングスクリプト
    - utils/
      - logging_setup.py      — ログ設定ユーティリティ
      - process_priority.py   — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py      — SQLite 永続層
      - monitoring_engine.py  — 各 Monitor を束ねる
      - system_monitor.py     — システム状態 / データ鮮度監視
      - risk_monitor.py       — ドローダウン / ポジション上限監視
      - trade_monitor.py      — （注文監視ロジック; ここでは参照されるが詳細は省略）
      - kill_switch.py        — フラグファイルによる停止シグナル
      - alert_manager.py      — （アラートの送信管理; 省略）
    - execution/              — 発注・リスク管理・OrderManager 等（実行系）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py

（注）リポジトリ内の一部ファイルは本 README に含めた説明向けに抜粋されています。実際のファイル全体を参照して実行してください。

補足（運用上の注意）
- 本番（KABUSYS_ENV=live）では必須環境変数や通知の設定（LINE 等）を確実に行い、KILL_FLAG_CLEAR_ON_START は 0 にしてください。
- .env は絶対にリポジトリにコミットしないでください（秘密情報を含むため）。
- DuckDB や SQLite のパスは .env で変更可能。ペーパートレード用 DB は本番 DB と物理的に分離して運用してください。

---

以上が本リポジトリの README（日本語）概略です。必要であれば以下を追加で用意します：
- 各モジュールの詳細 API/関数リファレンス（docstring からの自動生成）
- サンプル .env.example
- CI / デプロイ手順（systemd / cron / supervisor 用の例）

どれを追加しますか？