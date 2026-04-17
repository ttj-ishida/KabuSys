# KabuSys README

本プロジェクトは日本株向け自動売買システム「KabuSys」のコードベースです。  
この README ではプロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

注意: 実行には Python 3.10+ を推奨します。外部依存ライブラリ（例: duckdb, psutil, openai, requests, PyYAML など）が必要です。requirements.txt は本リポジトリに含まれていない想定のため、必要に応じてインストールしてください。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ日本株自動売買/研究プラットフォームです。

- 戦略（ファクター・リサーチ、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- ExecutionEngine（発注管理、ブローカー抽象化、ペーパートレード対応）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用補助ツール（.env 設定ウィザード、設定検証、検証レポート生成）

設計方針の例:
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドバイアス回避（日時参照を安全に行う）
- フェイルセーフ（API 失敗時のフォールバック）
- 多くのコンポーネントは副作用を持たない純粋関数として設計

---

## 機能一覧（主なモジュール）

- 実行系
  - run_execution.py: ExecutionEngine を起動。ペーパートレード時は MockBroker を使い DB を分離。
  - ブローカーファクトリ / OrderManager / RiskManager / Reconciler 等。
- 監視系
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）。
  - monitoring_engine.py: System / Trade / Risk モニタを束ねる。
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - monitoring_db.py: SQLite に監視ログ・トレードログ等を永続化。
- ポートフォリオ構築
  - portfolio_builder.py: 候補選定・スコアソート・重み計算
  - position_sizing.py: 株数計算・lot 単位丸め・aggregate cap
  - risk_adjustment.py: セクター上限・レジーム乗数
- リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - research.feature_exploration: 将来リターン、IC、統計サマリー等
- AI
  - ai.news_nlp: raw_news を OpenAI に投げて銘柄ごとにセンチメントを算出 → ai_scores に保存
  - ai.regime_detector: ETF 1321 の MA 乖離 + マクロニュースで市場レジーム判定
- ユーティリティ
  - config.py: 環境変数/.env の読み込み・Settings 抽象
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: .env や config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: ペーパー取引ログから検証レポートを生成
  - utils.process_priority: プロセス優先度/CPU affinity 設定ユーティリティ

---

## 主な環境変数（必須 / 重要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用設定（代表例・デフォルトを併記）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant|partial|never|reject（デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグ（デフォルト: data/kill.flag）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager が LINE 通知するために利用（任意）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env 自動読み込み:
- プロジェクトルート (pyproject.toml/.git を基準) にある .env と .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate または .venv\Scripts\activate

2. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai requests PyYAML
   （プロジェクトに requirements.txt があればそれを利用）

3. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します。シークレット値（API キー等）は画面で入力してください。

4. 設定検証
   - python -m kabusys.validate_config
   - 必須項目の未設定や config/*.yaml のパース等をチェックします。
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリの確認
   - デフォルトでは data/ 以下に SQLite / DuckDB ファイルや PID/flag ファイルを配置します。必要に応じてディレクトリを作成してください（多くの書き込み処理は自動で親ディレクトリを作ります）。

---

## 使い方（主要コマンド）

- .env の対話式作成/更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレード:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行時は data/execution.pid に PID を書き込みます。停止シグナルは data/stop_requested.flag や data/kill.flag（KillSwitch）等を用います。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で指定可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず production 用 sqlite_path を参照して監視ログを記録します。

- Kill Switch の運用
  - KillSwitch は RiskMonitor 等の結果に基づいて data/kill.flag を書き込みます。ExecutionEngine 起動時や運用側で flag を検査/クリアして安全に停止できます。
  - ExecutionEngine は stop フラグ（data/stop_requested.flag）を検出すると安全に停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH がない場合）
  - レポートは uptime / fill rate / send rate / latency(P95) などをチェックし PASS/FAIL を出力します。

- AI モジュール（例）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、raw_news を集約して OpenAI に問い合わせ ai_scores に書き込みます。
    - OPENAI_API_KEY を環境変数で設定するか引数に渡してください。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF MA とマクロニュースを組み合わせて market_regime テーブルへ書き込みます。

---

## 実行時の注意点

- プロセス優先度: run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定します（utils.process_priority）。権限により設定に失敗する場合は警告が出ます。
- DB 分離: KABUSYS_ENV=paper_trading の場合、ペーパートレードは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離されます。
- Auto .env 読み込み: config.py が自動的にプロジェクトルートの .env/.env.local を読み込みます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し: API 呼び出しはリトライ/バックオフを備えていますが、API キー・帯域・コストについて事前に確認してください。
- LINE 通知: AlertManager は channel token / user id が設定されていない場合は通知をスキップします。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込み・Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/  (実行時に生成される、リポジトリルートの data ディレクトリを想定)
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - *.db / *.duckdb
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/ （発注周りの実装）
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
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
  - monitoring/（上記）
  - その他（data/schema や config/*.yaml を参照する設計）

config ディレクトリ（リポジトリルート）
  - config/system_config.yaml
  - config/data_config.yaml
  - config/strategy_config.yaml
  - config/risk_config.yaml
  - config/execution_config.yaml
  - config/monitoring_config.yaml

---

## よくある運用フロー（例）

1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を検証
4. データ投入（prices_daily / raw_financials / raw_news 等を DuckDB に準備）
5. 本番またはペーパートレードを起動
   - python -m kabusys.run_execution
6. 監視を別プロセスで起動
   - python -m kabusys.run_monitoring
7. 必要に応じて AI モジュール・レジーム判定・検証レポートを実行

---

## トラブルシューティング / 補足

- .env は絶対に Git にコミットしないでください（config_setup でも注意書きがあります）。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップします（警告が出ますが動作自体は可能）。
- process priority / cpu affinity の設定はプラットフォーム依存、権限が必要な場合があります。設定失敗時は警告で続行します。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います。

---

必要に応じて README に追記します。実行例や systemd / supervisor 用のサービスファイルなども必要であれば教えてください。