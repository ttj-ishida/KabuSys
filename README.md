# KabuSys

日本株向け自動売買システムの軽量実装。ポートフォリオ構築、注文管理、監視、Paper Trading 検証、ニュース NLP / レジーム判定などの主要コンポーネントを含みます。

---

## 概要

KabuSys は以下の責務を分離して実装したモジュール群です。

- strategy / portfolio: 銘柄選定、重み付け、ポジションサイズ計算、リスク調整
- execution: ブローカークライアントを通じた注文発行・状態管理・リコンシリエーション
- monitoring: システム・注文・リスク監視、LINE 通知、監視 DB（SQLite）
- research: DuckDB を用いたファクター計算・特徴量解析ツール
- ai: ニュース NLP による銘柄センチメント、マクロニュースを用いた市場レジーム判定
- tools: Paper Trading 検証レポート生成などのユーティリティスクリプト
- utils: プロセス優先度・CPU affinity 設定など

設計方針の特徴:

- DB（監視用、Paper Trading 用）はファイルベースの SQLite（デフォルト）と DuckDB を併用
- .env / 環境変数で設定を管理（自動読み込み機能あり。無効化可能）
- Paper Trading 環境は本番 DB と完全分離
- OpenAI を用いた NLP 処理はフェイルセーフ設計（API 失敗時はスキップ or 0 にフォールバック）
- 監視は監視ループ（polling）で継続実行

---

## 主な機能一覧

- SystemMonitor: CPU / メモリ / ディスク使用率、Execution プロセスの生存確認、データ鮮度チェック
- TradeMonitor: 注文滞留（stale order）・約定価格の異常検知
- RiskMonitor: ドローダウン、ポジション数上限監視、ダッシュボード永続化
- KillSwitch: 監視により停止条件を満たした場合、data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送出
- AlertManager: LINE Messaging API を利用した通知（クールダウン管理あり）
- ExecutionEngine 周辺: Broker クライアント（Paper / Live 切替）、OrderManager、Reconciler（起動時リコンシリエーション）
- portfolio モジュール: 候補選定、重み算出、単元ロット丸めを伴うポジションサイズ計算、セクター制限、レジーム乗数
- research モジュール: Momentum / Volatility / Value 等のファクター計算、IC（Information Coefficient）計算など
- ai モジュール: ニュースのセンチメントスコアリング（OpenAI 使用）、日次レジーム判定
- tools.paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）

---

## セットアップ手順

前提: Python 3.10+（型ヒントに | 演算子を用いているため）

1. リポジトリをクローンしてプロジェクトルートへ移動
   - 仮にプロジェクトルートに `src/` があり、パッケージは `kabusys` という構成を想定しています。

