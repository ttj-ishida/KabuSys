# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ／運用用スクリプト群）

このリポジトリは、注文発行・執行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、リサーチ／ファクター計算、AI（ニュースNLP／レジーム判定）などを含むモジュール群で構成されています。各コンポーネントはできるだけ純粋関数または副作用の少ないクラスで実装されており、運用用スクリプトから組み合わせて稼働させます。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・ツール）
- 環境変数（主要なもの）
- 運用上のファイル・フラグ
- ディレクトリ構成

---

## プロジェクト概要

- 実稼働 / ペーパートレード両対応の実行エンジン（ExecutionEngine を起動する run_execution.py）
- システム状態・注文状態の監視とアラート（MonitoringEngine / run_monitoring.py）
- 監視データの永続化用 SQLite（monitoring.db） と 分析用 DuckDB
- ポートフォリオ構築、リスク調整、ポジションサイジングの純粋関数群（portfolio パッケージ）
- ファクター計算・リサーチ用モジュール（research パッケージ）
- ニュースを LLM でスコアリングする AI モジュール（news_nlp, regime_detector）
- 運用補助ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード等）

設計上のポイント
- 環境に依存する設定は Settings（kabusys.config）で一元管理（.env/.env.local 自動ロード対応）
- Paper Trading モードは本番 DB と分離（専用 SQLite）
- OpenAI を使う箇所は API キーを必須にし、API エラーはリカバリ可能な方針で実装
- 監視は kill flag / stop flag による外部制御を想定（運用での安全停止）

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - ブローカークライアントを抽象化し、paper_trading では MockBroker を使用
  - 起動時の自動リコンシリエーション（Reconciler）
  - OrderManager / OrderRepository による注文状態管理

- Monitoring
  - SystemMonitor: CPU/MEM/DISK/プロセス・データ鮮度を監視
  - TradeMonitor: 注文滞留（stale orders）／約定異常価格を検出
  - RiskMonitor: ドローダウン／ポジション数上限の監視とリスクログ化
  - KillSwitch: 条件に応じてデータ/kill.flag を書込むことで ExecutionEngine を停止
  - AlertManager: LINE Messaging API によるプッシュ通知（cooldown 管理）
  - Streamlit ダッシュボード（監視データ閲覧用）

- Portfolio
  - 候補選定（select_candidates）
  - 等配分・スコア加重配分（calc_equal_weights / calc_score_weights）
  - セクター制約適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 発注株数計算（calc_position_sizes） — 単元株丸め、利用可能現金でのスケーリング 等

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB に対する SQL+Python 実装）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー

- AI
  - news_nlp.score_news: raw_news を集約し OpenAI で銘柄毎センチメントを生成 → ai_scores に保存
  - regime_detector.score_regime: ETF(1321)の MA200 乖離とマクロニュースの LLM センチメントを合成してレジーム判定

- Tools
  - paper_verification_report: ペーパートレード DB を集計しパス/フェイル判定を表示
  - streamlit_dashboard: 監視 DB を可視化

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈やライブラリ互換性のため）
- Git でプロジェクトルートが存在すること（.env 自動ロードのため）

1. リポジトリをクローンしてソースルートへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

   主な依存:
   - duckdb: データ解析 / research / AI の入力集計
   - psutil: プロセス・システム情報取得（優先度設定 / CPU/MEM）
   - requests: LINE API 呼び出し
   - openai: LLM 呼び出し
   - streamlit: ダッシュボード
   - sqlite3: 標準ライブラリ（別途インストール不要）

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を配置して必要な設定を定義
   - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
   - 主要変数は後述の「環境変数」セクション参照

5. データディレクトリを作っておく（必要に応じて）
   - mkdir -p data

注: monitoring DB や paper_trading DB の初期化は起動スクリプト内で自動的に行われます（init_monitoring_db を呼び出す）。

---

## 使い方

以下は主要な起動方法とツールの使い方例です。

1) ExecutionEngine 起動（本番 / ペーパートレード）
- 環境変数でモードを切替:
  - 本番: KABUSYS_ENV=live
  - 開発: KABUSYS_ENV=development
  - ペーパートレード: KABUSYS_ENV=paper_trading
- 実行:
  - python -m kabusys.run_execution
  - ペーパートレード時は paper DB が data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
- 動作:
  - プロセス優先度を high に設定し、BrokerClientFactory でブローカークライアントを作成
  - 停止は data/stop_requested.flag を作成するか、実行中に kill.flag が作られると停止処理を行います

