KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株自動売買のための内部ライブラリ群と起動スクリプトを備えたプロジェクトです。
主な目的は、戦略の実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター / リサーチ、ニュース NLP によるセンチメント評価などを組み合わせた
運用ワークフローを提供することです。ローカル SQLite / DuckDB をデータ永続化に用い、OpenAI や外部 API（J-Quants / kabuステーション 等）と連携するモジュールを含みます。

特徴（機能一覧）
---------------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカーファクトリ（本番 / paper_trading に応じた Mock ブローカー切替）
  - OrderManager / OrderRepository / Reconciler による発注管理・再同期処理
  - リスク管理（RiskManager）によるポジション・利用率の制約
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor：滞留注文や約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクログ
  - KillSwitch：閾値到達時に停止フラグ（data/kill.flag）を書き込む仕組み
  - AlertManager：LINE によるアラート送信（オプション）
  - Streamlit ダッシュボード（読み取り専用）による監視情報可視化
- Portfolio
  - 候補選定、等重配分 / スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
  - 純粋関数設計（副作用なし、DB参照なし）
- Research / Features
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB を用いた高速クエリ処理
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントスコアリング
  - market_regime 判定（ETF MA200 とマクロセンチメントの合成）
  - API エラー時のリトライ・フォールバックロジック
- ユーティリティ
  - 環境変数読み込み（.env / .env.local 自動ロード、必要キーチェック）
  - プロセス優先度・CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）

動作環境・依存
---------------
- 推奨 Python バージョン: 3.10+
  - （コード中で | 型アノテーション等の構文を使用）
- 主な依存パッケージ（requirements.txt がある場合はそちらを参照してください）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite と DuckDB をデータストアとして使用

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限:
     pip install duckdb psutil requests openai

   - Streamlit ダッシュボードを使う場合:
     pip install streamlit

4. 環境変数の設定 (.env)
   - プロジェクトルートに .env / .env.local を置くことで自動ロードされます（既存 OS 環境変数が優先）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）

   - .env の自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要コマンド）
---------------------

1. ExecutionEngine を起動（本番または paper_trading）
   - 実行:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB を使用します（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在する場合は起動を止めます。
     - 実行中に data/stop_requested.flag が作成されると安全に停止します。
     - プロセス PID は data/execution.pid（デフォルト）に出力されます。

2. Monitoring を起動（SystemMonitor のポーリング）
   - 実行:
     - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒、デフォルト 60）
     - 監視は環境にかかわらず本番 sqlite_path を使用してログを記録します（monitoring 側は本番 DB を参照）
     - 停止は data/stop_requested.flag によって行えます

3. Streamlit ダッシュボード（監視画面）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 読み取り専用で SQLite DB を開き監視情報を可視化します

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - オプション:
       --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
   - 説明:
     - 指定期間の system_status / trade_logs / risk_logs を集計し PASS/FAIL 判定を出力します

5. AI 機能（ニュース NLP / レジーム）
   - OpenAI API キー（OPENAI_API_KEY）が必要です
   - ai.score_news や ai.regime_detector.score_regime を呼び出して DuckDB 上のテーブルに結果を書き込みます
   - API のレート制限や一時エラーに対するリトライ・フォールバック実装あり

停止・フラグ操作
-----------------
- 実行中プロセスを安全に停止させたい場合:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring はそれを検出して停止します
- KillSwitch（自動停止）:
  - RiskMonitor 等が閾値を越えた場合 data/kill.flag が書き込まれます（ExecutionEngine の起動時にそれが存在すると起動を防ぐなど）
  - 手動クリアはファイルを削除してください: rm data/kill.flag

設定の挙動に関する補足
---------------------
- 設定管理
  - kabusys.config.Settings で環境変数を一元的に扱います
  - Settings.env により is_dev / is_paper / is_live を判定します
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動的に読み込まれます
- DB 初期化
  - monitoring 側は init_monitoring_db(sqlite_conn) を用いて必要テーブルを冪等に作成します
- プロセス優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼んでプロセス優先度を上げようとします（psutil を使用。権限がない場合は警告ログでスキップ）

ディレクトリ構成（抜粋）
-----------------------
以下は主要ファイル / モジュールのツリー（src/kabusys 配下を中心に抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - order_record.py
      - ...（発注関連の実装）
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/  (実行時に利用／作成されることが多い)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kabusys.duckdb
      - stop_requested.flag, kill.flag 等

例: 簡単な運用フロー
--------------------
1. .env を用意して必要な API キーやパスを設定
2. DuckDB / SQLite ファイルがなければ、まず Execution を一度起動して DB スキーマを作らせる（ExecutionEngine / Monitoring の init が適宜実行されます）
3. 常時運用: run_execution を daemon 化（systemd 等）して実行、別プロセスで run_monitoring を動かす
4. 監視・アラート: monitoring のアラートを LINE へ通知する設定を行う（LINE_TOKEN / USER_ID）
5. 定期的に tools/paper_verification_report を実行して paper_trading の検証を行う

注意事項・設計上のポイント
-------------------------
- paper_trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）
- 監視（monitoring）は「環境にかかわらず」本番の sqlite_path を参照してログを残す実装箇所があるため、運用時は環境設定に注意してください（run_monitoring の docstring 参照）
- OpenAI / 外部 API 呼び出しはリトライやフォールバックを備えていますが、API キー管理/使用量には注意してください
- 本 README はコードベースの抜粋に基づく概要説明です。詳細は各モジュールの docstring / 実装を参照してください。

よく使うコマンドまとめ
---------------------
- Execution 起動:
  python -m kabusys.run_execution
- Monitoring 起動:
  python -m kabusys.run_monitoring
- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

問い合わせ / 貢献
-----------------
- バグ報告や機能改善提案は Issue を立ててください。
- コード変更の際はユニットテスト（未同梱の可能性あり）と動作確認をお願いします。

以上。README の補足や具体的な .env.example、requirements.txt の生成などをご希望であれば追加で作成します。