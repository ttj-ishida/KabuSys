# KabuSys

日本株自動売買システムのコードベース（抜粋）。  
このリポジトリは取引実行・監視・ポートフォリオ構築・リサーチ・AI ニュース分類などのコンポーネントを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステム群です。以下の主要機能を持ち、モジュール設計により本番/ペーパートレードの切り替え、監視・アラート、レポート、研究用途までをカバーします。

主な設計方針：
- DuckDB / SQLite を用いたデータ格納（市場データ / 監視ログ / 注文ログ 等）
- OpenAI（gpt-4o-mini）を使ったニュース NLP（センチメント評価）
- ペーパートレードと本番口座の分離（DB・ブローカークライアント）
- 監視エンジンによるリスク監視・Kill Switch（フラグファイル）による安全停止
- 純粋関数（ポートフォリオ構築、資金配分等）を分離してテストしやすく設計

---

## 主な機能一覧

- Execution（ExecutionEngine）
  - ブローカークライアント経由で注文送信、注文状態管理、リコンシリエーション（再起動時同期）
  - Paper Trading モードで MockBroker を利用（完全分離 DB）

- Monitoring
  - SystemMonitor：プロセス状態、CPU/メモリ/ディスク使用率、データ鮮度監視
  - TradeMonitor：滞留注文チェック、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、dashboard 更新、risk_logs 書き込み
  - KillSwitch / AlertManager：条件により data/kill.flag を書き込み、LINE で通知（オプション）
  - MonitoringEngine：上記モニタの統合ポーリングループ
  - Streamlit ダッシュボード（監視ダッシュボード）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索・IC 計算・統計サマリ

- AI
  - news_nlp: raw_news を集約して OpenAI に送信し銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA200 乖離とマクロ記事の LLM センチメントを合成して市場レジーム判定

- Portfolio
  - 候補選定、重み計算（等金額・スコア加重）、セクターキャップ、ポジションサイジング（ロット丸め・aggregate cap）

- Tools
  - paper_verification_report: ペーパートレード用 SQLite DB から稼働率・成功率・レイテンシ等の検証レポートを生成

---

## セットアップ手順（開発・実行環境）

※要件ファイルはリポジトリに含めてください（例: requirements.txt）。以下は必要となる主要ライブラリ例です。
- Python 3.9+
- duckdb
- sqlite3（標準モジュール）
- psutil
- requests
- openai（または openai パッケージに対応する SDK）
- streamlit（ダッシュボード利用時）

推奨手順（UNIX 系）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存インストール（例）
   - pip install duckdb psutil requests openai streamlit

3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（実行する機能により不要なものもあります）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 推奨/便利な変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - LOG_LEVEL（DEBUG|INFO|...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を有効にする場合）

例 .env（テンプレート）
    JQUANTS_REFRESH_TOKEN=...
    KABU_API_PASSWORD=...
    OPENAI_API_KEY=...
    KABUSYS_ENV=development
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    PAPER_FILL_MODE=instant
    LOG_LEVEL=INFO

4. データディレクトリ作成
   - mkdir -p data

注意:
- プロセス優先度や CPU affinity の設定には psutil の権限が必要になる場合があります（root 権限が必要な操作がある OS もあります）。
- OpenAI の呼び出しはレート制限やタイムアウト時にリトライロジックを備えていますが、APIキーと利用量には注意してください。

---

## 使い方（実行コマンド例）

- 監視ループ（Monitoring を単独で実行）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 終了方法: data/stop_requested.flag を作成するとループは検知して終了します。また Ctrl+C（KeyboardInterrupt）で終了。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 停止: data/stop_requested.flag を作成するとエンジンに停止指示が送られます。
  - 実行中に data/execution.pid に PID が書かれます（管理用）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開くため、MonitoringEngine が書き込んでいる DB の読み取り専用ビューを表示できます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 機能（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡すと ai_scores テーブルへ銘柄別スコアを書き込みます。
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定を実行し market_regime テーブルへ書き込みます。

- Kill Switch（監視にて自動書込）
  - KillSwitch は RiskMonitor の結果等に基づき data/kill.flag を書き込みます。ExecutionEngine 起動時にこのフラグがあると起動を回避できます。
  - 管理者が手動で kill.flag を削除することで再度起動可能にできます。

---

## 注意点 / 運用メモ

- ペーパートレードと本番データは明確に分離されています（paper_trading 用 DB を使用）。
- LLM（OpenAI）呼び出しは外部依存・料金発生・レート制限があるため、運用時は API キー管理とコストに注意してください。
- MonitoringDB のスキーマは init_monitoring_db() で冪等的に作成・マイグレーションされます。
- process priority / CPU affinity の設定はプラットフォーム依存で失敗することがあり、失敗した場合はログでスキップされます。
- データ鮮度チェックは DuckDB の prices_daily テーブルの最終日付を参照します（SystemMonitor）。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数読み込み・Settings クラス（アプリ設定）
- run_monitoring.py — SystemMonitor ベースのポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）

サブパッケージ:
- ai/
  - news_nlp.py — raw_news を OpenAI でスコア化して ai_scores に書込
  - regime_detector.py — ETF MA とマクロセンチメントで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite を使った永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク、プロセス・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定価格異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルで ExecutionEngine 停止シグナル
  - alert_manager.py — LINE 通知送信とクールダウン管理
  - monitoring_engine.py — モニタ群の統合（テスト用 run_once / 本番 run）
  - streamlit_dashboard.py — Streamlit を使った監視ダッシュボード
- execution/
  - order_manager.py — 注文状態管理（OrderManager）
  - reconciler.py — 起動時のリコンシリエーション（注文・ポジション突合）
  - （その他の execution 関連モジュールは本リストの抜粋外）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数決定・aggregate cap / ロット丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading DB から検証レポートを生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

data/ (運用時に生成される想定)
- monitoring.db（SQLite、デフォルト: data/monitoring.db）
- paper_trading.db（ペーパートレード用 DB）
- kabusys.duckdb（DuckDB ファイル）
- execution.pid / stop_requested.flag / kill.flag（監視・制御用フラグ・PID）

---

## 開発・拡張のヒント

- 単体関数（portfolio や research の関数群）は副作用がなくテストしやすい設計になっています。ユニットテストを作成して部分ごとに検証してください。
- OpenAI 呼び出し部分は _call_openai_api を抽象化しており、テスト時はモック差し替えが可能です。
- MonitoringDB はスキーマアップデートに対する簡易マイグレーションロジックを含みます（カラム追加等）。大きな変更を加える際は互換性に注意してください。
- 実運用ではログ収集（ファイル or 集約サービス）やプロセスマネージャ（systemd / supervisor）での監視方法を検討してください。

---

この README はリポジトリ内のソースから抜粋して要点をまとめたものです。運用に入れる前に環境変数・権限・APIキー・DBのバックアップ等を十分に確認してください。必要があれば README を拡張してデプロイ手順や運用手順、テスト方法を追加できます。