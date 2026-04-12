# KabuSys — README

これは日本株自動売買システムのコードベース（部分）です。本リポジトリは取引実行・監視・リサーチ・ポートフォリオ構築・AI ベースのニュース分析などのコンポーネントを含みます。以下は開発者向けの概要、セットアップ、使い方、ディレクトリ構成の説明です。

重要: 本 README はソースコード（src/kabusys）に基づいて作成しています。実運用前に十分なレビュー・テストを行ってください。

概要
- プロジェクト名: KabuSys
- 目的: 日本株の自動売買に必要な実行エンジン、監視、ポートフォリオ構築、リサーチ、AIニューススコアリング等を提供するモジュール群。
- 設計思想:
  - モジュールはテストしやすい純粋関数と副作用を持つインフラ層に分離。
  - 本番／ペーパー（検証）環境を環境変数で切り替え可能。
  - DuckDB / SQLite を利用したデータ保存と高速分析。
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントやレジーム判定を統合（API キー必須）。

主な機能一覧
- 実行（Execution）
  - 起動スクリプト: run_execution.py
  - Broker クライアント抽象化 / OrderManager / RiskManager / Reconciler による発注・状態管理・再同期
  - paper_trading モード（完全に分離された SQLite DB へ記録）
- 監視（Monitoring）
  - 起動スクリプト: run_monitoring.py
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン / ポジション上限監視とリスクログ
  - KillSwitch: 条件に応じた停止フラグファイル出力
  - AlertManager: LINE Push による一方向アラート送信
  - streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み算出（等金額／スコア加重）、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ（Research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - DuckDB を用いた高速集計
- AI（ai）
  - news_nlp: ニュース記事をまとめて OpenAI に投げセンチメント（ai_scores）を生成・保存
  - regime_detector: MA200 とマクロニュースの LLM 判定を合成して市場レジームを算出・保存
- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等）
- ユーティリティ
  - process_priority: プロセス優先度（nice / Windows priority）や CPU affinity 設定ユーティリティ
  - 設定管理（config.py）: 環境変数 / .env 自動ロード機能

セットアップ手順（開発 / 検証用）
前提: Python 3.10 以上（ソースで | 型や match を使っているため Python 3.10+ を推奨）

1. リポジトリをクローンして、作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   最低限必要なパッケージ（例）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit (ダッシュボード利用時)
   例:
   - pip install duckdb psutil openai requests streamlit

   （実プロジェクトでは requirements.txt を用意して pip install -r で管理してください）

4. 環境変数設定
   プロジェクトは .env / .env.local を自動でプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。主な環境変数:

   必須（実行する機能による）:
   - JQUANTS_REFRESH_TOKEN — （必要に応じて）
   - KABU_API_PASSWORD — kabuステーション API 用
   - OPENAI_API_KEY — AI 機能（news_nlp, regime_detector）利用時に必須

   オプション:
   - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - paper_trading: run_execution は paper_db（PAPER_TRADING_SQLITE_PATH）を使用
   - PAPER_FILL_MODE — instant|partial|never|reject（paper_trading の約定挙動）
   - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（デフォルト）
   - DUCKDB_PATH — data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH — data/monitoring.db（デフォルト）
   - PID_FILE_PATH — data/execution.pid（デフォルト）
   - KILL_FLAG_PATH — data/kill.flag（デフォルト）
   - MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、run_monitoring で使用。デフォルト 60）
   - LOG_LEVEL — DEBUG/INFO/…（Settings.log_level でも制御）

   例 .env（簡易）
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリ作成
   - mkdir -p data

基本的な使い方（コマンド例）
- 監視ループの起動（SystemMonitor 単体起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）起動
  - 本番モード:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパー検証モード（完全に分離された DB へ記録）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - PAPER_TRADING_SQLITE_PATH を指定すれば別ファイルに書き出せます

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既に監視 DB が存在しないと read-only 接続に失敗します。その場合は先に run_monitoring を起動してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI / レジーム判定（プログラムから呼ぶ例）
  - 以下は Python REPL などから呼べます（DuckDB に価格・raw_news 等のテーブルが必要）
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026,4,1), api_key="sk-...")

注意点
- OpenAI API を使用する機能は api_key が必須です。失敗時はフェイルセーフとしてスコア 0.0 を扱う実装の部分もありますが、完全なスコアリングやレジーム算出にはキーを設定してください。
- run_monitoring では Settings による自動 .env 読み込みを行います。テスト環境で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードは本番 DB と完全に分離する設計になっています（PAPER_TRADING_SQLITE_PATH を使用）。
- Process 優先度設定（set_process_priority）を起動直後に行います。権限不足等の場合は警告が出ますが処理は継続します。
- kill.flag を書くことで ExecutionEngine に対する停止シグナルを送出します（KillSwitch により管理）。

ディレクトリ構成（主なファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に保存
    - regime_detector.py — ma200 とマクロニュースを合成して市場レジーム算出
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 滞留注文・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — flag ファイルによる停止制御
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - reconciler.py — 起動時の注文・ポジション再同期
    - order_manager.py — Order 状態管理および broker とのやり取り
    - （他の execution 関連モジュールは省略／存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 株数算出・単元丸め・キャップ処理
  - research/
    - factor_research.py — momentum/value/volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計集計
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・拡張のヒント
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news 等）が整備されていることが前提です。リサーチ・AI モジュールはこれらのテーブルに依存します。
- AI 呼び出しはネットワーク障害やレート制限に対して指数バックオフでのリトライ実装がありますが、実運用では API レートやコストに注意してください。
- MonitoringDB はマイグレーション（列追加）ロジックを一部含むため、既存 DB と互換性を保つための挙動を理解してください（例: trade_logs.latency_ms の追加など）。
- テスト時は OpenAI 呼び出しをモック（unittest.mock.patch）すると簡単に単体テストが可能です。news_nlp._call_openai_api や regime_detector._call_openai_api を差し替えることを想定しています。

ライセンス・注意
- この README はサンプルコード解析に基づくものであり、本リポジトリに元々付属するライセンス情報を参照してください。
- 金融アルゴリズム・自動売買の運用はリスクを伴います。自己責任で行ってください。

問題があれば具体的な実行手順（OS、Python バージョン、発生したエラーメッセージ）を教えてください。追加で起動スクリプト用の systemd ユニット例や docker 化手順なども作成できます。