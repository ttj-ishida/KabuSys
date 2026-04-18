README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリは取引エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター研究、ニュースNLP（LLM を用いたセンチメント評価）などの主要コンポーネントを含んでいます。設計方針として「本番データベースと研究／ペーパートレードを分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時は安全側にフォールバック）」を重視しています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカ抽象化
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常等）
  - RiskMonitor: ドローダウン、ポジション数上限監視、リスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込んで ExecutionEngine を停止
  - MonitoringEngine: 上記を束ねてポーリング実行
- ポートフォリオ構築（pure functions）
  - 候補選定、等ウェイト／スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - 特徴量探索、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）連携
  - news_nlp: ニュース記事を集約し OpenAI（gpt-4o-mini など）で銘柄別センチメントを算出して ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して market_regime を判定
  - API 呼び出しはリトライ/フェイルセーフ実装あり（429/タイムアウト/5xx 等）
- ツール
  - 設定ウィザード（config_setup）: 対話的に .env を生成
  - 設定検証（validate_config）: .env と config/*.yaml の基本チェック
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順
--------------
1. Python（推奨: 3.10+）を用意します。

2. 必要な Python パッケージをインストールします（例）:
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（validate_config の YAML 検証に使用）
   例:
     pip install duckdb psutil openai PyYAML

   注: requirements.txt は本リポジトリに含まれていないため、実環境に合わせて依存を管理してください。

3. ディレクトリ作成（初回のみ）:
   デフォルトではデータ・ログがプロジェクト内の data/ と logs/ に書き込まれます。必要に応じて作成してください（logging_setup.setup_logging は自動で作成を試みます）。
     mkdir -p data logs

4. 環境変数設定:
   - 推奨: 対話式で .env を作る
       python -m kabusys.config_setup
     このウィザードは .env（デフォルト: プロジェクトルート/.env）を生成します。

   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使用する場合）
   - 実行環境:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading: MockBrokerClient を使用し、ペーパートレード用 DB (data/paper_trading.db) に保存
       - live: 本番動作 — 注意深く設定すること
   - DB パスのデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

5. 設定検証（任意だが推奨）:
     python -m kabusys.validate_config
   --strict オプションで警告も失敗扱いにできます:
     python -m kabusys.validate_config --strict

使い方
------
- 実行エンジン（ExecutionEngine）を起動:
  - 本番（設定に応じて）/ ペーパートレードを自動判定します（KABUSYS_ENV）。
    python -m kabusys.run_execution

  - ペーパートレードで起動する例:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  挙動の概要:
    - 起動時にプロセス優先度を "high" にセット（utils.process_priority.set_process_priority）
    - SQLite・DuckDB に接続
    - BrokerClientFactory でブローカクライアントを取得（paper_trading なら MockBrokerClient）
    - エンジンは別スレッドで実行され、data/stop_requested.flag を検知すると停止します
    - PID は data/execution.pid に書き込まれます

- 監視ループを起動（Monitoring）:
    python -m kabusys.run_monitoring

  仕様:
    - デフォルトのポーリング間隔は 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を変更可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は Settings.sqlite_path（環境を問わず本番 sqlite_path）を使用して監視ログを書き込みます
    - data/stop_requested.flag を検出すると監視ループを終了します

- 設定ウィザード（.env 生成）:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    オプション --db で DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 機能の利用:
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。
  - API 呼び出しはリトライやパースの堅牢化が施されていますが、API キーの設定と料金管理には注意してください。

運用上の注意
-------------
- Kill Switch:
  - RiskMonitor が重大な条件（ドローダウン超過やポジション上限超）を満たすと KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine はこのフラグを監視して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動でクリアされるため）。本番では 0 を推奨します。
  - 手動で kill.flag を削除する場合:
      rm data/kill.flag
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します（安全停止用）。
- ログ:
  - デフォルトのログディレクトリは logs/
  - ログは日次ローテーション（30 日保持）されます（kabusys.utils.logging_setup.setup_logging）

環境変数一覧（抜粋）
------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行制御:
  - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
  - LOG_DIR — ログ保存先（デフォルト: logs）
- DB 構成:
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- AI:
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- 監視:
  - MONITOR_POLL_INTERVAL — 監視ポーリング秒（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

ディレクトリ構成（主要ファイル）
----------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py                  — パッケージ定義（バージョン等）
  - config.py                    — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py              — .env 作成ウィザード（対話式）
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 株数決定・資金配分・丸めロジック
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py          — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py      — 将来リターン・IC 計算等
  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py            — SQLite テーブル初期化・永続化層
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — 発注ログ監視（存在）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 管理
    - monitoring_engine.py        — 各 Monitor を束ねるループ
    - alert_manager.py            — （存在想定）アラート送信
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/monitoring_db.py   — DB スキーマ初期化とマイグレーション（列追加対応）
  - その他: execution/*, data/*（各責務の実装モジュールが存在）

追加メモ
--------
- DB マイグレーション: monitoring_db.init_monitoring_db() は既存の DB に対して冪等にテーブルを作成し、必要に応じて列を追加する簡易マイグレーション処理を行います（例: trade_logs に latency_ms カラム追加など）。
- テストとモック: AI 呼び出し等は内部で分離されており、テスト時には該当関数をパッチして差し替えることが想定されています（例: unittest.mock.patch）。
- セキュリティ: .env は決して Git にコミットしないでください（config_setup のヘッダにも注記あり）。

問い合わせ / 開発メモ
-------------------
- 開発者はまず .env を config_setup で準備し、validate_config でチェックしてから run_monitoring / run_execution を起動してください。
- 本 README はコードベース（src/kabusys）を元に作成しています。さらに詳しい設計書（PortfolioConstruction.md 等）があれば参照してください。

以上。