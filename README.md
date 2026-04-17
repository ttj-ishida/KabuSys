# KabuSys

日本株向け自動売買システムのコードベース。システム監視、Execution エンジン、ポートフォリオ構築、リサーチ、ニュース NLP（OpenAI）連携などの機能を含みます。

注意: この README は src/kabusys 配下のコードを元に作成しています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主なコマンド／実行方法）
- 環境変数（主要）
- アーキテクチャ / ディレクトリ構成
- 運用上の注意点

---

プロジェクト概要
- 日本株自動売買（ExecutionEngine）とそれを支える監視・リスク管理コンポーネント、研究（factor / feature）モジュール、ニュース NLP によるセンチメント評価などを備えたパッケージ。
- DuckDB を使った分析用テーブル（prices_daily, raw_financials など）と、SQLite を使った監視／発注ログ保存を併用する設計。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替えて動作可能。

主な機能
- ExecutionEngine（発注処理、Order 管理、リスク管理、Reconciler 等）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / AlertManager / KillSwitch）
- ポートフォリオ構築（シグナル順位付け、重み付け、ポジションサイジング、セクター制限、レジーム乗数）
- Research（ファクター計算：momentum / volatility / value、将来リターン、IC 計算、統計サマリ）
- AI（ニュースのセンチメントを OpenAI で評価し ai_scores に格納、マーケットレジーム判定）
- CLI ツール：.env 対話式生成ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成ツール

セットアップ手順（開発マシン向け）
1. Python
   - Python 3.10+ を推奨（typing の | Union を使用しているため）。
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests pyyaml
   - （実運用では OS パッケージや追加の依存が必要になる場合があります）
4. .env の用意
   - 対話式ウィザードで生成: python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動作成（.env.example はプロジェクトに含める想定）
5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit 1）になります
6. DB 初期化
   - monitoring 用 SQLite（デフォルト: data/monitoring.db）はスクリプト起動時に必要テーブルが自動作成されます（init_monitoring_db）。
   - DuckDB（デフォルト: data/kabusys.duckdb）は分析用に別途データ投入が必要。

主要な使い方（コマンド例）
- ExecutionEngine を起動（本番/ペーパーはいずれも Settings.KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録し、本番 DB と完全分離されます。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - プロセス優先度を "high" に試みて設定します（psutil を利用、権限不足の場合は警告を出してスキップ）。
    - 実行中、data/execution.pid に PID を書きます（pid ファイルパスは Settings.pid_file_path で変更可）。
- Monitoring を起動（継続的ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使ってログを記録します（環境に無関係）。
  - 停止は data/stop_requested.flag を作成することで行えます（run_execution と同じフラグ）。
- .env を作成・更新（対話式）
  - python -m kabusys.config_setup
- 設定検証 CLI
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- AI 関連（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — OpenAI API でニュースを評価して ai_scores に書き込む。api_key が None の場合は環境変数 OPENAI_API_KEY を参照。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)  — レジーム判定と market_regime への書き込み。
  - これらは OpenAI の API キー（OPENAI_API_KEY）を必要とします。

主要な環境変数（Settings 経由で参照）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 実行環境指定
  - KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- DB パス
  - DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパー取引時の専用 SQLite（デフォルト: data/paper_trading.db）
- AI / Notifications
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager による LINE 通知（任意）
- ログ・監視
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト INFO）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH — kill フラグパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で有効、デフォルト "0"）
- Paper Trading 設定
  - PAPER_FILL_MODE — MockBroker の約定モード（instant|partial|never|reject、デフォルト instant）

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数の読み込み・Settings クラス（.env 自動ロード機能含む）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — .env / config/*.yaml の起動前検証ツール
  - run_execution.py — ExecutionEngine の起動スクリプト（プロセス優先度設定、DB 接続、停止フラグ監視）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL に対応）
  - tools/
    - paper_verification_report.py — Paper Trading の実行結果検証レポート生成
  - ai/
    - news_nlp.py — raw_news を OpenAI で評価して ai_scores に保存
    - regime_detector.py — MA200 とマクロニュースを合成して市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層（テーブル作成・マイグレーション含む）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度の監視
    - trade_monitor.py — 注文滞留・約定異常価格の検出
    - risk_monitor.py — ドローダウン・ポジション上限監視（ダッシュボード更新、リスクログ）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン（run / run_once）
    - alert_manager.py — LINE へ通知（クールダウン管理）
    - kill_switch.py — kill.flag の書き込み・評価
  - portfolio/
    - portfolio_builder.py — 候補選択・重み計算
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数計算（単元丸め、aggregate cap 対応）
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ラッパー（psutil 利用）
  - execution/ （発注ロジック関連 — ここでは省略されていますが ExecutionEngine 等の主要部分が置かれる想定）
  - data/ （ランタイム生成データ: monitoring.db, kabusys.duckdb, execution.pid, kill.flag など）

運用上の注意点
- Kill Switch / stop フラグ
  - data/kill.flag により ExecutionEngine の停止シグナルを発行できます（KillSwitch が評価して存在すれば停止）。
  - run_execution / run_monitoring は data/stop_requested.flag の有無で起動 / 停止動作を制御しています（フラグファイル名はソース参照）。
- Paper Trading
  - ペーパートレード時は本番監視 DB と発注 DB を分離しているため、本番データの汚染を防げます。
- OpenAI API
  - AI 機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはエラー時にリトライやフォールバック（score=0 等）を行う実装ですが、API 利用量と料金に注意してください。
- プロセス優先度 / CPU affinity
  - 起動時に process priority を "high" に設定しようとしますが、OS と権限によっては失敗します（その場合はログに警告が出ます）。

追加情報 / 推奨ワークフロー
1. .env を対話式で作成: python -m kabusys.config_setup
2. 設定を検証: python -m kabusys.validate_config
3. DuckDB に価格データや財務データをロード（外部プロセス）
4. ExecutionEngine を paper_trading で動かして振る舞い確認
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. Monitoring を別プロセスで立ち上げる
   - python -m kabusys.run_monitoring
6. 結果確認・レポート:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
- このリポジトリは複数の外部サービス（kabuステーション、J-Quants、OpenAI）、およびネイティブライブラリ（psutil, duckdb）に依存します。実運用前にテスト環境で充分な検証を行ってください。
- 詳細な設計やアルゴリズムの背景はコード内コメントや StrategyModel.md / PortfolioConstruction.md 等の設計文書を参照してください（プロジェクトに同梱されている想定）。

必要であれば、この README をベースに
- 簡易構築スクリプト（requirements.txt / Dockerfile）や
- 運用ハンドブック（起動順序、障害対応手順）
のテンプレートを作成します。どちらを希望しますか？