2. 仮想環境を作成・有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール（プロジェクトに requirements.txt がない場合は下記をインストール）
   - pip install duckdb psutil requests openai streamlit
   - 必要に応じて他ライブラリを追加（例: pytest など）

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` を用意するか、OS 環境変数で設定します。
   - よく使うキー（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60
     - LOG_LEVEL=INFO
   - 自動読み込みの無効化（テスト等）: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

注: Settings クラスは自動で .env / .env.local をプロジェクトルートから読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。プロジェクトルートは .git または pyproject.toml を基準に探索します。

---

## 使い方

以下は代表的な実行方法（プロジェクトルートから実行）です。

1. 監視ループを起動（Monitoring）
   - Python モジュールとして:
     - python -m kabusys.run_monitoring
   - もしくはスクリプトを直接:
     - python src/kabusys/run_monitoring.py
   - 補足:
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
     - 監視は常に（KABUSYS_ENV に関係なく）本番用 sqlite_path を使用して監視ログを残します。
     - 停止方法: プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。

2. Execution エンジンを起動（注文実行部分）
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、モックブローカーを使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
     - 実行時は data/execution.pid に PID を書き、data/stop_requested.flag を置くことで外部から停止できます。
     - Execution の起動前に data/kill.flag が存在する場合は起動しません（KillSwitch により停止指示が出ていたため）。

3. Streamlit ダッシュボード（監視用）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - モニタリング DB を読み取り専用で開き、ダッシュボードを表示します。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH を指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を設定します。

5. AI 機能（ニューススコア / レジーム判定）
   - ニューススコア:
     - kabusys.ai.score_news をプログラムから呼び出し。DuckDB 接続と target_date、OpenAI API キーが必要。
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime を呼び出し。DuckDB 接続と target_date、OpenAI API キーが必要。
   - 補足:
     - API キーは引数で渡すことも、環境変数 OPENAI_API_KEY を利用することも可能。
     - API 失敗時はフェイルセーフ（スコア 0.0 等）で継続します。

6. 停止フラグ / キルフラグの扱い
   - data/stop_requested.flag
     - run_monitoring / run_execution がこのファイルの存在を検知すると自身を終了または停止します（外部からの優雅なシャットダウン指示）。
   - data/kill.flag
     - KillSwitch が条件を満たした場合に生成され、ExecutionEngine に対して停止指示を送るために使用します（KillSwitch.clear() で消去可能）。

---

## 設定（Settings）について

- 設定は環境変数を通して提供されます。Settings クラス（kabusys.config）で各値を取得します。
- .env / .env.local は自動的に読み込まれます（プロジェクトルートが検出できる場合）。OS 環境変数より優先度は低く、.env.local は .env の上書き用に読み込まれます。
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須のキー（未設定だと起動時に例外）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - （OpenAI を利用する機能を使う場合）OPENAI_API_KEY

---

## ディレクトリ構成

以下は `src/kabusys` の主要ファイルと役割（抜粋）です。

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / .env 読み込みと Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算、ロット丸め、aggregate cap
    - risk_adjustment.py — セクター上限、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py — raw_news を OpenAI で評価して ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA でレジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成 / CRUD（init_monitoring_db / MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留 / 価格異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるループ（run/run_once）
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
    - __init__.py
  - execution/
    - order_manager.py — Order State Machine 外向き API
    - reconciler.py — 起動復旧・照合ロジック
    - order_repository.py — Orders DB アクセス（参照される）
    - (その他 broker_factory, execution_engine 等)
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py
  - monitoring/monitoring_db.py — 監視用テーブル群の定義、マイグレーション処理

- data/ (実行時に使用されることが多い)
  - monitoring.db (SQLite、デフォルト)
  - paper_trading.db (Paper Trading 専用 SQLite)
  - kabusys.duckdb (DuckDB 用の DB ファイル)
  - execution.pid, stop_requested.flag, kill.flag, など

---

## 運用上の注意 / ヒント

- Paper Trading と Live を混同しないでください。KABUSYS_ENV=paper_trading を設定すると Execution は Paper DB に記録します（本番 DB は汚れません）。
- OpenAI 利用機能は API キーと通信環境が必要です。レート制限や一時的な失敗に耐えるよう実装されていますが、実運用では API 料金に注意してください。
- LINE 通知を有効にするには LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定してください。未設定時は通知はスキップされ、ログのみ出力されます。
- モニタリングは監視 DB（SQLite）へ記録します。初回起動時にスキーマ作成処理 init_monitoring_db が自動的に実行されます。
- 停止・再起動時の復旧：Reconciler は OrderSent 等の不整合を検出して可能な限り同期しますが、手動確認が必要なケースもあるためログを確認してください。
- プロセス優先度変更は psutil を使用します。root/管理者権限が必要な場合や OS によっては変更に失敗することがあります（警告ログが出ますが処理は継続します）。

---

## よく使うコマンドまとめ

- 仮想環境作成 / 有効化（一例）
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール
  - pip install duckdb psutil requests openai streamlit

- 監視起動
  - python -m kabusys.run_monitoring

- Execution 起動
  - python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含める環境変数のサンプル .env.example、起動スクリプトのユニットテスト手順、もしくは各モジュールの詳細な API ドキュメント（関数一覧・引数説明）を追加で生成します。どちらが必要か教えてください。