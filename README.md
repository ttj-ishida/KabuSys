KabuSys — README
本リポジトリは「KabuSys：日本株自動売買システム」の一部主要モジュール群を収めています。
以下はこのコードベースの概要、機能、セットアップ / 実行方法、ディレクトリ構成の説明です。

プロジェクト概要
- KabuSys は日本株の自動売買に関するコンポーネント群（実行エンジン、監視、ポートフォリオ構築、ファクター計算、AI によるニュース解析など）を提供します。
- 設定は環境変数および .env / .env.local で管理され、Settings クラスを通じて参照されます。
- 実行要素（ExecutionEngine）と監視要素（MonitoringEngine）は分離され、Paper Trading モード（KABUSYS_ENV=paper_trading）では本番 DB と分離して動作します。

主な機能一覧
- 実行（Execution）
  - ブローカー抽象化（BrokerClientFactory）を経由して注文を送信・管理
  - OrderManager / OrderRepository による注文状態管理、Reconciler による再起動後の突合せ
  - リスク管理（RiskManager）や注文レポジトリ連携（order_repository.py は本 README 内では省略）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留、約定異常価格検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視
  - KillSwitch: 条件に応じてフラグファイルを書いて実行エンジン停止を指示
  - AlertManager: LINE Messaging API による通知（トークンが未設定ならログのみ）
  - streamlit を使った監視ダッシュボード（streamlit run で起動）
- ポートフォリオ構築（portfolio）
  - 候補選定、等重・スコア重み、セクター上限の適用、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン順位相関）や統計サマリー
- AI（ai）
  - news_nlp: OpenAI を使ったニュースのセンチメント集約 → ai_scores テーブルへ書込
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースを LLM で評価して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを出力

セットアップ手順（開発環境向け）
1. 必要ツール（例）
   - Python 3.10+
   - pipenv / venv 等で仮想環境を準備

2. 依存パッケージ（代表例）
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb psutil openai requests streamlit

   ※実際の requirements.txt / pyproject.toml があればそちらを利用してください。

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動読み込みされます（既存の OS 環境変数は上書きされません。 .env.local は上書き可能）。
   - 自動ロードを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - SQLITE_PATH: 監視 DB path（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB path（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 sqlite path（デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY: OpenAI を使う機能で必須
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用（未設定なら送信しない）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアする（"1" で有効）
   - Settings クラスは値の妥当性チェックを行います（例: PAPER_FILL_MODE の有効値など）。

セットアップ補足
- DB 初期化: 実行スクリプトは起動時に monitoring DB のテーブルを冪等に作成します（init_monitoring_db）。
- Paper Trading: KABUSYS_ENV=paper_trading の場合、run_execution は paper 用 sqlite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離された動作を行います。

使い方（主要スクリプト）
- 監視ループを起動
  - デフォルト（ポーリング 60 秒）:
      python -m kabusys.run_monitoring
  - 例（間隔 30 秒に上書き）:
      export MONITOR_POLL_INTERVAL=30
      python -m kabusys.run_monitoring
  - run_monitoring は Settings に従って monitoring DB（sqlite）と DuckDB に接続し、SystemMonitor のループを継続実行します。
  - 起動直後に set_process_priority("high") を試みます（環境により失敗しても継続）。

- 実行エンジンを起動
  - 本番 / 開発（デフォルト KABUSYS_ENV=development）:
      python -m kabusys.run_execution
  - Paper Trading:
      export KABUSYS_ENV=paper_trading
      python -m kabusys.run_execution
  - run_execution は BrokerClientFactory 経由でブローカーを生成し、ExecutionEngine を起動してセッション実行します。Paper Trading モードでは MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH に記録されます。

- Paper Trading 検証レポート生成
  - コマンド:
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
      --from YYYY-MM-DD
      --to   YYYY-MM-DD
      --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等を標準出力に表示

