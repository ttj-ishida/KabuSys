README.md

プロジェクト概要
- KabuSys は日本株の自動売買／リサーチ基盤のコードベースです。
- 主な目的はシグナル生成 → ポートフォリオ構築 → 注文実行 → 監視／リスク管理、並びに研究（ファクター計算）・AI（ニュースセンチメント／レジーム判定）支援です。
- エンジン（ExecutionEngine）と監視コンポーネント（MonitoringEngine）が分離されており、本番／ペーパートレード切替、ログ保存（ファイル／SQLite／DuckDB）、外部API（kabuステーション、J-Quants、OpenAI）連携が組み込まれています。

主な機能一覧
- 注文実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカ抽象化（paper_trading では MockBrokerClient）
  - OrderManager / RiskManager / Reconciler などの実装（発注・リスク制御）
- 監視（Monitoring）
  - SystemMonitor：CPU／メモリ／ディスク／プロセス状態／データ鮮度監視
  - TradeMonitor / RiskMonitor：注文滞留やドローダウンなどの監視とアラート
  - KillSwitch：異常時に data/kill.flag を書き込み ExecutionEngine を停止する仕組み
  - 永続化：SQLite に監視ログを保存（monitoring.db）
- ポートフォリオ構築
  - 候補選定（スコア順）、重み付け（等配分／スコア加重）
  - ポジションサイズ計算（risk_based, equal, score ベース）
  - セクター上限・レジーム乗数の適用
- 研究用モジュール（duckdb 経由）
  - ファクター計算（モメンタム、ボラティリティ、バリューなど）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）連携
  - news_nlp: ニュースを LLM でセンチメント解析して ai_scores に保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: 環境変数・config/*.yaml の検証 CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

動作要件（目安）
- Python 3.10+
  - （コード内で | 型注釈や match を使わないが、Union 表記短縮を使用しているため 3.10 以上を推奨）
- 必要な主要パッケージ（実行に必要なもの）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（validate_config の YAML パース時に利用）
- SQLite（標準ライブラリ sqlite3 を使用）

セットアップ手順
1. リポジトリをクローン / 取得
   - この README はパッケージのルート（pyproject.toml/.git があるディレクトリ）を想定しています。

2. Python 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - ※requirements.txt があれば pip install -r requirements.txt

4. 初期設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記サンプル参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。

環境変数（主要）
- 必須（実行に必須なもの）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
    - paper_trading の場合、MockBrokerClient を使用し DB を data/paper_trading.db に保存
- DB / ログ関連
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト data/monitoring.db) — 監視は常に sqlite_path を使います
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR (ログファイル保存先、デフォルト logs/)
- OpenAI / LINE
  - OPENAI_API_KEY （news_nlp / regime_detector で使用）
  - LINE_CHANNEL_ACCESS_TOKEN（任意）
  - LINE_USER_ID（任意）
- その他
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動

.env のサンプル（簡易）
- .env には機密情報が含まれるため、Git 管理しないでください。
- 例:
  JQUANTS_REFRESH_TOKEN=your_jquants_token
  KABU_API_PASSWORD=your_kabu_password
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  OPENAI_API_KEY=sk-xxxxxxxx
  LOG_LEVEL=INFO
  KILL_FLAG_CLEAR_ON_START=0
  PAPER_FILL_MODE=instant

基本的な使い方
- .env 作成 → 設定検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- 監視ループを起動（monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は Settings.sqlite_path を常に使用（KABUSYS_ENV に依存せず本番向け監視 DB を参照）

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定してペーパートレードモードで起動すると MockBrokerClient を使用し data/paper_trading.db に記録します
  - 実行中に data/stop_requested.flag を作成すると安全に停止処理が行われます（run_execution/run_monitoring 共通の停止フラグ）

- Kill Switch（自動停止）
  - KillSwitch により一定条件（ドローダウン超過やポジション上限超過）で data/kill.flag を書き込み ExecutionEngine 停止をトリガーします
  - KILL_FLAG_CLEAR_ON_START=1 による自動クリアは本番では危険なのでデフォルト 0 を推奨

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI スコアリング / レジーム判定（ライブラリ利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは duckdb 接続（DuckDBPyConnection）を受け取り、DB 内のテーブルを読み書きします
  - OPENAI_API_KEY の設定が必要（引数で上書き可能）

ログ
- logging_setup.setup_logging を各起動スクリプトで使用
- デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保持）へ出力
- LOG_DIR 環境変数でログ出力先を変更可能

停止・一時停止フラグ
- data/stop_requested.flag
  - run_monitoring / run_execution が終了検出に使用するフラグファイル（存在すると起動ループを抜ける）
- data/kill.flag
  - KillSwitch によって書き込まれ、ExecutionEngine 停止のトリガーとなる（存在確認を ExecutionEngine 側で行う設計）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - execution/               — 発注エンジン関連（Engine / OrderManager / RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（monitoring DB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

補足・運用上の注意
- 本リポジトリは実際の発注を行える設計要素を含みます。KABUSYS_ENV を必ず確認し、本番（live）設定ではキー、アドレス、フラグ類を慎重に管理してください。
- .env は絶対に Git 等へコミットしないでください。
- OpenAI 連携を使う場合は API キーの利用上限・コストを考慮し、バッチサイズやリトライロジック（実装済）を確認してください。
- monitoring は常に sqlite_path（本番向け監視 DB）を参照します。テスト用に監視 DB を分離したい場合は sqlite_path を別ファイルに設定してください。

トラブルシューティング
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（警告ログが出ます）。
- validate_config により設定の必須項目やパスの存在などを事前検査できます。

ライセンス / バージョン
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報等はリポジトリのルートに別途配置してください（本 README には含まれていません）。

以上。必要であれば README に「開発用のテスト手順」「ユニットテストの実行方法」「CI 設定例」などの追加節を作成します。どの情報を補足しますか？