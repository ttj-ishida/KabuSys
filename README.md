README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のサンプル実装です。  
主に次の責務を持つモジュール群で構成されています。

- 発注エンジン（ExecutionEngine）と注文管理
- 監視コンポーネント（System / Trade / Risk Monitor）とアラート管理
- ポートフォリオ構築（候補選定・重み付け・サイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI 統合（ニュースセンチメント・市場レジーム判定）
- 運用支援ツール（環境ウィザード・設定検証・ペーパートレード検証レポート等）

設計方針の一部：
- データ基盤に DuckDB（分析）と SQLite（監視・発注ログ）を使用
- 環境変数による設定駆動（.env の自動読み込みに対応）
- Paper Trading 環境は本番 DB と分離（専用 SQLite を使用）
- OpenAI を用いた NLP/レジームは API キー必須。フォールバック / フェイルセーフがある

主な公開 API / CLI：
- python -m kabusys.config_setup : .env の対話式作成・更新
- python -m kabusys.validate_config : 設定検証（--strict オプションあり）
- python -m kabusys.run_execution : ExecutionEngine 起動スクリプト
- python -m kabusys.run_monitoring : 監視ポーリングループ起動スクリプト
- python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート生成

機能一覧
--------
- 発注関連
  - BrokerClientFactory を介したブローカークライアント生成（paper_trading では Mock）
  - OrderRepository / OrderManager / Reconciler / RiskManager による発注・整合処理
- 監視
  - SystemMonitor：CPU / メモリ / ディスク使用率・プロセス生存・データ鮮度監視
  - TradeMonitor：滞留注文や約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限に対するアラートとログ化
  - MonitoringEngine：上記を束ねたポーリングエンジン
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager：LINE Push での通知（設定があれば）
- ポートフォリオ構築
  - 候補選定（スコア / ランク）
  - 等比重・スコア加重の重み計算
  - セクター集中制限適用
  - ポジションサイズ計算（単元丸め、資金・ポジション上限、コストバッファ）
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）算出、統計サマリー
- AI 統合
  - news_nlp.score_news: ニュースを OpenAI でセンチメント化して ai_scores に書込み
  - regime_detector.score_regime: ETF の MA とマクロニュースを組み合わせ市場レジーム判定
- ツール
  - 環境ウィザード（config_setup）
  - 設定検証（validate_config）
  - ペーパートレード検証レポート（paper_verification_report）

セットアップ手順
----------------
1. リポジトリをクローン / 取得
   - 例: git clone <repo>

2. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（config YAML の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai requests PyYAML

4. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（後述の主要環境変数参照）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗としたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの作成（.env のパスに合わせて）
   - 例: mkdir -p data

主要な環境変数
----------------
（.env に設定する代表的なキー）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API 用パスワード

- 実行モード
  - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、発注は MockBrokerClient を使い data/paper_trading.db に記録

- データベース / ファイルパス
  - DUCKDB_PATH : 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（monitoring）DB のパス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH : ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH : KillSwitch が書き込むフラグ（デフォルト: data/kill.flag）

- Paper Trading の動作
  - PAPER_FILL_MODE : instant | partial | never | reject（デフォルト: instant）

- ログ・通知
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（任意）

- OpenAI
  - OPENAI_API_KEY : news_nlp / regime_detector が利用

- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 : 自動 .env ロードを無効化する（テスト等）

使い方
------

.env の作成・検証
- 対話式に作成:
  - python -m kabusys.config_setup
- 検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

ExecutionEngine（発注エンジン）の起動
- 実行（KABUSYS_ENV により動作が変わる）
  - python -m kabusys.run_execution
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます
- 停止方法
  - run_execution はプロジェクトルートの data/stop_requested.flag を検出すると終了します
  - KillSwitch が作動すると data/kill.flag が書き込まれ、ExecutionEngine 側で検出され停止されます
- PID
  - 実行中は pid ファイル（デフォルト data/execution.pid）を利用してプロセス生存を管理

Monitoring（監視ポーリング）の起動
- 実行
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 挙動
  - Monitoring は KABUSYS_ENV に関わらず本番の sqlite_path（Settings.sqlite_path）を使用します
  - 停止フラグ: data/stop_requested.flag が存在するとループを終了
  - 監視結果・リスクイベントは monitoring 用 SQLite に永続化される

Paper Trading 検証レポート
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH

AI 関連
- news_nlp.score_news / regime_detector.score_regime
  - OpenAI API キー（OPENAI_API_KEY）必須
  - 両機能とも内部で LLM 呼び出しにリトライ・バリデーションの仕組みを持つ
  - news_nlp は銘柄ごとのニュースを集約して一括バッチ送信（最大チャンクサイズ 20）

プロセス優先度
- run_monitoring / run_execution の起動時に set_process_priority("high") を呼び出します
  - psutil を利用。OS 権限により設定できない場合は警告が出てスキップされます

プロセス制御 / 停止
- 手動停止（運用者が停止を要求）:
  - data/stop_requested.flag を作成すると run_execution と run_monitoring が終了します
    - 例: touch data/stop_requested.flag
  - 削除: rm data/stop_requested.flag
- KillSwitch（自動停止トリガ）:
  - RiskMonitor 等の評価により条件を満たすと data/kill.flag を書き込みます
  - ExecutionEngine は起動時と定期チェックで kill.flag を確認し、存在する場合は停止されます
  - Kill flag をクリアする設定 KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に自動クリアします（本番では注意）

ディレクトリ構成
----------------
リポジトリの主要なディレクトリ / ファイル（src/kabusys 以下を示す）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - execution/                — 発注関連（OrderManager, RiskManager 等）（部分的に参照）
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
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
  - utils/
    - process_priority.py

データ・ファイル（デフォルト）
- data/kabusys.duckdb     — DuckDB（分析）
- data/monitoring.db       — 監視用 SQLite（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db    — ペーパートレード用 SQLite（paper_trading 時）
- data/execution.pid       — ExecutionEngine の PID（デフォルト）
- data/stop_requested.flag — 手動停止フラグ（存在すると run_* スクリプトが終了）
- data/kill.flag           — KillSwitch による停止フラグ（存在で Execution 停止）

依存関係（主要）
- Python 標準ライブラリ（sqlite3, threading, logging, pathlib, datetime, json 等）
- 外部パッケージ:
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（任意: validate_config の YAML 検証）

注意事項 / 運用メモ
-------------------
- run_monitoring は Settings.sqlite_path を参照して監視ログを書き込みます。環境に関わらず本番の sqlite_path を使用するため、監視向け DB の取り扱いに注意してください。
- paper_trading モードでは発注は本番 API に送られず、専用 SQLite（PAPER_TRADING_SQLITE_PATH）にログされます。
- process priority の設定はプラットフォーム依存かつ権限が必要となる場合があります。失敗すると警告が出力されますが動作は継続します。
- OpenAI を利用する機能は API コストが発生します。API 利用量とモデル（デフォルト gpt-4o-mini）に注意してください。
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください（config_setup でも警告あり）。

開発者向け（補足）
------------------
- モジュールは比較的疎結合に設計されています。AI 関連の外部呼び出し部分はテストで差し替え可能（_call_openai_api をモック等）。
- MonitoringEngine.run_once() はテスト用に単一実行を行うヘルパとして便利です。
- DuckDB をテスト用に使う場合、テーブルが存在しないと関数は例外をハンドリングしている箇所が多いので、テスト用の最小スキーマを作成しておくとよいです。

問い合わせ / 貢献
-----------------
バグ報告、改善提案、プルリクエストはリポジトリの issue / PR を利用してください。README の改善提案も歓迎します。