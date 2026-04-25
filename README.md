README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の軽量実装です。本リポジトリはトレード実行、監視、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）を含むモジュール群を提供します。設計方針としては:
- 実行と監視を分離（monitoring / execution）
- Paper trading（ペーパートレード）と Live を明確に分離（専用 SQLite DB）
- DuckDB を分析用途（prices_daily, raw_financials 等）に使用
- OpenAI を利用したニュースセンチメント / レジーム判定機能を備える
- .env による設定管理、対話式ウィザードと事前検証ツールあり

主な機能
--------
- ExecutionEngine（発注エンジン）起動 / 停止制御（run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録
  - プロセス優先度設定、pid ファイル管理
- Monitoring（監視）ポーリングループ（run_monitoring）
  - システム稼働状況、データ鮮度、トレードログ、リスク指標の定期チェック
  - Kill Switch（条件満たすと data/kill.flag を書き込み）による安全停止
  - MONITOR_POLL_INTERVAL によるポーリング間隔調整
- 監視データ永続化（monitoring_db） — SQLite（冪等なテーブル作成・マイグレーション含む）
- リスク監視（RiskMonitor）・トレード監視（TradeMonitor）・システム監視（SystemMonitor）
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジションサイズ算出・セクター上限等）
- 研究用モジュール（ファクター計算 / 将来リターン / IC / 統計サマリ）
- AI モジュール
  - news_nlp: raw_news を OpenAI でスコア化して ai_scores テーブルに書き込む
  - regime_detector: ma200 とマクロニュースで市場レジーム判定して market_regime に書込
- ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

前提条件 / 推奨パッケージ
------------------------
（プロジェクトルートで仮想環境を作成して利用してください）
- Python 3.9+
- 必要なパッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- （任意）requirements.txt がある場合は pip install -r requirements.txt

セットアップ手順
--------------
1. レポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もし requirements.txt が無い場合、少なくとも以下をインストールしてください:
     - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードを利用（推奨）:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を配置（.env.example を参考に）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

重要な環境変数（主要なもの）
----------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注はモックとなり data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で利用
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

使い方
------
基本的な起動・運用例を示します。

1. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - エラーがあると exit(1)。--strict で警告も失敗扱いにできます。

3. 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - 起動時にプロセス優先度を「high」に設定します。
   - KABUSYS_ENV=paper_trading の場合、発注はモックとなり data/paper_trading.db に記録されます。
   - PID ファイル (デフォルト: data/execution.pid) を出力します。
   - 停止させるには:
     - data/stop_requested.flag を作成する（run_execution はこのファイルを監視して停止）
     - あるいは Kill Switch によって data/kill.flag が書き込まれると停止やアラートが発生します。

4. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - デフォルトで 60 秒ごとにポーリング。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
   - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
   - DB パス指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

6. AI 機能の呼び出し（ライブラリ API）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - conn: duckdb 接続
     - api_key: None なら OPENAI_API_KEY を環境変数から読む
   - regime_detector.score_regime(conn, target_date, api_key=None)

ログ
----
- 共通ユーティリティ setup_logging により、標準出力（stdout）と日次ローテートログ（logs/<app_name>.log）に出力します。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御可能。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

停止 / Kill Switch
------------------
- 手動停止要求:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
- 自動停止（Kill Switch）:
  - RiskMonitor 等が条件を満たした場合、kill_switch が data/kill.flag を書き込みます（既に存在する場合は再書き込みしない）。
  - 実行エンジン起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると既存の kill.flag を自動でクリアします（本番では危険なので 0 推奨）。

ディレクトリ構成（主なファイル）
------------------------------
（src/kabusys 以下を示す）

- kabusys/
  - __init__.py — パッケージ宣言、バージョン
  - config.py — 環境変数/.env ロードと Settings クラス（各種設定プロパティ）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ出力の統一設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/ (実行エンジン周り: broker, order_manager, risk_manager 等を含む)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤー
    - system_monitor.py — システム/データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留注文・異常約定検出 等）
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 監視コンポーネントの束ね
    - alert_manager.py —（通知/アラート送信）
  - portfolio/
    - portfolio_builder.py — 候補抽出 / 重み計算
    - position_sizing.py — 株数計算（ロット丸め、リスク制限、aggregate cap）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — OpenAI によるニュースセンチメント集約・書き込み
    - regime_detector.py — ma200 + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - data/ (runtime 用; DB / PID / flag ファイル等)
    - monitoring.db (default)
    - paper_trading.db (paper 用 default)
    - kill.flag, stop_requested.flag, execution.pid
  - logs/ (ログ出力先、デフォルト)

補足 / 運用上の注意
------------------
- Paper trading は本番 DB と分離するため PAPER_TRADING_SQLITE_PATH を利用してください（デフォルト: data/paper_trading.db）。
- OpenAI キーを用いる機能は API 呼び出し回数・コストに留意してください。失敗時はフェイルセーフ（スコア=0 等）で継続する実装になっていますが、運用ポリシーを決めてください。
- 本番環境では KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0、LINE 通知設定等を必ず確認してください。validate_config は本番チェックを含むため利用を推奨します。
- ローカルでのテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして .env 自動読み込みを無効化できます。

ライセンス・貢献
----------------
（必要に応じてここにライセンス情報やコントリビュート手順を記載してください）

以上。README の追加改善（例: 実行フロー図、構成図、より詳細な運用手順など）が必要であればお知らせください。