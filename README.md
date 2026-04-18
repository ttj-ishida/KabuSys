KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株自動売買システム「KabuSys」のコアロジック群を含みます。
本 README はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

概要
----
KabuSys は以下の主要コンポーネントから構成される、運用・監視・研究を目的としたコードベースです。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況、注文ログ、リスク指標の監視・アラート・Kill Switch
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：ニュースの NLP スコアリング、マクロセンチメントによるレジーム判定（OpenAI を利用）
- Portfolio モジュール：銘柄選定、重み付け、ポジションサイズ計算、セクター制限等
- Utilities：ロギング設定、プロセス優先度設定、設定管理ウィザード／検証ツールなど
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト

主な特徴（機能一覧）
-------------------
- ExecutionEngine
  - 実口座（live）とペーパートレード（paper_trading）を切り替え可能
  - BrokerClientFactory により適切なブローカークライアントを生成
  - OrderManager、Reconciler、RiskManager を統合して実取引フローを実行

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、データ鮮度、プロセス生存チェック
  - TradeMonitor：注文滞留や約定異常の検出（trade_logs 参照）
  - RiskMonitor：ドローダウンやポジション上限の監視（dashboard, positions）
  - KillSwitch：閾値超過時に data/kill.flag を書き、ExecutionEngine を安全に停止
  - MonitoringDB：SQLite を用いた永続化（system_status, trade_logs, positions, risk_logs, dashboard）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）
  - news_nlp: raw_news を集約して NLP により銘柄別センチメントを計算・ai_scores に格納
  - regime_detector: ETF MA とマクロニュースの LLM スコアを合成して market_regime を作成

- Portfolio
  - 銘柄候補選定、等重/スコア重み計算、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（ロット丸め、aggregate cap、コストバッファ対応）

