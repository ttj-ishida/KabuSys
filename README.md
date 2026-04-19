# KabuSys

日本株自動売買システム KabuSys のドキュメント（README）。  
このリポジトリは戦略・発注・監視・研究・AI（ニュース NLP）などを含む自動売買プラットフォームのコードベースです。

## プロジェクト概要
KabuSys は以下を目的とした日本株向けの自動売買基盤です。

- シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）
- 実行・約定のログ化とリスク監視（Monitoring）
- Paper Trading（検証用の完全分離 DB）対応
- DuckDB を用いた研究／ファクター計算モジュール
- OpenAI を用いたニュースセンチメント解析（ai/news_nlp）と市場レジーム判定（ai/regime_detector）
- 運用のための設定ウィザード・検証ツール・レポート生成ツール

主要なエントリポイント（起動スクリプト）はパッケージモジュールとして提供されています（python -m kabusys....）。

## 主な機能一覧
- ExecutionEngine：ブローカークライアント経由で発注を行うエンジン（本番/ペーパートレード切替）
- Monitoring：CPU/メモリ/ディスク、データ鮮度、注文滞留・約定異常、ドローダウン・ポジション上限の監視
- Kill Switch：閾値超過時に data/kill.flag を書き込み、Execution を停止する仕組み
- Portfolio モジュール：候補銘柄選定・重み計算・ポジションサイズ計算・セクターキャップ・レジーム調整
- Research モジュール：ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン・IC・統計サマリ
- AI モジュール：
  - news_nlp：raw_news から銘柄単位のセンチメントを OpenAI によって算出・保存
  - regime_detector：ETF の MA とマクロニュースの LLM スコアを合成し日次レジーム判定
- ユーティリティ：
  - 環境変数の .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- 永続化：
  - SQLite（監視・発注ログ等） — monitoring.db（環境による分離あり）
  - DuckDB（時系列価格や財務など分析用）

## セットアップ手順（開発／運用向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無い場合の代表的な依存ライブラリ:
     - pip install duckdb psutil openai pyyaml

   ※ OpenAI を使わない場合は openai は不要。PyYAML は config/*.yaml のバリデーションで使用しますが必須ではありません。

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - または手動で .env を作成（下記「主要環境変数」を参照）

5. ディレクトリ作成（必要に応じて）
   - data/ （SQLite / PID / flag 用）
   - logs/ （ログ保存先）
   - 例: mkdir -p data logs

6. 設定検証（任意）
   - python -m kabusys.validate_config
     - --strict を付けると警告も FAIL 扱いで exit(1)

注意:
- monitoring の DB は常に（環境にかかわらず）settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。
- Execution は KABUSYS_ENV=paper_trading の場合、paper 用 DB（PAPER_TRADING_SQLITE_PATH, default data/paper_trading.db）を使用して本番 DB と分離します。

## 主要環境変数（例・デフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必須）
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の約定挙動)
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（settings 参照）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基に .env/.env.local を自動で読み込みます。  
- テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 使い方 — 起動コマンド例
- ExecutionEngine を起動（本番 or ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行時は data/execution.pid（デフォルト）に PID を書く実装があるため同時起動に注意

- Monitoring を起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- 設定ウィザード（.env を対話式生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

停止・Kill Switch:
- 手動で Execution を停止したい場合:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループは検知して終了します。
- システムが自動的に停止判定する場合:
  - Monitoring が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を安全に停止する機構があります（KillSwitch）。

ログ:
- ログは stdout（コンソール）に出力され、日次ローテーションで logs/<app_name>.log に書き出されます（logs ディレクトリに出力）。ログレベルは LOG_LEVEL または setup_logging の引数で制御。

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下をパッケージ化している想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py         — Monitoring 起動スクリプト（python -m kabusys.run_monitoring）

  - execution/                — 発注関連モジュール群（broker, engine, order_manager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — CPU/メモリ/ディスク、データ鮮度、プロセス監視
    - trade_monitor.py        — 注文滞留・約定異常検出（ファイル内にあり）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 monitor を束ねる実行ループ
    - alert_manager.py        — LINE 等への通知（実装に依存）

  - portfolio/                — ポートフォリオ構築ロジック（純粋関数）
    - portfolio_builder.py    — 候補選定、等配分/スコア配分
    - position_sizing.py      — 株数計算・単元丸め・aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/                 — DuckDB を使ったファクター計算・分析
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py             — ニュースを OpenAI でスコアリングし ai_scores へ書込
    - regime_detector.py      — マクロ＋MA200 を用いたレジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

  - utils/
    - logging_setup.py        — 統一的なロギング設定（stdout + 日次ローテート）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定（Windows/Linux 対応）
    - __init__.py

- data/                        — データファイル（SQLite / PID / flags）を置く想定（runtime が自動作成）
- logs/                        — ログ出力先（setup_logging が作成）

## 実運用上の注意点
- 本番環境（KABUSYS_ENV=live）では設定ミスが致命的になります。validate_config で必ずチェックしてください。
- .env は機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- OpenAI API を使用する AI モジュールは API 料金・レイテンシに注意して運用してください。失敗時はフェイルセーフ（スコア 0 等）にフォールバックする実装になっていますが、外部依存は注意が必要です。
- Paper Trading（KABUSYS_ENV=paper_trading）のデータは本番 DB と物理的に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を確認）。

## 開発・拡張のヒント
- DuckDB 接続を渡して純粋関数でファクター計算を行う設計になっており、テスト容易性が高いです。
- utils.logging_setup.setup_logging を全起動スクリプトで統一して呼ぶことでログ出力を統一できます。
- process_priority.set_process_priority により起動時にプロセス優先度を上げる実装があるため、必要に応じて呼び出し順に注意してください。

---

その他、各モジュールには docstring と実装コメントが充実しています。具体的な API やテーブルスキーマ、運用手順は該当モジュールのソースコード内コメントを参照してください。必要であれば README に追記したい箇所（例: サンプル .env、運用手順書テンプレート、systemd ユニット例など）を教えてください。