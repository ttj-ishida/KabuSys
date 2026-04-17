# KabuSys

KabuSys は日本株向けの自動売買・研究・監視プラットフォームのミニマル実装例です。  
このリポジトリには、取引実行エンジン、監視（Monitoring）モジュール、ポートフォリオ構築ロジック、リサーチ用ユーティリティ、AI を用いたニュース/レジーム判定など、実運用を想定した複数コンポーネントが含まれます。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境変数（主な設定）
- 実行方法
- ディレクトリ構成（抜粋）
- 注意事項 / トラブルシューティング

---

## プロジェクト概要
KabuSys は以下の目的を持つモジュール群を含みます。

- ExecutionEngine: ブローカー API と接続して注文発行・状態管理を行う。paper_trading モードでは MockBroker を使用して本番 DB と分離。
- Monitoring: システム状態・注文状態・リスク（ドローダウン・ポジション上限等）を定期チェックし、SQLite にログを残す。LINE Push によるアラート送信や kill flag によるエンジン停止が可能。
- Portfolio construction: 候補選定、重みづけ、ポジションサイズ計算、セクター制限などの純粋関数群。
- Research: DuckDB 上の時系列データを用いたファクター計算・特徴量探索ユーティリティ。
- AI モジュール: ニュース記事のセンチメント（OpenAI）や市場レジーム検出（OpenAI + MA200）を行い、DuckDB テーブルへ書き込むツール群。
- Tools: Paper Trading の検証レポート生成や Streamlit ベースの監視ダッシュボードなど。

---

## 主な機能一覧
- システム監視（CPU/MEM/Disk、Execution プロセス生存チェック、データ鮮度）
- 注文監視（滞留注文検出、約定価格異常検出）
- リスク監視（ドローダウンアラート、ポジション上限アラート）
- Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
- ExecutionEngine（live / paper_trading の切替、ブローカー抽象化）
- Reconciliation（起動時に未確定注文の同期・ポジション差分検出）
- Portfolio construction（候補選定、スコア加重・等分配、position sizing）
- Research（モメンタム・ボラティリティ・バリュー等ファクター計算）
- AI スコアリング（OpenAI を用いたニュースセンチメント / レジーム判定）
- Streamlit ダッシュボード（監視 DB の可視化）
- Paper Trading 検証レポート生成（過去期間の稼働率・成功率・レイテンシなどを集計）

---

## 必要条件
- Python 3.9+
- 主要 Python ライブラリ（抜粋）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（標準ライブラリで利用）
- （任意）J-Quants / Kabuステーションの API 情報（本番連携時）
- OpenAI API キー（ai/news_nlp、ai/regime_detector を使用する場合）

※ requirements.txt はリポジトリに含めていない場合があります。最低限上記パッケージを pip でインストールしてください。

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートへ移動します。
   - このコードベースは `src/` 配下にパッケージがあるため、開発時はプロジェクトルートから動かすか、pip の editable install を推奨します。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - pip install duckdb psutil requests openai streamlit

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと Settings モジュールが自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. data ディレクトリなどの作成（初回）
   - mkdir -p data

---

## 環境変数（主な設定項目）
Settings クラスで参照される主要な環境変数（デフォルト含む）:

- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は MockBroker を使い、DB は paper_trading 専用に分離されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject、デフォルト instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

Settings モジュールは自動でプロジェクトルートの `.env` と `.env.local` を読み込みます。OS 環境変数は保護され、`.env.local` は既存の OS 変数を上書きしません（ただし override ロジックにより振る舞いが異なります）。

---

## 実行方法（代表的なコマンド）

前提: プロジェクトルートで実行するか、src を Python path に含める / install -e すること。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor を初期化し、MONITOR_POLL_INTERVAL（default 60 秒）でループします。停止させるには Ctrl+C またはプロジェクトルートの data/stop_requested.flag を作成します。
  - 監視は環境に関係なく本番 sqlite_path（SQLITE_PATH）を使用します（監視ログは本番 DB に集める想定）。

