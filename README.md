# KabuSys — 日本株自動売買システム（README）

この README はリポジトリ内の主要スクリプト・モジュールを対象に、セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件・依存パッケージ
- セットアップ手順
- 環境変数 / .env
- 設定検証・ウィザード
- 主要コマンドと使い方
- 動作フロー（重要挙動の説明）
- ディレクトリ構成（主要ファイル一覧）
- 開発上の注意点

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システム（アルゴリズム取引）です。
- 取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、
  AI を用いたニュースセンチメント／レジーム判定等のコンポーネントを備えています。
- DuckDB（分析用）と SQLite（監視・注文ログ用）を組み合わせて利用します。
- ペーパートレードモード（KABUSYS_ENV=paper_trading）では、実際のブローカーとは分離した専用 DB を使用します。

主な機能一覧
- 実行エンジン（ExecutionEngine）
  - ブローカー抽象化（実口座 / MockBroker）
  - 注文管理・リスク管理・約定照合
- 監視（Monitoring）
  - システムリソース（CPU/メモリ/ディスク）、プロセス監視、データ鮮度、
    注文/約定ログ、ダッシュボードの永続化
  - Kill Switch（条件を満たすと停止フラグを書き込み ExecutionEngine を止める）
- ポートフォリオ構築
  - 候補選定、等金額/スコア重み、位置サイズ計算、セクター制限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリ
- AI 関連
  - ニュースの LLM（OpenAI）によるセンチメントスコア化
  - マクロニュース + ETF MA200 に基づく市場レジーム判定
- 開発用ツール
  - .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール

前提条件・依存パッケージ
- Python 3.10 以上を推奨（typing の union 等を使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml（設定ファイルの検査を行う場合に任意）
- インストール例:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

セットアップ手順（ローカル開発用）
1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env を生成（下記「環境変数 / .env」を参照）
   - 対話式ウィザード: python -m kabusys.config_setup
5. 設定を検証:
   - python -m kabusys.validate_config
   - 警告も許容せず失敗扱いにする場合: python -m kabusys.validate_config --strict
6. デフォルトでは必要に応じて data/ や logs/ が自動作成されます。

環境変数 / .env（主要項目）
- 必須（起動前に設定すること）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — 実行環境: development | paper_trading | live
    - paper_trading: MockBroker を使用し、ペーパートレード専用 DB に記録
- DB 関連（デフォルトは data/ 配下）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- ロギング / プロセス
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - PID_FILE_PATH — ExecutionEngine 向け PID ファイルパス
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、production では 0 推奨）
- OpenAI
  - OPENAI_API_KEY — OpenAI を使う機能（ニュース NLP / regime）の実行に必要（未設定時は該当機能でエラー）
- その他（paper_trading の細かい挙動）
  - PAPER_FILL_MODE — instant | partial | never | reject（ペーパートレードの約定挙動）

設定検証・ウィザード
- .env を対話式で作成/更新:
  - python -m kabusys.config_setup
- 設定検証ツール:
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱いに

主要コマンド・使い方
- 実行エンジン（Execution）
  - 説明: ブローカークライアント生成 → 各依存コンポーネントを組み立てて ExecutionEngine を起動
  - 実行:
    - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - エンジン停止は data/stop_requested.flag を作成するか、Kill Switch による data/kill.flag 作成で行います。

- 監視プロセス（Monitoring）
  - 説明: SystemMonitor（リソース／データ鮮度等）をポーリングして監視ログを永続化
  - 実行:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL — ポーリング間隔（秒、デフォルト 60）
  - 動作:
    - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用する（KABUSYS_ENV に依らず）
    - data/stop_requested.flag があるとループを抜けて終了

- AI / レジーム・ニュース機能
  - ニュース NLP（ai.news_nlp.score_news）:
    - OpenAI API キーが必要（OPENAI_API_KEY）
    - 内部で raw_news / news_symbols / ai_scores テーブルを操作
  - レジーム判定（ai.regime_detector.score_regime）:
    - ETF 1321 の MA200 乖離 + マクロニュースを組み合わせて market_regime を更新
    - OpenAI API キーが必要（記事がない場合は安全に 0.0 を扱う）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - ペーパートレード DB のパスは --db > 環境変数（PAPER_TRADING_SQLITE_PATH）> デフォルト の順で解決
  - 出力: 稼働率、注文成功率、レイテンシ統計、PASS/FAIL 判定を標準出力に表示

動作フロー（重要な挙動）
- Kill Switch
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START 設定を尊重して処理するほか、
    稼働中に kill.flag を検知すると停止処理を行います。
- 停止フラグ
  - data/stop_requested.flag は run_monitoring/run_execution のローカル停止フラグとして使われます。
  - stop_requested.flag を作成すると次のポーリングや待機中にプロセスが優雅に終了します。
- DB の分離
  - paper_trading（ペーパートレード）時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番の monitoring DB と完全に分離されます。
- ロギング
  - logs/ に日次ローテーションでログを出力（TimedRotatingFileHandler、デフォルト 30 日保持）
  - コンソールは stdout に出力されます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（テーブル初期化 & CRUD）
    - system_monitor.py — システム状態監視
    - trade_monitor.py — 注文 / 約定監視（実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / 判定
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py —（通知・LINE 等を扱う想定の管理）
  - execution/ (一部のみ参照)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/（ランタイム / ローカルに生成される想定）
    - stop_requested.flag
    - kill.flag
    - execution.pid
    - monitoring.db / paper_trading.db / kabusys.duckdb など（設定により場所変更可）
  - logs/（ログファイル、実行時に作成）

（リポジトリ全体の木構造は実際のファイル数により差があります。上記は主要モジュールの抜粋です。）

開発上の注意点
- 本番運用（KABUSYS_ENV=live）は注意深い設定確認が必須です。validate_config の警告を必ず確認してください。
- .env は決してバージョン管理に含めないでください（README 先頭でも警告している通り）。
- OpenAI API 等外部サービスを利用する機能は API キー漏えいに注意してください。
- ペーパートレードと実口座データは分離されていますが、設定ミスで本番 DB を参照しないよう .env を確認してください。
- プロセス優先度変更や CPU affinity の操作は権限により失敗することがあります（警告ログが出ます）。

補足（よく使うコマンドまとめ）
- .env の生成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動:
  - python -m kabusys.run_monitoring
  - (MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring)
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - (KABUSYS_ENV=paper_trading python -m kabusys.run_execution)
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README は主要な使用方法と構成をまとめたものです。実際の運用にあたっては config/*.yaml（存在する場合）や個別ドキュメント（PortfolioConstruction.md 等）を参照してください。質問や追加でほしい項目があれば教えてください。