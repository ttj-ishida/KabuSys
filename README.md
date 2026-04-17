# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした小規模フレームワークです。本リポジトリは以下の主要機能を含みます：

- 注文発行・状態管理（ExecutionEngine 周辺）
- 監視（監視ループ、アラート、ダッシュボード）
- ポートフォリオ構築（候補選定、重みづけ、ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 等）
- AI を用いたニュースセンチメント評価・レジーム判定（OpenAI を利用）
- Paper Trading 用の検証レポート作成ツール
- ユーティリティ（環境変数ロード、プロセス優先度設定 等）

以下、本プロジェクトの概要、セットアップ手順、使い方、ディレクトリ構成を示します。

---

## プロジェクト概要

KabuSys は以下の設計方針に基づいて構築されています。

- 「実行（Execution）」と「監視（Monitoring）」「リサーチ（Research）」を明確に分離
- DB は SQLite / DuckDB を利用（監視ログは SQLite、時系列データ等は DuckDB）
- Paper Trading（テスト）環境は本番 DB と完全に分離して実行可能
- AI（OpenAI）呼び出しはリトライ・検証を行い、失敗時はフェイルセーフ（ゼロやスキップ）で継続
- 外部サービス（kabu API, J-Quants, LINE, OpenAI 等）は環境変数で設定

---

## 主な機能一覧

- Execution
  - 注文の作成 / 同期 / キャンセル等を行う OrderManager、ExecutionEngine（セッション実行）
  - Reconciler による起動時の自動復旧（OrderSent の再照合、ポジション差分検出）
  - Paper Trading モードでは MockBroker を利用し、paper_trading 用 SQLite に記録

- Monitoring
  - SystemMonitor：CPU/MEM/Disk、Execution プロセスの生存確認、データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン、ポジション上限監視
  - KillSwitch：条件を満たしたら data/kill.flag を書き込み Execution を停止
  - AlertManager：LINE によるプッシュ通知（cooldown 管理）
  - Streamlit ダッシュボード（data/monitoring.db を読み取り表示）

- Portfolio
  - 候補選定（score / rank）、等金額・スコア加重の重み算出
  - セクターキャップ適用、レジーム乗数、ポジションサイズ算出（単元丸め、aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC、統計サマリー

- AI
  - news_nlp.score_news：ニュース記事を集約して OpenAI でセンチメント算出 → ai_scores へ書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースを組み合わせて市場レジーム判定（market_regime テーブルへ書込）

- Tools
  - paper_verification_report：Paper Trading DB を解析し、稼働率・注文成功率・レイテンシ等の検証レポートを出力

---

## セットアップ手順

要件（推奨）
- Python 3.10 以上（型注釈に `|` を使用しているため）
- SQLite（Python 標準ライブラリに同梱）
- 必要な Python パッケージ（以下の例を参照）

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   - pip install duckdb psutil requests streamlit openai

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を利用）

3. パッケージのインストール（開発）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置することで自動読み込みされます（既存の OS 環境変数を上書きしない）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨される主要な環境変数（.env 例）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development|paper_trading|live
- PAPER_FILL_MODE=instant|partial|never|reject
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- DUCKDB_PATH=data/kabusys.duckdb
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- LOG_LEVEL=INFO

注意:
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を用います（本番 DB と分離）。
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。

---

## 使い方（起動例）

プロジェクトルートを想定（src/ を PYTHONPATH に含む、あるいはパッケージを pip install -e .）

1. 監視ループ起動（Monitoring）
   - デフォルトでは monitoring は本番 sqlite_path を使用（KABUSYS_ENV に関わらず）
   - 環境変数でポーリング間隔を上書き可能： MONITOR_POLL_INTERVAL（秒、デフォルト 60）
   - 起動コマンド:
     - python -m kabusys.run_monitoring
   - 停止:
     - プロセスを Ctrl+C
     - あるいはプロジェクトルートの data/stop_requested.flag を作成するとポーリングループが検出して終了します

