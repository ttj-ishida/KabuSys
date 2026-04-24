# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
本プロジェクトは戦略計算、ポートフォリオ構築、発注エンジン、監視、研究ツール、LLM を用いたニュース評価などを含む一連のコンポーネントで構成されています。

> 注意: この README はリポジトリ内のソースコード（src/kabusys 以下）を基に作成しています。

---

## プロジェクト概要

KabuSys は以下の機能を持つ日本株自動売買基盤です（設計意図の抜粋）:

- DuckDB / SQLite を用いたデータ管理（時系列価格、財務、ニュース、監視ログなど）
- 研究（ファクター計算・IC 計算）用モジュール
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine（発注エンジン）：実口座・ペーパートレードの切替に対応
- 監視サブシステム（System / Trade / Risk モニタ）と Kill Switch
- OpenAI を利用したニュースの NLP スコアリングおよび市場レジーム判定
- ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証など）
- 検証用ツール（Paper Trading 検証レポート生成）

---

## 主な機能一覧

- 環境設定
  - 対話式ウィザードで `.env` を生成・更新（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
- 発注/実行
  - ExecutionEngine（実取引 / ペーパートレードを切替可能）
  - RiskManager / OrderManager / Reconciler 等の実行関連コンポーネント
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による外部停止、停止フラグ（data/stop_requested.flag）
  - 監視ログの永続化（SQLite）
- 研究・リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- ポートフォリオ構築
  - 候補選定、等配分/スコア加重、リスクベースのポジションサイズ計算
  - セクター上限・レジーム乗数（調整）
- AI（LLM）連携
  - ニュース記事を集約して OpenAI（gpt-4o-mini 等）でセンチメント評価
  - マクロニュースと ETF MA200 乖離を用いた市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（期間指定可能）

---

## セットアップ手順

以下は一般的なローカルセットアップ手順の例です。

1. 必要環境（例）
   - Python 3.10+（ソースは型注釈・新しい構文を使用）
   - system パッケージ: make/apt 等は不要だが、psutil のビルドや OpenAI クライアントの依存がある場合あり
2. リポジトリをクローン
   - git clone <repo-url>
3. 仮想環境の作成・アクティベート（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
4. 依存パッケージをインストール
   - requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定ファイル検証に使用、任意）
   - 例: pip install duckdb psutil openai pyyaml
5. 環境変数の設定
   - 対話式ウィザードで `.env` を作成:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動で配置（既定のパスはリポジトリルートの `.env`）
   - 自動ロード機構:
     - config モジュールはプロジェクトルート（.git または pyproject.toml）を探索して `.env` を自動で読み込みます。
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う（デフォルト値を持つもの含む）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs
- OPENAI_API_KEY: OpenAI API キー
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（詳細は Settings クラス参照）

（設定は `kabusys.config.Settings` によって取得されます。詳細なプロパティは src/kabusys/config.py を参照してください）

---

## 使い方（起動・コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します（本番 DB と分離）。
    - エンジンは data/stop_requested.flag を監視して停止を受け付けます。
    - 実行中は data/execution.pid に PID を書く設計です。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）。
    - 監視プロセスは monitoring 用の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に関係なく本番パスを使用する設計）。
    - 停止フラグ: src/... に _STOP_FLAG = data/stop_requested.flag を見る実装

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

- AI / リサーチ機能（ライブラリとしての利用）
  - ニュース評価:
    - from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - ポートフォリオ:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

---

## ログ / ファイル / フラグ

- ログ
  - デフォルトログディレクトリ: logs/
  - 実行スクリプトは app_name に基づくファイルを生成:
    - logs/execution.log, logs/monitoring.log 等
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通して初期化されます

- DB
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite(監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合に利用）

- フラグ / PID
  - data/stop_requested.flag: run_* スクリプトが監視している停止フラグ（存在するとループ終了）
  - data/kill.flag: KillSwitch により ExecutionEngine 停止要求を表すフラグ（監視 -> Execution 停止）
  - data/execution.pid: ExecutionEngine の PID（起動時に使用）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の取得・検証、自動 .env 読み込み
- config_setup.py
  - .env を対話式で作成するウィザード
- validate_config.py
  - 起動前チェック CLI（必須環境変数、config/*.yaml、パス確認等）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV によるペーパートレード切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
- utils/
  - logging_setup.py: ログの統一設定（Stream + 日次ローテートファイル）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ラッパ
- monitoring/
  - monitoring_db.py: SQLite スキーマ作成 / 永続化 API
  - system_monitor.py: CPU / メモリ / データ鮮度 / 実行プロセス監視
  - trade_monitor.py: （トレード監視、ソース参照）
  - risk_monitor.py: ドローダウン・ポジション数監視
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - kill_switch.py: kill.flag 書き込みロジック
  - alert_manager.py: （アラート送信ラッパ、ソース参照）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
  - Execution に関する主要ロジック
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・ユニット丸め・スケール調整
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: モメンタム/ボラティリティ/バリュー計算（DuckDB ベース）
  - feature_exploration.py: forward returns / IC / 統計サマリー
- ai/
  - news_nlp.py: ニュースの LLM によるスコアリング（ai_scores への書き込み）
  - regime_detector.py: マクロニュース + ETF MA200 でレジーム判定
- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成ツール
- research, portfolio, ai 等の詳細はソース内 docstring を参照してください。

---

## 開発上の注意 / 設計上の要点

- 設定は .env を中心に管理。自動読込機能はプロジェクトルートを基準に動作します（CWD に依存しない）。
- モジュールは外部副作用（実際の発注等）に容易に差し替えられるよう抽象化されています（例: BrokerClientFactory）。
- LLM 呼び出しはリトライ・バックオフ・レスポンスバリデーションを備え、失敗時はフェイルセーフ（0.0 等）で継続する設計です。
- 監視系は kill.flag による停止や、監視ログの永続化・デデュープ（risk_logs）をサポートします。
- DuckDB は分析用途、SQLite は監視・注文ログ等の永続化用に使い分けられています。

---

## よくある操作例（まとめ）

- .env を対話的に作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- エンジン起動（開発/紙トレード/本番は KABUSYS_ENV で切替）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動（ポーリング間隔を 30 秒にしたい場合）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であればこの README をプロジェクトの実際の環境やポリシーに合わせてカスタマイズできます（例: 推奨 Python バージョン、具体的な requirements.txt、デプロイ手順、CI 設定、運用ルール）。どの点を追記／詳述したいか教えてください。