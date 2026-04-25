KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買プラットフォーム向けユーティリティ群です。  
システム監視・実行エンジン・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）など、運用に必要なコンポーネントを含みます。  
本リポジトリは主に以下を提供します：

- ExecutionEngine（発注実行）起動スクリプト
- Monitoring（システム状態・注文監視 / Kill Switch）
- Paper Trading（ペーパートレード）分離・検証用ツール
- Portfolio 構築、リスク調整、ポジションサイズ計算の純粋関数群
- Research（ファクター計算・特徴量解析）
- AI モジュール：ニュースのセンチメントスコアリング / 市場レジーム判定
- 開発用ユーティリティ：.env ウィザード、設定検証、レポート生成 等

主な機能
--------
- 実行エンジン（run_execution）:
  - 本番 / ペーパートレードを切り替え（KABUSYS_ENV）
  - Broker クライアントの切替、リスク管理、注文管理、照合（reconciler）
  - PID ファイル管理、停止フラグ検出
- 監視（run_monitoring / MonitoringEngine）:
  - システムリソース（CPU/メモリ/ディスク）監視、データ鮮度チェック
  - 注文ログ監視（未処理 / 異常約定）・リスク監視（ドローダウン / ポジション上限）
  - Kill Switch（条件により data/kill.flag を書き込み、Execution を停止）
  - 監視ログは SQLite（monitoring.db）に永続化
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
  - 検証レポート生成ツール（paper_verification_report）
- ポートフォリオ構築:
  - 候補選定、等金額/スコア加重配分、リスクベースの株数決定
  - セクターキャップ、レジーム乗数の適用
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI:
  - raw_news を LLM（OpenAI）でスコア化して ai_scores に書き込み
  - 市場レジーム判定（ETF ma200 乖離 + マクロセンチメント）
- 共通ユーティリティ:
  - ロギングセットアップ（日次ローテート）、プロセス優先度設定、.env ウィザード / 検証

前提条件
--------
- Python 3.9+（型アノテーションで | を使用しているため 3.10+ を想定しているコード箇所もありますが、互換性は環境で確認してください）
- 必要な Python パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML 内容チェックを行う場合に必要）
- SQLite（標準ライブラリで利用可）
- kabuステーション API（実運用での接続には外部 API と認証情報が必要）

セットアップ手順
---------------
1. リポジトリをクローン / 展開
   - 例: git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt があれば pip install -r requirements.txt）

4. 初期データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

環境変数（.env）作成
--------------------
推奨フロー:
- python -m kabusys.config_setup を実行すると対話式に .env を生成・更新できます。

主要な環境変数（必須と推奨）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / 任意:
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading時）
  - LOG_LEVEL — ログレベル（INFO 等）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（本番運用）

注意:
- .env は Git にコミットしないでください（機密情報を含む）。
- KILL_FLAG_CLEAR_ON_START=1 を本番（live）で設定するのは危険です（kill.flag が自動クリアされるため）。

設定検証
--------
設定を起動前にチェックするには:
- python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit(1) になります

実行方法
--------
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - 動作: Settings に従って本番 DB または paper_trading DB を使用。デーモン的に ExecutionEngine をスレッドで動作させ、 data/stop_requested.flag により停止する。
  - ペーパートレードモード: KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは paper_trading 用 DB に保存されます。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に（環境にかかわらず）本番 sqlite_path を使用して監視ログを記録します。
  - 停止: data/stop_requested.flag を作成するとループは安全に終了します。

- .env ウィザード（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ
---
- ログは標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます（kabusys.utils.logging_setup.setup_logging を使用）。
- LOG_DIR 環境変数でログディレクトリを上書きできます。
- LOG_LEVEL でログレベルを設定します（例: INFO、DEBUG）。

停止フラグ / Kill Switch
----------------------
- 停止フラグ:
  - data/stop_requested.flag — run_execution や run_monitoring の外部停止トリガとして利用。存在するとループが終了します。
  - data/execution.pid — ExecutionEngine の PID ファイル（実行管理に使用）
- Kill Switch（自動停止判定）:
  - 条件（ドローダウン超過 / ポジション上限等）が成立すると KillSwitch が data/kill.flag に理由を書き込みます。
  - ExecutionEngine は起動時に kill.flag の存在を検査し、存在する場合は起動を抑止します（本番保護）。設定 KILL_FLAG_CLEAR_ON_START による自動クリアを行うかは設定次第です。

DB 周り
------
- DuckDB: 分析 / リサーチ用（デフォルト data/kabusys.duckdb）
- SQLite:
  - 監視ログ: data/monitoring.db（Settings.sqlite_path）
  - Paper Trading 用: data/paper_trading.db（KABUSYS_ENV=paper_trading 時は専用 DB を使用）
- monitoring_db.init_monitoring_db() により必要テーブルを冪等的に作成します。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py — パッケージ定義・バージョン
- config.py — Settings クラス（環境変数読み込み、自動 .env ロード）
- config_setup.py — .env 作成ウィザード（対話式）
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py — 監視ログ用 SQLite 永続化層
- system_monitor.py — システム状態 / データ鮮度監視
- trade_monitor.py — 注文ログ監視（ファイル参照: 実装あり）
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — Kill Switch フラグ書き込みロジック
- monitoring_engine.py — 複数 Monitor を束ねる実行エンジン
- alert_manager.py — アラート送信管理（実装例）

src/kabusys/execution/
- execution_engine.py — 実行エンジン本体（EngineConfig 等）
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 実行に必要なコンポーネント

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数計算・資金スケール処理
- risk_adjustment.py — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py — raw_news を LLM でスコア化し ai_scores に書き込む
- regime_detector.py — 市場レジーム判定（ETF ma200 + マクロ NLP）

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

src/kabusys/utils/
- logging_setup.py — ログ初期化ユーティリティ
- process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

開発者向けメモ / ベストプラクティス
-----------------------------------
- .env は絶対にコミットしないこと。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨。
- ロギングは setup_logging() で統一して使ってください（主な起動スクリプトはこれを呼び出します）。
- DuckDB や SQLite のパスは環境変数で明示的に設定するとテスト・本番の切り替えが容易です。
- OpenAI 呼び出し部分は API 失敗時にフェイルセーフ（スコア 0.0 やスキップ）となるよう設計されていますが、API キーの管理・レート制限には注意してください。

よく使うコマンド例
-----------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
- （ここにライセンス情報と貢献方法を追記してください）

サポート / 問い合わせ
--------------------
不具合報告や機能要望は Issue を立ててください。設計に関する簡潔な説明を添えると対応が早くなります。

---

この README はコードベースの主要機能と運用上の注意点をまとめたものです。必要に応じて実際の運用環境・運用手順書（運用 runbook）を別途用意してください。