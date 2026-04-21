# KabuSys

日本株向けの自動売買・研究・監視フレームワーク（モジュール群）です。  
このリポジトリは、発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・ファクター計算・ニュース NLP（OpenAI）・検証ツール等を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存ライブラリ
- セットアップ手順
- 使い方（主要スクリプト・コマンド例）
- 環境変数（主要なもの）
- 実行時の挙動メモ（Kill Switch / stop フラグ 等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買に必要なコンポーネントを分離したモジュール群として提供します。
- コンポーネント例:
  - ExecutionEngine（発注実行とオーダーマネージャ）
  - Monitoring（システム監視、トレード/リスク監視、Kill Switch）
  - Portfolio Construction（銘柄選定・重み付け・ポジションサイジング）
  - Research（ファクター計算・特徴量探索）
  - AI（ニュースセンチメント / レジーム判定：OpenAI を利用）
  - CLI ユーティリティ（.env ウィザード、設定検証、レポート生成）

---

主な機能一覧
- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成（Mock 対応）
  - RiskManager / OrderManager / Reconciler と連携して注文実行
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常等の検出
  - RiskMonitor: ドローダウン検出、ポジション上限監視
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）作成
  - 監視ログ永続化（SQLite）
- Portfolio
  - 候補選定、等重/スコア重み計算、セクター上限適用、レジーム乗数、株数決定（単元丸め）
- Research
  - DuckDB を使ったファクター計算 (momentum / volatility / value)、将来リターン、IC 計算、統計サマリ
- AI
  - ニュースセンチメント（OpenAI Chat API）で ai_scores を生成
  - マクロニュース + ETF MA を合成した市場レジーム判定（market_regime）
  - API レート制限・エラーに対するリトライ・フェイルセーフ実装
- ツール
  - config_setup: .env を対話式で作成/更新
  - validate_config: .env / config/*.yaml の起動前チェック
  - paper_verification_report: ペーパートレード DB の検証レポート生成

---

前提条件 / 依存ライブラリ
- Python 3.9+（型ヒント等を考慮）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証時に任意）
- SQLite は標準ライブラリで使用
- ローカル実行時には kabuステーション API（またはモック）への接続設定が必要

（プロジェクトに requirements.txt が無い場合は上記パッケージを pip でインストールしてください）

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

---

セットアップ手順（ローカル）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して依存をインストール
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml

3. .env を作成（対話式ウィザード推奨）
   python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 本番実行時は KABUSYS_ENV=live を設定（注意）

4. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - 問題がある場合は出力に従って修正してください
   - --strict を付けると警告も FAIL 扱いになります

5. データディレクトリ
   - デフォルトで data/ 下のファイルを使用します（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください

注意:
- monitoring は常に本番用 sqlite_path を使用して監視 DB を初期化します（run_monitoring.py の挙動）。
- ペーパートレード実行時は PAPER_TRADING_SQLITE_PATH（defaults: data/paper_trading.db）を使用し本番 DB と分離します。

---

使い方（主要スクリプト）
- 実行（ExecutionEngine）を起動
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録されます
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 起動中は data/execution.pid に PID を書き込みます

- 監視ループを起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - 監視は常に Settings.sqlite_path（monitoring DB）を使用して永続化します
  - 停止は data/stop_requested.flag の作成でループを抜けます

- 設定ウィザード（.env 作成/更新）
  python -m kabusys.config_setup

- 設定検証 CLI
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定、もしくは環境変数 PAPER_TRADING_SQLITE_PATH を使用

- AI / リサーチ系関数呼び出し（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュース NLP を実行し ai_scores テーブルへ書き込む
    - OPENAI_API_KEY（または api_key 引数）必須
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF MA とマクロニュースでレジーム判定を行い market_regime に書き込む

ログ:
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルトは stdout と logs/<app_name>.log（日次ローテート、30日保持）
- LOG_DIR 環境変数や引数でログ出力先を変更可能

プロセス優先度:
- 起動スクリプトは set_process_priority("high") を呼んで優先度を高く設定します（psutil を使用）

---

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DBパス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- OpenAI:
  - OPENAI_API_KEY
- ログ:
  - LOG_LEVEL（DEBUG/INFO/…）
  - LOG_DIR
- 監視/停止関連:
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒）
- その他:
  - PAPER_FILL_MODE（ペーパー注文の約定モード: instant | partial | never | reject）

---

実行時の挙動メモ（Kill Switch / stop フラグ 等）
- 停止制御:
  - data/stop_requested.flag: run_monitoring / run_execution のループを停止するために使われる（運用側で作成）
  - KillSwitch（kabusys.monitoring.kill_switch）はリスク検知時に data/kill.flag を作成し ExecutionEngine に停止を促します
  - ExecutionEngine 側は起動時に kill.flag の存在を確認し（設定によってはクリア）起動を抑止できます
- ログや DB は基本的に冪等操作に注意して実装されています（INIT や upsert は安全に実行可能）

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/設定読み込み
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
      - ...（Execution 関連実装）
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/                     — 実行時に使用するファイル群（logs/ や data/ は作成されます）
    - config/                   — YAML 設定ファイル群（system_config.yaml 等。テンプレは scripts/generate_config.py で生成）

（注）ここに記載のファイルは主要なものを抜粋しています。実装はモジュール単位で細かく分かれています。

---

運用上の注意
- KABUSYS_ENV=live の場合は設定を慎重に確認してください（本番注文・資金リスク）。
- .env を絶対に Git にコミットしないでください。
- OpenAI API やブローカー API の鍵は適切に管理してください（環境変数か秘密管理を使用）。
- monitoring と execution は独立した実行プロセスとして運用することを想定しています。
- 監視 DB（SQLite）は運用中にスキーママイグレーションを検出して自動でカラム追加等を行いますが、事前バックアップは推奨します。

---

開発者向け
- 各モジュールは単体テストしやすい設計（副作用を抑えた純粋関数群が多く含まれます）。
- OpenAI 呼び出し等はラッパー関数にまとめており、テスト時はパッチして外部呼び出しを差し替え可能です（例: unittest.mock.patch）。
- DuckDB を使ってオフラインでの研究処理を行えます。prices_daily / raw_financials 等のテーブルを用意して利用してください。

---

問題/改善提案
- README の不足や動作に関する質問、バグ報告、設計改善の提案は issue を立ててください。

以上。必要であれば README を英語版に翻訳したり、導入手順を Docker / systemd など運用用に展開したテンプレートを追加します。希望があれば教えてください。