- ExecutionEngine（発注エンジン）
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を起動してスレッドで run_session を開始します。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します。起動時に data/stop_requested.flag が存在すると起動せず終了します。停止は data/stop_requested.flag の作成で行うか、KillSwitch が data/kill.flag を書き込むと監視側の判断で停止されます。

- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: read-only モードで SQLite を開き、ポジション・注文・システム状態・リスクログを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間フィルタ: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（デフォルトは data/paper_trading.db / 環境変数 PAPER_TRADING_SQLITE_PATH）
  - 目的: Paper Trading の稼働率 / 注文成功率 / レイテンシ等の集計を行い PASS/FAIL を表示します。

- AI 関連（ニューススコア・レジーム判定）
  - 実行関数はライブラリ API として提供（score_news, score_regime）。スクリプト化している場合は環境変数 `OPENAI_API_KEY` を設定してください。
  - 注意: OpenAI 呼び出しは課金が発生します。API キー・利用制限に注意。

---

## ファイル/ディレクトリ構成（抜粋）
プロジェクトは src/kabusys パッケージ配下にモジュールを配置しています。主な構成:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - data/                           — データ関連ユーティリティ（別モジュール）
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - ...
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
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
    - process_priority.py
  - tools/
    - paper_verification_report.py

（上記は抜粋です。詳細はソースツリーを参照してください。）

---

## 主要な挙動・設計上のポイント

- Settings は .env / .env.local の自動読み込みを行う（プロジェクトルートは .git または pyproject.toml により検出）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Monitoring の DB はデフォルトで data/monitoring.db（Settings.sqlite_path）。paper_trading の Execution は別 DB（data/paper_trading.db）を使い、本番 DB と完全分離されるよう設計。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能。1 秒以上の正整数を期待します。
- プロセス優先度を高くする処理が各 run_* スクリプトの起動時に呼ばれます（utils/process_priority.py）。権限不足の環境では警告となりスキップされます。
- AI モジュールは OpenAI API のエラー（429/タイムアウト/5xx）に対して指数バックオフでリトライする設計です。API キー未設定時は例外（ValueError）を投げます。
- KillSwitch（data/kill.flag）を書き込むことで ExecutionEngine の停止を促す運用が可能。KillSwitch の評価は MonitoringEngine が担います。
- Reconciler により再起動後の注文同期・ポジション差分検出が自動で行われます（運用上重要な安全策）。

---

## よくある運用コマンド（例）

- 開発環境で監視を1回だけ実行（テスト用）:
  - python -c "from kabusys.monitoring.monitoring_engine import MonitoringEngine; print('use library API for tests')"
  - あるいはユニット的に MonitoringEngine.run_once() を呼ぶ

- Paper Trading レポート（過去期間）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボードを起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 注意事項 / トラブルシューティング
- DB ファイルのロックやパーミッションに注意。streamlit などで読み取り専用 URI を使う場合は `Path(...).as_uri() + "?mode=ro"` を利用しています。
- OpenAI API 呼び出しはコストとレート制限が発生します。API キーと使用量を管理してください。
- 実口座で運用する際は KABUSYS_ENV=live を設定し、十分なテストを行ってください。paper_trading モードでの検証を必ず行ってください。
- PID ファイル / stop flag / kill flag の管理は運用ルールを定めてください。stale PID や不正な PID ファイルは SystemMonitor が検出して削除しますが、手動操作の際は注意してください。
- Settings による .env 自動ロードはプロジェクトルート検出に .git / pyproject.toml を使います。配布後に CWD に依存せず動作することを想定した実装ですが、環境によっては明示的に環境変数をセットしてください。

---

この README はコードベースの主要な使い方・設定をまとめた概略です。詳細な API / 設計ドキュメントは各モジュールの docstring を参照してください。必要であれば導入・運用ガイド（起動スクリプト例・systemd ユニット・Dockerfile 例）も作成できます。ご希望があれば追加します。