- streamlit ダッシュボード（監視）
  - 起動:
      streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で monitoring DB を開き、Overview / Positions / Orders / System を表示します。

- AI 機能（news_nlp / regime_detector）
  - 必要: OPENAI_API_KEY を環境変数に設定
  - news_nlp.score_news(conn, target_date, api_key=None) / regime_detector.score_regime(conn, target_date, api_key=None) としてプログラム的に呼べます（コマンドラインエントリは提供されていません）。
  - OpenAI API エラーはリトライ処理を行い、最終的に失敗してもフェイルセーフ（スコア 0 やスキップ）で進みます。

注意事項 / 運用メモ
- 自動ロード: config モジュールはプロジェクトルートの .env / .env.local を自動読み込みします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- kill.flag: KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に文字列を書き込み ExecutionEngine へ停止シグナルを送ります。ExecutionEngine 側でこれを監視して停止動作とする設計です。
- PID 管理: run_execution や monitor は pid_file を用いる箇所があります（Settings.pid_file_path デフォルト data/execution.pid）。SystemMonitor は PID の stale 検出と削除を行います。
- DB マイグレーション: init_monitoring_db は冪等でテーブルを作成し、既存 DB に欠けているカラム（例: latency_ms, peak_value）があれば ALTER TABLE で追加します。
- プロセス優先度や CPU affinity の設定は環境に依存します。psutil による設定で権限不足等の場合は警告が出てスキップされます。

主要ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / .env ロードと Settings
    - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py       — ExecutionEngine 起動スクリプト
    - ai/
      - news_nlp.py          — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py   — 市場レジーム判定（MA + LLM）
      - __init__.py
    - monitoring/
      - monitoring_db.py     — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py    — CPU/メモリ/プロセス/データ鮮度監視
      - trade_monitor.py     — 注文滞留・約定異常検出
      - risk_monitor.py      — ドローダウン / ポジション上限監視
      - kill_switch.py       — フラグファイルによる停止シグナル
      - alert_manager.py     — LINE 通知
      - monitoring_engine.py — 各 Monitor を束ねるエンジン
      - streamlit_dashboard.py — Streamlit ダッシュボード
      - __init__.py
    - portfolio/
      - portfolio_builder.py — 候補選別・重み計算
      - position_sizing.py   — 株数計算・上限・丸め
      - risk_adjustment.py   — セクターキャップ・レジーム乗数
      - __init__.py
    - research/
      - factor_research.py   — ファクター計算（momentum, volatility, value）
      - feature_exploration.py — 将来リターン、IC、統計サマリー
      - __init__.py
    - execution/
      - reconciler.py        — 再起動時の注文・ポジション突合せ
      - order_manager.py     — 注文ステートマシン外向け API
      - (他: broker_factory, execution_engine, order_repository など — 一部省略)
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート
      - __init__.py
    - utils/
      - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py
    - data/ (想定)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb

開発者向けヒント
- テスト: 各モジュールは外部依存（OpenAI, ブローカー API, DB）を注入可能な設計になっているため、ユニットテストではモックが容易です（例: news_nlp._call_openai_api の差し替え）。
- ロギング: logging.basicConfig(level=logging.INFO) が各起動スクリプトで呼ばれます。LOG_LEVEL 環境変数は Settings.log_level で取得できます。
- Safety-first: AI 呼び出しやブローカー操作はリトライ・サニタイズ・フェイルセーフを多く実装しており、部分失敗時のデータ保護（部分書込で既存データを破壊しない等）に配慮されています。

問い合わせ / 貢献
- コードの理解や拡張、バグ修正は歓迎します。プルリクエストを送る際はテスト・静的解析を併せて添えてください。
- 設定例（.env.example）がある場合は参照して必要な環境変数を準備してください。

以上。必要であれば README を英語版に翻訳したり、実行フロー図や設定テンプレート (.env.example) を追加で作成できます。どの情報を追加したいか教えてください。