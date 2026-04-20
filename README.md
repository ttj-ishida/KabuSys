KabuSys — 日本株自動売買システム
=============================

本プロジェクトは日本株向けの自動売買システム（KabuSys）のコードベースです。戦略（リサーチ）・ポートフォリオ構築・発注エンジン・監視・AIによるニュース分析などのコンポーネントを含み、ローカルでのペーパートレードから本番運用までを想定しています。

主な特徴
--------
- モジュール構成により、戦略開発（research）・ポートフォリオ構築（portfolio）・実行（execution）・監視（monitoring）・AI（ニュース／レジーム判定）を分離。
- DuckDB（分析用）・SQLite（監視／発注ログ）を併用したデータ設計。
- OpenAI を用いたニュースのセンチメント解析 / マクロセンチメント評価（LLM 統合）。
- ペーパートレード用に実際の注文を行わない MockBrokerClient を利用するモードをサポート。
- 起動時の対話式 .env ウィザード（config_setup）と設定検証ツール（validate_config）を同梱。
- 日次ローテーションのログ出力、プロセス優先度設定、Kill Switch（フラグファイルによる安全停止）など運用支援機能。

主な機能一覧
------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV により Paper/Live を切替）
  - run_monitoring.py — SystemMonitor ポーリングループ起動（監視）
- 設定
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env と config/*.yaml の事前検証 CLI
  - kabusys.config.Settings — 環境変数の集中管理（デフォルトや検証ロジック含む）
- 監視 / 安全停止
  - monitoring/* — SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、DB 層
  - monitoring_db.py — 監視用 SQLite スキーマとクラス
- 発注 / 実行
  - execution/* — ExecutionEngine、OrderManager、RiskManager 等（BrokerFactory 経由で実ブローカー or Mock を切替）
- ポートフォリオ構築
  - portfolio/* — 候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム調整
- リサーチ
  - research/* — ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン / IC 計算
- AI（LLM 統合）
  - ai/news_nlp.py — ニュース記事の銘柄別センチメントスコアリング（OpenAI）
  - ai/regime_detector.py — マクロセンチメント + ETF MA を統合した市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <リポジトリ URL>
   - cd <repo>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   以下は推奨パッケージ例です（実際の requirements.txt を用意している場合はそちらを使用してください）。
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML（validate_config の YAML 検証を有効化する場合）

   例（まとめて）:
   - pip install duckdb psutil openai PyYAML

4. 環境変数を作成（対話式ウィザード）
   - python -m kabusys.config_setup
   ウィザードは .env を生成します。生成後は運用に応じて KABUSYS_ENV を設定してください（development / paper_trading / live）。

5. 設定検証（必須）
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って修正してください。
   - --strict を付けると警告も失敗扱いになります。

6. DB ディレクトリの準備
   - デフォルトは data/ に DB・PID・フラグファイル等が置かれます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定してください。

使い方
------

基本的な起動例（ローカル単体実行）

- 監視ループを起動（常時監視）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 起動時にプロセス優先度が "high" に設定されます（可能な範囲で）。

- ExecutionEngine を起動（発注エンジン）
  - KABUSYS_ENV によって振る舞いが異なります:
    - development: 発注は行わない（テスト）
    - paper_trading: MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録（本番 DB と分離）
    - live: 実ブローカーへ発注（kabuステーション等）
  - python -m kabusys.run_execution

- ペーパートレード検証レポート（例）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH を指定可能。

- AI（ニューススコア／レジーム判定）
  - ai モジュールの関数は DuckDB 接続と target_date を受け取り、OpenAI API キーを環境変数 OPENAI_API_KEY（または関数引数）で参照します。
  - score_news / score_regime の実行には OPENAI_API_KEY が必要です。

重要な環境変数（主なもの）
--------------------------
- 基本
  - KABUSYS_ENV: execution モード（development / paper_trading / live） — default: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） — default: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

- API / 認証
  - JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（AI 関連機能で必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）

- データパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）

- ペーパートレード挙動
  - PAPER_FILL_MODE: instant|partial|never|reject（デフォルト "instant"）

- 監視・プロセス制御
  - PID_FILE_PATH: 実行プロセスの PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

運用上の注意
------------
- .env ファイルは秘密情報を含むため絶対に Git 等へコミットしないでください（config_setup の先頭にも警告を出しています）。
- validate_config は本番環境（KABUSYS_ENV=live）での危険設定（例: KILL_FLAG_CLEAR_ON_START=1）を警告します。必ず確認してください。
- Kill Switch は data/kill.flag の作成で発動します。KillSwitch はドローダウンやポジション上限をトリガーに flag を書きます。
- run_monitoring と run_execution は別プロセスで実行してください。両者は PID / flag ファイルで相互監視を行います。
- OpenAI 呼び出しは料金が発生するため、テスト時はキーと呼び出し回数に注意してください。

ディレクトリ構成
----------------

以下は src/kabusys 配下の主なファイル・ディレクトリ（抜粋）です:

- src/kabusys/
  - __init__.py                   — パッケージ定義（__version__ 等）
  - config.py                     — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py               — 対話式 .env ウィザード（CLI）
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py            — 監視用 SQLite スキーマ & DB 操作用クラス
    - system_monitor.py           — システム状態 / データ鮮度監視
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - kill_switch.py              — Kill Switch（フラグファイル操作）
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - alert_manager.py            — （アラート統合管理: 実装がある場合）
    - trade_monitor.py            — 注文に関する監視（滞留・約定異常等）

  - execution/
    - execution_engine.py         — 実行エンジン本体
    - broker_factory.py           — BrokerClient の生成（Mock / 実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py        — 候補選定・重み付け
    - position_sizing.py          — 発注株数計算
    - risk_adjustment.py          — セクター上限・レジーム乗数

  - research/
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 将来リターン / IC / 統計サマリ
  - data/                          — （実行時に生成される想定: DB・PID・フラグ等）
  - logs/                          — ログ出力先（デフォルト）

付録: よく使うコマンド例
-----------------------
- .env を作る（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視の起動（背景プロセスや systemd で管理するのを推奨）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution の起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ライセンス / 貢献
----------------
（ここにプロジェクトのライセンスや貢献ガイドラインを記載してください）

お問い合わせ / 参考
-------------------
- 本 README はソースコードの docstring と実装に基づいて作成しています。実運用に際しては config/*.yaml（必要に応じて）や運用ドキュメントを併せて参照してください。