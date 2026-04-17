# KabuSys

日本株向けの自動売買システム（モジュール群）。このリポジトリは戦略の研究・ファクター計算・ポートフォリオ構築・発注実行・監視・AI 補助（ニュースの NLP、レジーム判定）などを含むコンポーネントで構成されています。

注意: この README は src/kabusys 以下のコードを基に作成しています。実行環境によっては追加の設定や DB 初期化が必要です。

---

## 概要

KabuSys は以下のような責務を持つ複数のモジュールから構成されます。

- research: DuckDB を用いたファクター計算・特徴量解析（calc_momentum, calc_volatility, calc_value 等）
- portfolio: 候補選定、重み付け、ポジション算出、セクター制限など（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）
- execution: ブローカーとのやり取りを抽象化した注文発行・管理・再同期（OrderManager, Reconciler, ExecutionEngine など）
- monitoring: システム監視・取引監視・リスク監視・アラート送信・監視 DB（MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, AlertManager, KillSwitch 等）
- ai: ニュースの NLP によるセンチメントスコア算出、マクロニュースを使った市場レジーム判定（news_nlp, regime_detector）
- tools: 検証レポート等のユーティリティスクリプト（paper_verification_report）
- utils: OS 関係のユーティリティ（プロセス優先度・CPU affinity 設定 等）
- streamlit ダッシュボード: 監視 DB を可視化する UI（monitoring/streamlit_dashboard.py）

主要な設定は環境変数で行い、`.env` / `.env.local` をプロジェクトルートから自動読み込みします（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

---

## 機能一覧

- DuckDB / SQLite を用いた時系列・財務データ解析（ファクター、将来リターン、IC、統計サマリー）
- ポートフォリオ構築（候補選定、等重/スコア重み、リスクベースの株数決定、ロット丸め、セクターキャップ適用）
- 発注管理（OrderManager）と起動時の再同期（Reconciler）
- 実行エンジン（ExecutionEngine）と Paper Trading モード（本番 DB と分離して data/paper_trading.db を使用）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と永続的な監視ログ（SQLite）
- Kill Switch：条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送信
- LINE へのアラート通知（AlertManager、チャンネルアクセストークン／ユーザID 必要）
- ニュース NLP（OpenAI を用いた銘柄別センチメント集計）と市場レジーム判定（OpenAI 必要、フェイルセーフ実装あり）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 検証レポート生成ツール（パス指定可）

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... ; cd <repo>

2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な依存パッケージをインストール
   - requirements.txt がない場合は主なパッケージを直接インストール:
     - pip install duckdb psutil requests openai streamlit
   - 実行環境に応じて他の依存（例: numpy 等）が必要になる場合があります。

4. 環境変数設定
   - プロジェクトルートに `.env` を用意するか、OS 環境変数で設定します。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN=...（アラート送信に必要）
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - MONITOR_POLL_INTERVAL=60  （監視ポーリング間隔秒）
   - Settings モジュールは自動で `.env` を読み込みます（自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

5. データディレクトリの用意
   - data/ ディレクトリを作成しておくとログや DB の保存がスムーズです。
     - mkdir -p data

---

## 使い方（主要スクリプト・実行方法）

すべてのモジュールはパッケージとして実行可能です（python -m kabusys.<module> が動作することを想定）。

1. 監視ループを起動（SystemMonitor を単独で稼働）
   - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
   - 実行概要:
     - プロセス優先度を "high" に設定し、SQLite（monitoring DB）と DuckDB に接続して SystemMonitor を周期実行します。
     - 停止するには data/stop_requested.flag を作成するか、Ctrl-C。

2. 実行エンジンを起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV が `paper_trading` の場合はモックブローカーを使用し、Paper Trading 用の SQLite（デフォルト data/paper_trading.db）を使います。本番環境とは分離されます。
     - 実行中に data/stop_requested.flag が作成されると安全に停止します。
     - PID ファイル: data/execution.pid（Settings.pid_file_path を参照）

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH    （PAPER_TRADING_SQLITE_PATH を上書き）
   - 目的:
     - system_status, trade_logs, risk_logs などから各種指標（稼働率、成立率、送信率、P95 レイテンシ等）を集計して PASS/FAIL 判定を行います。