2. 実行エンジン起動（Execution）
   - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
   - 起動コマンド:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するか、実行中に kill.flag が書き込まれると停止処理が走ります

3. Streamlit ダッシュボード（監視 UI）
   - 起動コマンド:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、Positions/Orders/System/Overview を表示します

4. Paper Trading 検証レポート
   - 起動コマンド:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。--db オプションでパスを上書き可能。

5. AI 機能
   - OpenAI API キーを渡すか環境変数 OPENAI_API_KEY を設定
   - ニュースセンチメント:
     - kabusys.ai.score_news は DuckDB 接続と target_date を受け取り、ai_scores テーブルへ書き込む
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime を呼ぶと market_regime テーブルへ書き込み

運用時の注意:
- KillSwitch（data/kill.flag）は監視ロジックから書かれ、ExecutionEngine に停止シグナルを与えます。必要に応じて起動前に clear（削除）してください。Settings.kill_flag_clear_on_start を 1 にすると起動時に自動でクリアする設定があります。
- PID ファイル: Settings.pid_file_path（デフォルト data/execution.pid）を ExecutionEngine が利用します。stale PID を SystemMonitor が検出すると削除してアラートを出します。

---

## 主要ファイルと説明（抜粋）

- src/kabusys/run_monitoring.py
  - SystemMonitor を使ったポーリングループ。MONITOR_POLL_INTERVAL による間隔指定可能。

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading の場合は専用 DB を使う。

- src/kabusys/config.py
  - 環境変数の読み込み・管理。プロジェクトルートの .env / .env.local を自動ロードする（デフォルト）。

- src/kabusys/monitoring/
  - monitoring_db.py: monitoring 用 SQLite スキーマ初期化 / 永続化ロジック
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常検出
  - risk_monitor.py: ドローダウン / ポジション数監視
  - kill_switch.py: kill.flag による停止シグナル管理
  - alert_manager.py: LINE Push による通知
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: 監視ダッシュボード

- src/kabusys/execution/
  - order_manager.py, reconciler.py 等：注文管理、復旧、Engine 実行に関連するロジック

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py：候補選定・配分・リスク調整ロジック

- src/kabusys/research/
  - factor_research.py, feature_exploration.py：ファクター計算、IC、統計量

- src/kabusys/ai/
  - news_nlp.py: ニュースセンチメント算出（OpenAI 使用）
  - regime_detector.py: ETF MA + マクロニュースでレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py：Paper Trading DB を元に検証レポートを生成

- src/kabusys/utils/
  - process_priority.py：プロセス優先度・CPU affinity 設定

---

## ディレクトリ構成（概略）

src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py
- tools/
  - __init__.py
  - paper_verification_report.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...（その他実行関連モジュール）
- monitoring/
  - __init__.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- utils/
  - process_priority.py
  - __init__.py
- data/ (runtime に生成される想定)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 運用・トラブルシューティングのヒント

- MONITOR_POLL_INTERVAL は環境変数で秒数を指定できます。不正な値を与えるとデフォルト 60 秒にフォールバックします。
- Paper Trading モードでは実際のブローカーに注文を sent しないため、本番とは挙動が異なる点に注意してください（PAPER_FILL_MODE 等で約定挙動を制御）。
- OpenAI を使う処理はレート制限やタイムアウトに対してリトライ実装がありますが、API キーが無い場合は例外を投げる箇所があります（事前に OPENAI_API_KEY を設定してください）。
- 監視処理は monitoring DB（SQLite）にログを記録します。DB スキーマは monitoring_db.init_monitoring_db で冪等に初期化されます。
- kill.flag があると ExecutionEngine は安全に停止します。運用時は kill.flag の管理（意図的な書き込み、クリアの手順）を運用ルールとして定めてください。

---

必要に応じて README を拡張して、セットアップスクリプト、CI、テストコマンド、詳細な設定例（.env.example）などを追加してください。質問や特定の使い方（たとえば ExecutionEngine の設定変更方法や DuckDB のデータ投入方法）について詳しく知りたい場合は教えてください。