- ユーティリティ
  - setup_logging: stdout + 日次ローテーションログ出力
  - process_priority: Windows/Linux の違いを吸収してプロセス優先度を設定
  - config_setup: .env 作成ウィザード（対話式）
  - validate_config: .env や config/*.yaml を起動前に検証
  - tools/paper_verification_report: ペーパートレード検証レポート生成

セットアップ手順
----------------

1. リポジトリをクローン / ルートへ移動
   - 本 README の動作はプロジェクトルート（pyproject.toml または .git のあるディレクトリ）を前提とします。

2. Python 環境を用意
   - Python 3.9+ を推奨（コードは typing | 構文を使用）
   - 仮想環境を作成して有効化してください。

3. 依存パッケージをインストール
   - 主に以下のパッケージが必要です（requirements.txt があればそちらを使用してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証用、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. ディレクトリ作成
   - data/ および logs/ を作成（多くのデフォルトファイルパスは data/ 下を参照します）
     - mkdir -p data logs

5. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成。代表的な環境変数（デフォルト値があるものは省略可）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード DB の上書き（paper_trading 時のみ使用）
     - LOG_LEVEL — デフォルト: INFO
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 任意（本番アラート用）
     - OPENAI_API_KEY — AI 機能利用時に必要

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

7. DB 初期化
   - 初回起動時、Execution / Monitoring 起動スクリプト内で SQLite / DuckDB のテーブルは自動作成されます（init_monitoring_db 等による）。

使い方（実行例）
----------------

- ExecutionEngine を起動（プロジェクトルートで実行）
  - 本番/ペーパーは KABUSYS_ENV に依存
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid に PID を書きます（PID ファイルは Settings.pid_file_path）
  - 停止フラグ: data/stop_requested.flag を作成するとエンジンは順次シャットダウンします
  - Kill Switch による強制停止は data/kill.flag を書き込む仕組み（KillSwitch が書き込みます）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で監視ループの間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は monitoring DB（Settings.sqlite_path）へ記録されます（監視は本番 sqlite_path を使用）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - フィルタ例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

主要設定項目（要点）
--------------------
- KABUSYS_ENV
  - development / paper_trading / live
  - paper_trading の場合、Execution は専用の paper_sqlite_path を使い MockBrokerClient（実口座アクセスなし）で動作

- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb（分析用）
  - SQLITE_PATH: data/monitoring.db（監視ログ）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用）

- ログ
  - ログは stdout と logs/<app_name>.log （日次ローテーション）に出力
  - LOG_DIR 環境変数で変更可能

- Kill / Stop
  - Kill Switch: data/kill.flag — KillSwitch が書き込み、Execution 停止を促す（明示的に書き込む方法もあり）
  - Stop flag: data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的に kill.flag をクリアします（本番では 0 推奨）

ディレクトリ構成
-----------------
以下は主要ファイル / モジュールの簡易ツリー（src/kabusys 配下）です。実際のプロジェクトルートは pyproject.toml 等を含みます。

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / Settings 管理（.env 自動ロード）
    - config_setup.py                  — .env 対話式ウィザード
    - validate_config.py               — 設定検証 CLI
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — Monitoring ポーリング起動スクリプト

    - ai/
      - __init__.py
      - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py             — レジーム判定（MA + マクロ NLP）

    - monitoring/
      - monitoring_db.py               — SQLite schema + MonitoringDB クラス
      - system_monitor.py              — CPU/メモリ/Disk・データ鮮度・プロセスチェック
      - trade_monitor.py               — （注文監視ロジック）※実装ファイルあり
      - risk_monitor.py                — ドローダウン / ポジション上限監視
      - monitoring_engine.py           — 各 Monitor を束ねる
      - kill_switch.py                 — KillSwitch 実装
      - alert_manager.py               — （通知管理）※実装ファイルあり

    - execution/
      - broker_factory.py              — BrokerClientFactory（Mock / 実ブローカー切替）
      - execution_engine.py            — ExecutionEngine 本体
      - order_manager.py               — OrderManager
      - order_repository.py            — OrderRepository（DB 関連）
      - reconciler.py                  — Reconciler
      - risk_manager.py                — RiskManager（リスク制御）
      - ...                            — その他実行関連モジュール

    - portfolio/
      - portfolio_builder.py           — 候補選定・重み計算
      - position_sizing.py             — 株数決定・キャップ・丸め
      - risk_adjustment.py             — セクター制限・レジーム乗数
      - __init__.py

    - research/
      - factor_research.py             — ファクター計算（momentum, value, volatility）
      - feature_exploration.py         — forward returns, IC, 統計サマリ
      - __init__.py

    - tools/
      - __init__.py
      - paper_verification_report.py   — ペーパートレード検証レポート生成スクリプト

    - utils/
      - logging_setup.py               — ログ設定ユーティリティ
      - process_priority.py            — プロセス優先度 / affinity ユーティリティ
      - __init__.py

補足 / 運用上の注意
------------------
- .env は決してリポジトリにコミットしないでください（config_setup も README に注意書きあり）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）を必要とします。API 利用料に注意してください。
- 本番環境（KABUSYS_ENV=live）での起動前には validate_config を実行し、LINE 通知設定等を確認してください。
- Monitoring は常に本番用 sqlite_path を参照して監視データを記録します（run_monitoring 内の設計）。
- ペーパートレードは本番 DB と完全分離するよう設計されています（paper_trading 用 sqlite を使用）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（参照用）
- ライセンス情報が別途ある場合はリポジトリの LICENSE を参照してください。

問題報告 / 貢献
----------------
バグ報告や改善提案は Issue を立ててください。Pull Request は歓迎します。変更を加える場合は既存のユニットテストや validate_config を利用して動作を確認してください。

以上です。必要であればサンプル .env のテンプレート、起動スクリプトの具体的なデバッグ手順、各モジュールの詳細ドキュメント（API サンプル）を別ドキュメントとして追加します。どの情報がさらに欲しいか教えてください。