2) Monitoring 起動
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更（デフォルト 60）
- 実行:
  - python -m kabusys.run_monitoring
- 動作:
  - SystemMonitor / TradeMonitor / RiskMonitor を使って定期的にチェックし、監視 DB にログを残します
  - MONITOR は実行環境にかかわらず本番 sqlite_path を参照して監視データを保存します

3) Streamlit ダッシュボード（監視画面）
- 起動方法:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で監視データを表示します（DB が存在しない場合はエラーメッセージを表示）

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ等の指標と PASS/FAIL 判定を標準出力に出します

5) AI モジュール
- OpenAI API キーが必要:
  - 環境変数 OPENAI_API_KEY または関数引数で指定
- 主な関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 起動環境（development | paper_trading | live）, デフォルト: development
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env の自動読み込みを無効化
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の処理箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定モード（instant | partial | never | reject, デフォルト instant）
- PID_FILE_PATH: ExecutionEngine PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意:
- .env と .env.local の自動読み込みは Settings モジュールで行います（OS 環境変数 > .env.local > .env の優先度）。
- .env ファイルのパースはシェル風の export 形式やクォート、インラインコメントにある程度対応しています。

---

## 運用上のファイル・フラグ

- data/execution.pid: ExecutionEngine が起動時に書き込む PID ファイル（SystemMonitor がプロセス生存確認に使う）
- data/stop_requested.flag: run_execution/run_monitoring によるループ停止用フラグ（存在すると安全終了）
- data/kill.flag (または Settings.kill_flag_path): KillSwitch が書き込む停止フラグ（ExecutionEngine に停止を促す）
- data/monitoring.db: 監視ログ用 SQLite（init_monitoring_db で自動作成・マイグレーション）
- data/paper_trading.db: ペーパートレード専用 DB（KABUSYS_ENV=paper_trading 時に使用）

停止フロー:
- 運用者が kill.flag を置くと次回の MonitoringEngine の評価で KillSwitch が検出し、ExecutionEngine 側は停止処理を行います。stop_requested.flag は run_* スクリプト自体のループ停止用です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数/設定管理（.env 自動ロード等）
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py   — Paper Trading 検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py                    — ニュースの LLM センチメントスコアリング
      - regime_detector.py             — 市場レジーム判定（MA200 + LLM）
    - monitoring/
      - __init__.py
      - monitoring_db.py               — 監視用 SQLite 永続化層（init / MonitoringDB）
      - monitoring_engine.py           — 複数監視を束ねる実行ロジック
      - system_monitor.py              — CPU/MEM/DISK/プロセス/データ鮮度監視
      - trade_monitor.py               — 注文滞留 / 約定異常監視
      - risk_monitor.py                — ドローダウン / ポジション上限監視
      - kill_switch.py                 — kill.flag の読み書き
      - alert_manager.py               — LINE プッシュ通知
      - streamlit_dashboard.py         — Streamlit 監視ダッシュボード
    - portfolio/
      - __init__.py
      - portfolio_builder.py           — 候補選定・重み計算
      - risk_adjustment.py             — セクターキャップ・レジーム乗数
      - position_sizing.py             — 発注株数決定・スケールダウン処理
    - research/
      - __init__.py
      - factor_research.py             — Momentum/Volatility/Value 等
      - feature_exploration.py         — forward returns / IC / summary
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 broker / order_repository 等)
    - utils/
      - __init__.py
      - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
    - (その他 data / strategy / 等のパッケージが上位に存在する想定)

---

## 備考・運用のヒント

- Monitoring の初期化は run_monitoring/run_execution 内で行われるため、手動で DB スキーマを用意する必要は基本的にありません。
- OpenAI を使う機能は API 利用料が発生します。テスト時は環境変数を与えずにスキップするか、API 呼び出し関数をモックしてください（モジュール内でテストフックを利用可能）。
- Paper Trading モードは本番 DB と分離されるため、実運用前の挙動確認に活用してください。PAPER_FILL_MODE によって約定挙動を変更できます。
- process_priority の設定はプラットフォーム依存で失敗することがあります（権限不足など）。失敗時は警告が出て処理は継続します。
- alert_manager は LINE トークンが未設定でも安全に無視します（ログに警告が出ます）。実運用では必ず LINE トークンと user_id を設定してください。

---

この README はコードベースから抽出した情報を元に作成しています。実際の運用開始前に .env の中身（シークレット）や Broker クライアントの設定、DB パス等を確認し、テスト環境で十分に動作確認を行ってください。質問や追加したいドキュメントがあれば教えてください。