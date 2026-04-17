KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買基盤（プロトタイプ）です。  
主要機能として注文発行・再同期（Reconciler）を行う ExecutionEngine、システム／注文／リスクを監視する MonitoringEngine、ポートフォリオ構築・ポジションサイズ計算、ファクター計算・リサーチユーティリティ、ニュースを用いた AI スコアリング等を備えます。  
設計方針として「本番の発注系と分析系を分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しは明示的にキーを必要とする」「DB migration を最小限に保つ」ことを重視しています。

主な機能
--------
- Execution
  - ExecutionEngine による発注フロー（Broker クライアント経由）
  - OrderManager / OrderRepository による状態管理・重複防止
  - Reconciler による再起動後の自動復旧・ポジション差分検出
  - paper_trading モード（モックブローカー & data/paper_trading.db）
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、PID ステータス監視
  - TradeMonitor: 滞留注文 / 約定価格異常検出
  - RiskMonitor: ドローダウン／ポジション上限監視とダッシュボード更新
  - KillSwitch: 条件達成で停止フラグ（data/kill.flag）を書き込み ExecutionEngine を停止
  - AlertManager: LINE Push によるアラート配信（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード読み出し (read-only)
- Portfolio construction
  - 候補選定、等重・スコア重み付け、セクターキャップ、レジーム乗数、ポジションサイジング（lot 整数丸め）
- Research / Data
  - DuckDB 経由でファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp: OpenAI を利用したニュースセンチメント集約スコアリング（ai_scores テーブルへ書込）
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- ツール
  - paper_verification_report: paper_trading DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）

セットアップ
------------
前提
- Python 3.10 以上（typing の新しい構文を使用）
- SQLite（組み込み）、DuckDB、ネットワークアクセス（ブローカー / OpenAI / LINE を利用する場合）

1. リポジトリをクローン / 取得
   - プロジェクトルートに移動。パッケージは src/ 配下に配置されています。

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必要な主要依存例:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

4. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な必須/重要環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY （AI 機能を使う場合は必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH: paper_trading モード時の DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE: paper_trading の fill モード（instant / partial / never / reject、デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（デフォルト 60）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート用（任意）
   - .env のサンプルは .env.example を参考に作成してください。

初期化・DB
- monitoring 側のテーブルは init_monitoring_db() により冪等的に作成されます（run_monitoring / run_execution の起動時に自動実行）。
- Paper Trading は本番 DB と完全分離して data/paper_trading.db を利用します（KABUSYS_ENV=paper_trading）。

使い方
------
起動スクリプト
- ExecutionEngine 起動（発注エンジン）
  - 簡易起動:
    - KABUSYS_ENV=live python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading では MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録されます
  - 起動時に data/execution.pid が作成され、停止は data/stop_requested.flag または data/kill.flag で行えます。

- Monitoring 起動（ポーリング監視）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 停止は data/stop_requested.flag を作成するか Ctrl+C

- Streamlit ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only で開きます（存在しない場合はエラーメッセージ）。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等と PASS/FAIL 判定

プロセス制御 / フラグファイル
- 停止制御:
  - data/stop_requested.flag — run_execution / run_monitoring が監視している手動停止フラグ
  - data/kill.flag — KillSwitch（監視側）が書き込む停止フラグ（Execution 側が検知）
- PID:
  - data/execution.pid — ExecutionEngine 起動時に書き込まれる PID（SystemMonitor はこの PID をチェックしてプロセス生存確認を行う）

構成（主なディレクトリ / ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス：環境変数管理、自動 .env ロード、KABUSYS_ENV 判定、各種パス / 設定を提供
- run_execution.py
  - ExecutionEngine の起動スクリプト（paper_trading の DB 分離、MockBroker 切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- execution/
  - order_manager.py, execution_engine.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - 注文状態管理、ブローカー API 抽象化、再同期ロジック
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル作成・マイグレーション）
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py — 各 Monitor を束ねるオーケストレータ
  - alert_manager.py — LINE 通知
  - kill_switch.py — 停止フラグ管理
  - streamlit_dashboard.py — 監視ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築関連の純粋関数
- research/
  - factor_research.py, feature_exploration.py — DuckDB を用いたファクター計算・IC など
- ai/
  - news_nlp.py, regime_detector.py — OpenAI を使ったニュース NLP / レジーム判定（API キー必須）
- data/ (実行時に生成される想定)
  - monitoring.db（SQLite）、kabusys.duckdb（DuckDB）、paper_trading.db（paper モード）など
- tools/
  - paper_verification_report.py — paper_trading の検証レポート生成

運用上の注意 / トラブルシューティング
-----------------------------------
- 環境変数が不足していると Settings が ValueError を投げます（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- OpenAI を使用する機能は OPENAI_API_KEY の設定が必要です。設定がない場合は呼び出しで ValueError。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring_db.init_monitoring_db は起動時に呼ばれ、既存 DB へのカラム追加（マイグレーション）も行います。
- Process priority / CPU affinity の設定は utils/process_priority.py で抽象化され、Windows / POSIX を吸収します。権限不足で設定できない場合は警告ログを出してスキップします。
- paper_trading モードでは本番 DB を上書きしないよう独立した SQLite を使用します。デフォルト path は data/paper_trading.db。

開発・拡張メモ
----------------
- DuckDB 接続を受ける research / ai モジュールは本番の注文系に影響しない（read-only 想定）。
- LLM 呼び出しはリトライロジックやレスポンスの厳格なバリデーションを実装済み（news_nlp, regime_detector）。
- 将来的に銘柄別 lot_size、より詳細な価格フォールバック、paper_trading の挙動変更などが見込まれます（ソース内 TODO を参照）。

貢献
----
バグ報告や改善提案は Issue を立ててください。プルリクエスト歓迎です。設計方針に沿った実装（特にルックアヘッドバイアス回避、DB 一貫性）を重視してください。

以上。README に含める補足や、.env.example のテンプレートやコマンド例（systemd ユニット、Docker 化など）を追加したい場合は教えてください。