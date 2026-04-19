README
======

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは以下の主要機能を含むモジュール群を提供します。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク制御の実行基盤（run_execution.py）
- 監視（Monitoring）: システム状態・注文状態・リスクを定期モニタリングしてアラート／Kill Switch を制御（run_monitoring.py、monitoring/*）
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算（portfolio/*）
- リサーチ: ファクター計算・特徴量解析（research/*）
- AI 支援: ニュースの NLP スコアリング、レジーム判定（ai/*）
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度など（utils/*）
- 運用ツール: ペーパートレード検証レポート生成スクリプト（tools/*）

主な機能
--------
- 設定管理（.env 自動読み込み / Settings クラス）
- 実行環境分離: KABUSYS_ENV による development / paper_trading / live 切替
  - paper_trading 時は MockBroker を使い、専用 SQLite（data/paper_trading.db）に記録
- 監視ループ: CPU・メモリ・ディスク・プロセス稼働・データ鮮度の定期チェック
- Kill Switch: ドローダウンやポジション上限で stop flag（data/kill.flag）を作成し ExecutionEngine を止められる
- AI 統合: OpenAI を使ったニュースセンチメント集約（バッチ・リトライ・バリデーション実装）
- ポートフォリオ構築: 等配分／スコア配分／リスクベース配分、セクターキャップ、レジーム乗数など
- レポート: ペーパートレードのパフォーマンス／稼働率／レイテンシ等の検証レポート生成

前提条件
--------
- Python 3.9+
- 外部ライブラリ（主なもの）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（設定 YAML 検証を使う場合）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（kabuステーション API 等、実運用時）

インストール / セットアップ
--------------------------
1. リポジトリをクローンしてワークディレクトリに入る。

2. 仮想環境を作成して有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（requirements.txt がある場合はそちらを利用）:
   - pip install duckdb psutil openai
   - PyYAML を入れると config 検証で YAML の中身チェックが走る: pip install pyyaml

環境変数（.env）の準備
---------------------
このプロジェクトは .env ファイル（または環境変数）から設定を読み込みます。自動読み込みはデフォルトで有効です。

推奨手順（対話ウィザード）:
- python -m kabusys.config_setup
  - 対話形式で .env を作成できます（.env は絶対に Git にコミットしないでください）。

主要な必須環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — AI 機能利用時に必要

DB / ログのデフォルトパス
- DuckDB: data/kabusys.duckdb
- SQLite (監視): data/monitoring.db
- Paper trading SQLite: data/paper_trading.db (KABUSYS_ENV=paper_trading 時に使用)
- ログ: logs/<app_name>.log（日次ローテーション、30日分保持）

設定検証
--------
作成した .env と config/*.yaml を起動前に検証できます:
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります

使い方（主要スクリプト）
-----------------------

1) Execution Engine を起動（発注エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中、停止したい場合は data/stop_requested.flag を作成または monitoring の Kill Switch を発動してください。
  - 実行時に data/execution.pid が作成されます（pid ファイルパスは Settings で変更可能）。

2) Monitoring を起動（監視ループ）
- python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番の SQLite（Settings.sqlite_path）を利用します（環境にかかわらず同じパスを使う設計）。
  - 監視は system / trade / risk の各 Monitor を順に呼び出し、Kill Switch やアラート送信を行います。
  - 停止する際はプロジェクトルートの data/stop_requested.flag を作成してください（監視ループは検知して安全に終了します）。

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db を指定して上書き可能）
  - 検証指標: 稼働率、注文成功率（Fill Rate）、送信率、P95 レイテンシなど
  - しきい値はソース内定数で調整可能

4) AI 機能（プログラムからの呼び出し例）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - AI 呼び出しで 429 / ネットワーク断 / 5xx は指数バックオフでリトライします。API 失敗時は安全側フォールバック（例: macro_sentiment=0）します

運用上の注意点
--------------
- Kill Switch:
  - risk_monitor が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動中に kill.flag を検出すると停止処理を行います。
  - KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動クリアされますが、本番では 0 を推奨します。
- Paper Trading と Live は DB を分離しているため、paper_trading モードでの検証は本番データに影響を与えません。
- ログ:
  - ロギングは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソールのみ出力されます。
- プロセス優先度:
  - 実行スクリプトは起動時に set_process_priority("high") を呼び出します。権限がない場合は警告が出てスキップされます。

ディレクトリ構成
----------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数読み込み / Settings クラス（.env 自動ロード機能含む）
- config_setup.py — .env 作成ウィザード（対話式）
- validate_config.py — 設定検証 CLI

- run_execution.py — ExecutionEngine 起動用スクリプト
- run_monitoring.py — Monitoring ポーリングループ起動スクリプト

- utils/
  - logging_setup.py — 統一ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite 監視 DB 永続化レイヤー
  - system_monitor.py — CPU / メモリ / データ鮮度 / プロセス監視
  - trade_monitor.py — （注文関連の監視、ファイルに含まれます）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各 Monitor を束ねるランナー
  - alert_manager.py — （LINE などへの通知管理：実装を参照）
- execution/ — Execution エンジン関連（broker, order_manager, reconciler, risk_manager 等）
- portfolio/ — ポートフォリオ構築ロジック（builder / position_sizing / risk_adjustment）
- research/ — ファクター計算・特徴量解析モジュール
- ai/
  - news_nlp.py — ニュースを LLM でスコア化するロジック
  - regime_detector.py — マクロ + MA によるレジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

（※実際のファイル全体は src/kabusys 以下を参照してください）

開発者向けメモ
--------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト等で利用）。
- DuckDB 接続は分析系処理（research, ai）で使用します。prices_daily / raw_financials / raw_news 等のテーブルを利用する想定です。
- 監視 DB（SQLite）は init_monitoring_db() で必要なテーブル・マイグレーションを作成します（冪等）。
- AI 呼び出し部は JSON Mode を利用し、レスポンスの堅牢なバリデーション・クリップ・再試行を実装しています。

トラブルシューティング
----------------------
- 設定チェックでエラーが出る場合:
  - python -m kabusys.validate_config を実行し表示されるエラー／警告を確認してください。
- .env が正しく読み込まれない場合:
  - プロジェクトルートの場所、.env の存在、KABUSYS_DISABLE_AUTO_ENV_LOAD の有無を確認してください。
- OpenAI API 呼び出しに失敗する場合:
  - OPENAI_API_KEY の設定、ネットワーク、API レート制限に注意。ログにリトライ情報が出力されます。

ライセンス / 免責
-----------------
（ここにライセンス情報を記載してください。例: MIT License）

以上。README に不足している具体的な手順や追加で説明してほしい箇所があれば教えてください。