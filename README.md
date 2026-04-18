README
======

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
シグナル生成・ポートフォリオ構築・ポジションサイズ計算・発注エンジン（ExecutionEngine）・監視（Monitoring）・リスク管理・研究用モジュール・ニュース NLP を用いた AI スコアリング等を備えています。  
設計方針として「本番と検証の分離」「ルックアヘッドバイアスの回避」「外部 API 呼び出しのフェイルセーフ化」が徹底されています。

主な機能
--------
- Execution
  - 実際のブローカー（kabuステーション）またはペーパートレード（MockBrokerClient）での発注処理
  - OrderManager / Reconciler / RiskManager による注文管理・再整合・リスク制御
  - Paper Trading 用に本番 DB と分離された SQLite を使用可能
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス監視
  - TradeMonitor: 発注ログ・滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - KillSwitch: しきい値到達時にデータ/ファイル経由で ExecutionEngine を停止
  - MonitoringEngine: モニタを束ねて定期実行
- Portfolio Construction
  - 銘柄選定（スコアソート）、等金額配分 / スコア配分、リスクベースサイズ計算
  - セクター集中制限、レジーム乗数
- Research
  - DuckDB 接続を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント化し ai_scores に格納（batch・リトライ・バリデーション付き）
  - 市場レジーム判定（ETF + マクロニュース + LLM）
- ツール
  - Paper Trading 検証レポート（稼働率 / 注文成功率 / レイテンシ 等）
- ユーティリティ
  - 設定ウィザード（.env 作成支援）
  - 設定検証 CLI（環境変数・config/*.yaml の静的チェック）
  - 統一されたロギング設定、プロセス優先度設定、CPU affinity ユーティリティ

セットアップ
------------
前提
- Python 3.10+ を推奨（typing | match 等の近代機能を利用）
- SQLite は標準組み込み、DuckDB / psutil / openai 等は pip でインストール

例: 仮想環境の作成と依存パッケージのインストール
1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: PyYAML（config ファイル検証に使用）: pip install pyyaml

初期設定
1. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン / kabu API パスワード / DB パス / KABUSYS_ENV 等を対話式で作成します
2. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合: python -m kabusys.validate_config --strict

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH: data/kabusys.duckdb (default)
- SQLITE_PATH: data/monitoring.db (default; Monitoring は常に これを使用)
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL (default: INFO)
- OPENAI_API_KEY: OpenAI 呼び出しに使用
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

最小の .env 例
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

使い方
------
1. 監視プロセスを起動（Monitoring）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
   - 実行:
     - python -m kabusys.run_monitoring
   - 注意:
     - run_monitoring は KABUSYS_ENV にかかわらず sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
     - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します（stop フラグ）。

2. 実行エンジンを起動（ExecutionEngine）
   - KABUSYS_ENV=paper_trading のときは MockBrokerClient が使われ、paper_trading 用 SQLite に記録されます（PAPER_TRADING_SQLITE_PATH）。
   - 実行:
     - python -m kabusys.run_execution
   - 注意:
     - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
     - 実行中に stop_requested.flag を作成するとエンジンを停止します。
     - Kill Switch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine はそれを参照して停止する設計になっています。

3. 設定ウィザード / 検証
   - ウィザード: python -m kabusys.config_setup
   - 検証: python -m kabusys.validate_config [--strict]

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD --to YYYY-MM-DD
     - --db PATH で DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

5. AI / 研究モジュールの利用（ライブラリ呼び出し）
   - ai.news_nlp.score_news(conn, target_date, api_key=None)
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - research.calc_momentum/ calc_volatility / calc_value / calc_forward_returns などは DuckDB 接続を受け取って計算します。
   - これらは CLI スクリプトではなく Python API として利用します（独自スクリプトからインポートして呼び出す想定）。

ロギング
--------
- 共通の logging は kabusys.utils.logging_setup.setup_logging で設定されます。
- デフォルトログディレクトリ: logs/
- 実行時: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- stdout にもログを出力します。

停止 / Kill Switch
-----------------
- stop_requested.flag:
  - run_execution / run_monitoring はプロジェクトルート/data/stop_requested.flag の存在をチェックし、存在すれば起動を中止または実行を終了します。
- kill.flag:
  - KillSwitch（監視）により data/kill.flag が作成されると ExecutionEngine は停止対象となります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアします（本番環境では 0 を推奨）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                     — パッケージ定義
- config.py                       — 環境変数 / Settings
- config_setup.py                 — .env 対話式ウィザード
- validate_config.py              — 設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — Monitoring ポーリング起動スクリプト

サブパッケージ（主要モジュール）
- ai/
  - news_nlp.py                    — ニュース NLP スコアリング（OpenAI 統合）
  - regime_detector.py             — 市場レジーム判定（ETF + LLM）
- monitoring/
  - monitoring_db.py               — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py              — システム状態 / データ鮮度監視
  - trade_monitor.py               — 発注ログ監視（ファイルは省略）
  - risk_monitor.py                — ドローダウン / ポジション上限監視
  - kill_switch.py                 — Kill Switch 実装
  - monitoring_engine.py           — 監視ループ束ね
  - alert_manager.py               — （通知の抽象化）※実装参照
- execution/
  - execution_engine.py            — 実行エンジン本体（run_session 等）
  - order_manager.py               — 注文管理
  - order_repository.py            — 発注ログ保存
  - broker_factory.py              — ブローカークライアント生成
  - reconciler.py                  — 注文再整合
  - risk_manager.py                — 発注リスク制御
- portfolio/
  - portfolio_builder.py           — 候補選定・重み計算
  - position_sizing.py             — 株数決定・単元丸め・cap 適用
  - risk_adjustment.py             — セクターキャップ・レジーム乗数
- research/
  - factor_research.py             — ファクター計算（momentum/value/volatility）
  - feature_exploration.py         — 将来リターン / IC / サマリ
- tools/
  - paper_verification_report.py   — Paper Trading 検証レポート
- utils/
  - logging_setup.py               — ログ初期設定ユーティリティ
  - process_priority.py            — プロセス優先度 / CPU affinity 設定
  - (他ユーティリティ)

注意事項 / ベストプラクティス
------------------------------
- 本番（KABUSYS_ENV=live）では .env を Git 管理せず、LINE などの通知設定を適切に行ってください。
- validate_config による事前チェックを行い、--strict モードで警告も FAIL として扱うことを推奨します（特に本番）。
- OpenAI API を使用する機能は API キー設定とレート制限への配慮が必要です。失敗時はフォールバック動作（スコア 0.0 等）する実装になっていますが、運用負荷には注意してください。
- Paper Trading と本番 DB は分離できます（PAPER_TRADING_SQLITE_PATH を使用）。検証時は Paper Trading を活用してください。

ライセンス / 貢献
-----------------
- このリポジトリのライセンス・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者に確認）。

サポート
--------
- 実行中のエラー調査は logs/ 下のログと data/ 内のフラグファイル、SQLite（monitoring.db / paper_trading.db）を参照してください。SQLite 内の各テーブル（system_status, trade_logs, risk_logs, positions, dashboard）に監視・トレード情報が蓄積されます。

以上。初期セットアップや運用上の疑問があれば、具体的なエラーメッセージやログを添えて質問してください。