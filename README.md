# KabuSys

日本株向けの自動売買 / 研究 / 監視フレームワークの一部です。本リポジトリは戦略構築、発注実行、監視、検証、研究用ユーティリティ（ファクター計算・特徴探索・ニュースNLP 等）を含みます。

主に以下の目的で使われます：
- 日次・リアルタイムのシグナルに基づく発注実行（ExecutionEngine）
- 実行プロセス・注文状態・リスクの監視（Monitoring）
- Paper Trading 環境での検証・レポート生成
- DuckDB を使ったファクター計算・研究処理
- OpenAI を使ったニュースセンチメント評価・レジーム判定（AI モジュール）

対応 Python バージョン: 3.10 以上（型注釈で | を使用しているため）

---

## 機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化／MockBroker による Paper Trading 分離
  - 注文管理（OrderManager）、再同期待機（Reconciler）
  - リスク管理（RiskManager）設定

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルによる ExecutionEngine 停止トリガ
  - AlertManager: LINE Push による一方向通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 UI）
  - 監視ログの永続化（SQLite）

- Portfolio / Position sizing
  - 候補選定、等配分／スコア加重配分、リスク調整（セクター制限／レジーム乗数）
  - 株数決定（lot 単位丸め、aggregate cap、利用可能現金に基づくスケーリング）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、特徴量サマリ

- AI
  - ニュースのセンチメント解析（OpenAI）
  - 市場レジーム判定（ETF MA200 + マクロニュースセンチメント）

- Tools
  - Paper Trading 検証レポート生成スクリプト
  - その他 CLI ユーティリティ

---

## セットアップ手順

1. リポジトリをクローン、あるいはプロジェクトルートへ移動。

2. Python 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール（最低限）:
   - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt が無い場合は上記パッケージを個別にインストールしてください。プロジェクトに依存パッケージが追加されている場合は適宜追加してください。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...           （AI 機能を使う場合必須）
   - KABUSYS_ENV=development|paper_trading|live
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO|DEBUG|...

   サンプル .env（最小）:
   ```
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   OPENAI_API_KEY=sk-xxxx
   ```

5. データディレクトリ作成:
   - mkdir -p data

---

## 使い方

- 監視ループを起動（SystemMonitor 単体の簡易スクリプト）
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 直接実行:
    - python src/kabusys/run_monitoring.py

  実行の特徴:
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限が必要な場合は警告でスキップ）。
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（Paper Trading DB は run_execution で分離）。

- 発注実行（ExecutionEngine）
  - Paper Trading モード（MockBroker）で実行する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading の場合はデフォルトで `data/paper_trading.db` を使用して本番 DB と分離します。
  - 本番モード:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 起動の特徴:
    - 起動時にプロセス優先度を "high" に設定し、SQLite（monitoring テーブルの初期化）と DuckDB 接続を行います。
    - Reconciler による再同期待機、RiskManager の初期化などを行い ExecutionEngine を起動します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。 --db で上書き可能。
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシなどを標準出力に表示し PASS/FAIL を判定します。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、Overview / Positions / Orders / System のタブを提供します。

- AI モジュール（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要。
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) を使って ai_scores を DuckDB に書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) を使って market_regime テーブルへ書き込みます。
  - 内部では gpt-4o-mini（JSON mode）を使用するため、API 使用量に注意してください。

- Kill Switch / Flag ファイル
  - KillSwitch は評価により `data/kill.flag` を書き込み、ExecutionEngine がこのフラグを検出して停止する仕組みです。
  - Execution 起動時にフラグクリアを行う設定（Settings.kill_flag_clear_on_start）が利用可能です。

---

## 設定の振る舞い（主なポイント）

- 自動 .env ロード:
  - プロジェクトルートを .git または pyproject.toml から検出して `.env` / `.env.local` を読み込みます。
  - OS 環境変数は保護され、`.env.local` は既存キーを上書きできます。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

- KABUSYS_ENV の値:
  - 有効値: development, paper_trading, live
  - paper_trading の場合、run_execution は専用の Paper DB を使用（本番とは完全分離）。

- PAPER_FILL_MODE:
  - Paper Trading の MockBroker の約定挙動を制御（instant / partial / never / reject）

- DB:
  - DuckDB: データ分析用（prices_daily, raw_financials 等を保持）
  - SQLite (monitoring.db): 監視ログやトレードログ等を永続化

---

## 主要なディレクトリ構成

（src/kabusys 以下の主なファイルを抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込みと Settings クラス
- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading に応じた分離）
- src/kabusys/monitoring/
  - monitoring_db.py        — SQLite の初期化・永続化 API（MonitoringDB）
  - system_monitor.py       — システム状態 / データ鮮度チェック
  - trade_monitor.py        — 注文滞留 / 約定異常チェック
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — フラグファイル書き込みロジック
  - alert_manager.py        — LINE 通知（push）
  - monitoring_engine.py    — 複数 Monitor を束ねる実行ループ
  - streamlit_dashboard.py  — Streamlit ベースの監視ダッシュボード
- src/kabusys/execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照されるがコード抜粋は一部)
  - broker_factory / broker_api / ...（ブローカー抽象化）
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/tools/
  - paper_verification_report.py

補足:
- `kabusys.data` パッケージ（prices_daily 等を扱う）や `kabusys.execution` の一部実装は本スニペットの外にある可能性があります。DuckDB に必要なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）が準備されている前提です。

---

## よくあるコマンド（まとめ）

- 監視（デフォルト 60s）:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - or: python -m kabusys.tools.paper_verification_report --db path/to/db --from ... --to ...

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI スコアリング（サンプル呼び出し、DuckDB 接続が必要）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, date(2026,4,1), api_key="sk-...")

---

## 注意事項 / 運用上のヒント

- OpenAI API（news_nlp / regime_detector）は外部API利用・課金が発生します。API キーは環境変数で管理し、呼び出し頻度やバッチサイズに注意してください。
- Monitoring / Execution の両方で PID ファイル（デフォルト data/execution.pid）や kill.flag（data/kill.flag）を使用するため、適切なファイル権限と監視を行ってください。
- Paper Trading は本番 DB と分離されますが、DuckDB 内の市場データは共通である場合があるため取り扱いに注意してください。
- SQLite / DuckDB のファイルロックや同時接続に注意。Streamlit は read-only URI を使って監視 DB を開くことを推奨します（例: file URI with ?mode=ro）。

---

この README はコードベースの抜粋に基づいて作成しています。実際のプロジェクトでは依存関係ファイル（requirements.txt）、起動スクリプト、より詳しい運用手順（systemd / supervisor / Docker 等）を用意することを推奨します。必要であれば起動スクリプトや example .env の雛形、systemd ユニット例なども作成します。希望があれば教えてください。