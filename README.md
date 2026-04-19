KabuSys — 日本株 自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 補助）を想定したコードベースです。  
主な設計方針は次のとおりです。

- 戦略・ポートフォリオ構築は純粋関数（メモリ内計算）で実装し、再現性を重視
- 発注ロジックは ExecutionEngine に集約。paper_trading モードでは MockBrokerClient を使用して本番 DB と分離
- 監視（Monitoring）は独立プロセスで稼働し、監視ログは SQLite に永続化
- ニュースの NLP（OpenAI）を用いたセンチメント評価や市場レジーム判定を備える
- ロギング・プロセス優先度設定など運用に必要なユーティリティを提供

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler と協調して発注管理
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存、データ鮮度を監視
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション上限の監視
  - KillSwitch: 重大リスク時に data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringEngine: 各モニタを束ねるポーリングループ
- ポートフォリオ構築
  - 候補選定、等分配/スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ・レジーム乗数の適用
- リサーチ / ファクター計算
  - Momentum / Volatility / Value などのファクターを DuckDB 上で計算
  - 将来リターン・IC（情報係数）・統計サマリ
- AI（OpenAI）連携
  - news_nlp: raw_news を集約して LLM により銘柄別センチメントを算出 → ai_scores に書き込み
  - regime_detector: ETF ma200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- 運用ツール
  - config_setup: .env を対話式で作成/更新
  - validate_config: 起動前の環境変数 / config/*.yaml の検証
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポートを生成
- ユーティリティ
  - ロギング設定（logs/ 日次ローテーション）
  - プロセス優先度・CPU affinity 設定
  - config 自動ロード（.env / .env.local）

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントの | 演算子を使用）
- SQLite は標準ライブラリで問題なし
- DuckDB, psutil, OpenAI SDK など外部パッケージが必要

例: 仮想環境作成とパッケージインストール
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - (Windows) .venv\Scripts\activate
   - (macOS/Linux) source .venv/bin/activate

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - （オプション）PyYAML（config の検証で使用）: pip install pyyaml

3. リポジトリルートに移動し .env を作成
   - python -m kabusys.config_setup
     - 対話式ウィザードで必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定します。
   - 重要: .env は決して Git にコミットしないでください。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 必要ディレクトリの作成（通常は自動作成されますが事前に用意しておくと安全）
   - mkdir -p data logs

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db に書き込み
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL / LOG_DIR / MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）

使い方
------

起動スクリプト
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 事前に KABUSYS_ENV=paper_trading を設定すると MockBrokerClient と paper_trading DB を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag を作成すると優雅に停止します。
  - 実行時に実行 PID を data/execution.pid に書きます（Settings.pid_file_path）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視プロセスは Settings.sqlite_path（本番監視 DB）を使用してログを永続化します。
  - data/stop_requested.flag による停止、または Ctrl+C（KeyboardInterrupt）で停止します。

運用関連
- Kill Switch
  - KillSwitch は監視結果に基づいて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START の設定で自動クリアの制御が可能（本番では 0 推奨）。

- レポート生成（ペーパートレード検証）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

AI 機能
- news_nlp.score_news / ai.regime_detector.score_regime を利用するには OPENAI_API_KEY が必要
- LLM 呼び出しにはリトライ / バックオフが組み込まれていますが、API 利用料・レート制限に注意してください

便利コマンド
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 日次ログ: logs/<app_name>.log（setup_logging による出力、デフォルト 30 日保持）

ディレクトリ構成（抜粋）
---------------------

以下は src/kabusys 以下の主要ファイル・パッケージの概要です。

- src/kabusys/
  - __init__.py            — パッケージ定義（バージョン等）
  - config.py              — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring 起動スクリプト

  - execution/             — 発注関連（ExecutionEngine, OrderManager, BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py     — SQLite による監視ログ永続化（schema 初期化、CRUD）
    - system_monitor.py    — CPU/メモリ/ディスク、プロセス、生データ鮮度チェック
    - trade_monitor.py     — 発注ログ監視（滞留注文等）
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag の管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py     — アラート送信（LINE 等との連携は別実装を想定）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py   — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py   — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py   — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリ

  - ai/
    - news_nlp.py          — ニュース集約 → OpenAI でセンチメント算出 → ai_scores へ書き込み
    - regime_detector.py   — ma200 + マクロニュースで市場レジーム判定

  - data/                  — 実行時生成ファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag など）
  - logs/                  — ログファイル出力先（デフォルト）

設計上の注意点 / 運用ヒント
--------------------------
- 本番起動（KABUSYS_ENV=live）時は KILL_FLAG_CLEAR_ON_START=0 を推奨。kill.flag の自動クリアは危険です。
- Monitoring は本番監視 DB (Settings.sqlite_path) を参照します。paper_trading でも監視は本番 DB を使う仕様です（意図的）。
- paper_trading モードでは paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全分離されます。
- ロギングは stdout と日次ローテートファイルの両方に出力します。ログディレクトリ作成に失敗した場合はコンソールのみで継続します。
- OpenAI を使う機能は API 利用料が発生します。API キーは安全に管理してください。
- DuckDB はリサーチ用途で大量のデータを効率的に処理するために使用しています。prices_daily / raw_financials / raw_news 等のテーブルを想定しています。

ライセンス / 貢献
----------------
（この README に記載のサンプルコードは説明目的です。実運用する場合は追加のテスト・監査・例外処理を必ず行ってください。）

付録: よく使うコマンド一覧
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。運用や拡張について不明点があれば、どの部分を詳しくドキュメント化するか指示してください。