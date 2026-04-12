# KabuSys — README

本ドキュメントは提供されたコードベース（src/kabusys 以下）に対する README です。日本株自動売買システムのコアモジュール（監視、発注、ポートフォリオ構築、リサーチ、AI 補助など）を収録しています。

---
## プロジェクト概要
KabuSys は日本株向けの自動売買・監視基盤の一部実装です。主な責務は次のとおりです。

- ExecutionEngine：ブローカー経由の発注・注文管理・リコンシリエーション
- Monitoring：プロセス監視・データ鮮度・注文滞留・リスク監視・アラート送出
- Portfolio：銘柄選定、重み付け、ポジションサイジング、セクター制限等の純粋関数
- Research：DuckDB 上の価格・財務データからファクター・統計量・将来リターン等を計算
- AI モジュール：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ツール：Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード等

設計上、監視ログは SQLite（data/monitoring.db）、分析用は DuckDB（data/kabusys.duckdb）、Paper Trading は独立した SQLite（data/paper_trading.db）に分離して扱います。

---
## 主な機能一覧
- システム監視（CPU/メモリ/ディスク、実行プロセス生存、データ鮮度）
- 注文監視（滞留注文、約定価格の異常検出）
- リスク監視（ドローダウン、保有銘柄数上限）
- Kill Switch：条件に応じてフラグファイルを書き、Execution を停止させる仕組み
- LINE へアラート送信（AlertManager）
- Execution 起動スクリプト（実運用 / Paper Trading 切替対応）
- リコンシリエーション（再起動後の注文同期、ポジション差分検出）
- Portfolio 構築（候補選定、等金額/スコア加重、リスクベースの株数決定）
- Research（モメンタム、ボラティリティ、バリュー等のファクター計算、IC 計算）
- AI（ニュースセンチメントの LLM スコアリング、レジーム判定）
- Streamlit ダッシュボード（監視データの可視化）
- Paper Trading 検証レポート生成スクリプト

---
## セットアップ手順

前提
- Python 3.10+（型ヒントに種類 union (|) を使用）
- Git 等でプロジェクトルートに移動して作業することを推奨

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   （requirements.txt がない場合は最低限以下をインストール）
   - pip install duckdb psutil openai requests streamlit

   プロジェクトに requirements.txt があれば:
   - pip install -r requirements.txt

3. 環境変数の設定
   プロジェクトルートの `.env` / `.env.local` を使えます（自動読み込みあり）。
   自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN        （必須：J-Quants API 用）
   - KABU_API_PASSWORD            （必須：kabuステーション API 用）
   - OPENAI_API_KEY               （AI 機能を使う場合）
   - KABUSYS_ENV                  値: development | paper_trading | live（デフォルト: development）
   - SQLITE_PATH                  監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH                  分析 DB（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH    Paper Trading 用 DB（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE              paper_trading 時の約定モード（instant | partial | never | reject）
   - PID_FILE_PATH                Execution の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH               Kill フラグファイル（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL        run_monitoring のポーリング間隔（秒。デフォルト 60）

   例（UNIX shell）:
   ```
   export KABUSYS_ENV=paper_trading
   export OPENAI_API_KEY=sk-xxxx
   export KABU_API_PASSWORD=your_password
   ```

4. データフォルダ作成
   デフォルトの DB 保存先（data/）を作成しておくとよいです。
   - mkdir -p data

---
## 使い方

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30

  注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は常に本番 DB を見る想定）。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - Paper Trading の約定挙動は PAPER_FILL_MODE で制御できます（instant/partial/never/reject）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュール（プログラムから呼ぶ例）
  - from kabusys.ai import score_news
    - score_news(conn, target_date) — DuckDB 接続と日付を渡す。OPENAI_API_KEY を環境変数か引数で指定可能。

- ライブラリとしての利用
  - portfolio、research、monitoring の純粋関数やクラスはアプリケーションコードからインポートして再利用可能です。
  - 例:
    - from kabusys.portfolio import select_candidates, calc_score_weights
    - from kabusys.research import calc_momentum, calc_volatility

---
## 重要な挙動・運用メモ
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` → `.env.local` を読み込みます。OS 環境変数は保護されます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると run_execution が MockBroker を使い、paper_trading.db に記録します（本番 DB と完全分離）。

- Kill Switch:
  - RiskMonitor が閾値超過などを検知した場合、KillSwitch が `KILL_FLAG_PATH`（デフォルト data/kill.flag）に理由を記述して書き込みます。ExecutionEngine 起動時にこのフラグを見て停止します。起動時にフラグを消す設定もあります（Settings.kill_flag_clear_on_start）。

- プロセス優先度:
  - run_monitoring / run_execution は起動直後に `set_process_priority("high")` を呼びます。OS による制約で失敗することがあり、失敗時は警告ログに留まります。

- DB マイグレーション:
  - init_monitoring_db(conn) は冪等でテーブルを作成し、既存 DB に対する簡単なカラム追加（例: latency_ms, peak_value）を行います。

---
## ディレクトリ構成（抜粋）
以下は主要なファイル・モジュールの概観です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py (参照される)
    - reconciler.py
    - execution_engine.py (参照される)
    - broker_factory.py (参照される)
    - broker_api.py (参照される)
    - order_record.py (参照される)
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
  - tools/
    - __init__.py
    - paper_verification_report.py

※ 一部参照されるファイル（例: execution_engine.py、order_repository.py、data モジュールなど）はこの抜粋に含まれていない場合があります。実行時にはそれらの実装が必要です。

---
## トラブルシューティング（よくある問題）
- DuckDB / SQLite 接続エラー:
  - ファイルパスの権限・存在を確認してください。Streamlit で読み取り専用で開く場合は URI に `?mode=ro` を付けています。
- OpenAI 関連の問題:
  - OPENAI_API_KEY の設定を確認。API エラーは LLM 呼び出し側でリトライを行いますが、キー未設定時は例外になります。
- psutil アクセス拒否:
  - プロセス優先度設定や CPU affinity は管理者権限が必要な場合があります。警告ログが出ますが、処理は続行されます。
- .env 読み込みが期待通りに動かない:
  - プロジェクトルートの特定に .git または pyproject.toml を使用しています。該当ファイルがなければ自動ロードをスキップします。

---
## 参照例（コマンドまとめ）
- 監視を起動:
  - MONITOR_POLL_INTERVAL を 30 秒にする例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
- Execution 起動（Paper Trading モード）:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---
必要に応じて README の補足（環境変数の詳細説明、依存関係の固定バージョン、CI/デプロイ手順など）を作成します。どの部分を詳しく記載したいか教えてください。