4. Streamlit ダッシュボード（監視用）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 機能:
     - ダッシュボード、保有ポジション一覧、直近注文ログ、最新のシステムステータス、リスクログを可視化します。
   - read-only モードで SQLite を開くように実装されています（監視データを読み取るのみ）。

5. AI 機能（ニュース NLP / レジーム判定）
   - news_nlp.score_news と regime_detector.score_regime が公開 API です（パッケージ経由あるいはスクリプト経由で呼び出します）。
   - 必須: OPENAI_API_KEY 環境変数
   - 処理:
     - news_nlp: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini 等）へ送信して ai_scores テーブルへ書き込みます。バッチ処理・リトライ・レスポンスバリデーションを実装。
     - regime_detector: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成し market_regime に書き込みます。API 失敗時はフォールバック（macro_sentiment=0）。

6. 停止 / Kill Switch
   - KillSwitch（monitoring.kill_switch）は RiskMonitor の結果に応じて data/kill.flag を書き込みます。ExecutionEngine 実行プロセスはこれを検知して停止します。
   - 手動で停止シグナルを出したい場合は data/kill.flag に理由を記述して作成できます（KillSwitch API で冪等に作成されます）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 開発/ペーパー/本番を切り替え (development | paper_trading | live)
  - paper_trading 時は paper 用 DB を使用（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な処理で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager の通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（1 で無効）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／ディレクトリ構成です（完全一覧ではありませんが主要な位置を示します）。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定読み込みロジック
    - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP（OpenAI）処理
      - regime_detector.py            — 市場レジーム判定（MA200 + LLM）
    - research/
      - __init__.py
      - factor_research.py            — モメンタム/バリュー/ボラティリティ算出
      - feature_exploration.py        — 将来リターン / IC / 統計サマリ
    - portfolio/
      - __init__.py
      - portfolio_builder.py          — 候補選定・重み計算
      - risk_adjustment.py            — セクターキャップ・レジーム乗数
      - position_sizing.py            — 株数算出・集約キャップ処理
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - (その他発注関連モジュール)
    - monitoring/
      - __init__.py
      - monitoring_db.py              — SQLite 永続層（schema 初期化を含む）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - utils/
      - __init__.py
      - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ
    - portfolio/, research/, ai/ の各モジュール —— 研究・計算関連

---

## 実運用時の注意点と運用フロー

- Paper Trading を行う際は必ず KABUSYS_ENV=paper_trading を設定し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）を確認してください。paper_trading ではブローカーと本番 DB を分離します。
- AI（OpenAI）を用いる機能は API 呼出しに伴うコストとレイテンシが発生します。API エラーや 429 に対するリトライおよびフェイルセーフが組み込まれていますが、API キー管理・利用制限には注意してください。
- Monitoring は稼働状況、データ鮮度、注文滞留、約定異常、ドローダウンなどを DB に蓄積します。Kill Switch による自動停止や LINE 通知などを運用ルールに合わせて設定してください。
- streamlit ダッシュボードは監視データの簡易可視化向けです。運用ダッシュボードとして利用する場合は認証・アクセス制御を組み合わせてください。
- Settings は自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して挙動を制御できます。

---

## 開発者メモ / 参考

- Settings（config.py）はプロジェクトルートを .git または pyproject.toml を基準に探索して .env を読み込みます。CWD に依存しない設計です。
- monitoring_db.init_monitoring_db は冪等でスキーマを作成し、既存 DB に対する小さなマイグレーション（カラム追加）も含みます。
- process_priority.set_process_priority は Windows / POSIX の差分を吸収しつつ失敗時は警告を出してスキップします（権限のない環境でも安全）。
- AI スコア処理は部分失敗（API エラーなど）時に既存データを保護するように設計されています（書き込み前に対象コードを限定して DELETE → INSERT）。

---

必要であれば README をさらに拡張して以下を追加できます:
- 実行例（環境変数を含むコマンドラインの具体例）
- 依存パッケージの厳密なバージョン一覧（requirements.txt）
- DB スキーマの詳細ドキュメント
- テスト実行方法や CI 設定例

追加でほしいセクションや、具体的な実行例（例: KABUSYS_ENV=paper_trading での実行コマンド）を教えてください。