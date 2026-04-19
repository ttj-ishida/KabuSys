KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ／実行スクリプト群です。  
主な目的は以下のとおりです。

- 戦略（ファクター計算・ポートフォリオ構築）と発注ロジックの分離  
- 実行エンジン（ExecutionEngine）による発注・リスク管理の運用  
- 監視（Monitoring）によるプロセス・データ・注文状態の常時チェックと Kill Switch  
- 研究用モジュール（DuckDB を用いたファクター計算、特徴量解析）  
- AI 補助（ニュースの NLP スコアリング、レジーム判定）  
- ペーパートレード用 DB の分離、検証用レポート出力ツール

機能一覧
--------
- Execution
  - 実際のブローカークライアントまたはペーパートレード用 MockBrokerClient の切替
  - 注文管理、リスク管理、リコンシリエーション
  - PID ファイル管理・停止フラグ対応
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）監視とデータ鮮度チェック
  - 注文ログ・滞留注文・約定異常の検出
  - リスク監視（ドローダウン・ポジション上限）と Kill Switch（data/kill.flag）
  - 通知（AlertManager 経由）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重／スコア加重の重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元丸め、集約キャップ）
- Research
  - DuckDB を用いたファクター計算（Momentum, Volatility, Value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - ニュース記事のセンチメントスコアリング（gpt-4o-mini 想定）
  - マクロニュース + ETF MA を使った市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト
- 設定 / ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ロギング統一設定、プロセス優先度設定ユーティリティ

セットアップ手順
----------------
前提: Python 3.9+（実際の要件はプロジェクトの pyproject.toml 等を参照してください）

1. リポジトリをクローンして、作業ディレクトリに移動
   - プロジェクトルートに src/ 配下がある前提です。

2. 必要パッケージをインストール
   - 代表的な依存: duckdb, psutil, openai, pyyaml（YAML 検証用）
   - 例: pip install -r requirements.txt（requirements.txt がある場合）
   - または個別:
     - pip install duckdb psutil openai PyYAML

3. データ・ログディレクトリの作成（通常は自動作成されますが手動で用意しても良い）
   - data/（SQLite / PID / フラグファイルを格納）
   - logs/（ログ出力先）

4. 環境変数の設定
   - .env を作るには対話式ウィザードを利用すると簡単です（下記参照）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KILL_FLAG_CLEAR_ON_START (0/1)
   - .env の自動読み込み:
     - プロジェクトルートの .env / .env.local を自動でロード（OS 環境変数優先）
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザード後に .env が生成されます（.env は Git にコミットしないでください）。

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

使い方
------
主な実行コマンド（プロジェクトルートで実行）:

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 仕様:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB とは分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid（デフォルト）に PID を書きます。停止時はフラグまたは外部からの停止処理で終了します。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 仕様:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を設定可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を参照して監視テーブルを初期化します（監視ログは常に指定の SQLite に記録）。
    - 停止は data/stop_requested.flag の作成で行います（run_execution と共通のフラグを使用）。

- 設定検証
  - python -m kabusys.validate_config
  - 事前に .env を作成し、設定に不備がないか確認します。

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - ニューススコアリング: kabusys.ai.score_news（モジュール関数）
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - モデルは gpt-4o-mini を想定、リトライ・バックオフ等を組み込んであります

運用上の注意
-------------
- KABUSYS_ENV のモード:
  - development: ローカル開発・テスト（発注なしの想定）
  - paper_trading: ペーパートレード（MockBrokerClient・別 DB）
  - live: 本番（実際に発注）
- Kill Switch:
  - RiskMonitor やその他アラート条件で KillSwitch が data/kill.flag を作成すると ExecutionEngine に停止シグナルを与えます。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされますが、本番では 0 を推奨します。
- ログ:
  - デフォルトは logs/ にアプリ別ログ（execution.log, monitoring.log など）を日次ローテーションで保存します。
  - LOG_DIR 環境変数で変更可。ログ設定は kabusys.utils.logging_setup.setup_logging で共通化されています。
- DB:
  - DuckDB は分析用（デフォルト data/kabusys.duckdb）
  - SQLite は監視ログ（デフォルト data/monitoring.db）、ペーパートレードは別ファイル（data/paper_trading.db）
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼んで優先度を上げようとしますが、権限不足時は警告を出してスキップします。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数／.env ロードと Settings クラス
- config_setup.py               — .env 対話式ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — Monitoring ポーリング起動スクリプト

サブパッケージ（主なもの）
- ai/
  - news_nlp.py                  — ニュース NLP スコアリング（OpenAI 呼び出し）
  - regime_detector.py           — レジーム判定
- monitoring/
  - monitoring_db.py             — SQLite 監視 DB レイヤ
  - system_monitor.py            — システム状態・データ鮮度監視
  - trade_monitor.py             — 注文ログ・滞留注文監視（コード内にあり）
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag の作成 / 管理
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - alert_manager.py             — アラート通知管理（実装に応じて）
- execution/
  - execution_engine.py          — ExecutionEngine 本体
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 株数計算・集約キャップ
  - risk_adjustment.py           — セクターキャップ・レジーム乗数
- research/
  - factor_research.py           — ファクター算出（Momentum/Value/Volatility）
  - feature_exploration.py       — 将来リターン・IC・統計関数
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py             — ログ設定ユーティリティ
  - process_priority.py          — プロセス優先度 / CPU affinity
  - その他ユーティリティ群

補足・開発者向け情報
--------------------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト・ローカル実行では KABUSYS_ENV=paper_trading を使うと実際のブローカーに影響を与えず試験できます（MockBrokerClient を使用）。
- AI 機能を利用する場合は OPENAI_API_KEY を環境変数で与えてください。API 呼び出しはリトライと検証を行い、失敗時は安全側のフォールバックが働きます。
- 監視ループ・エンジンは例外を捕捉して続行する設計になっていますが、重大な不整合があればログ・通知で対応してください。

ライセンスや貢献
----------------
この README はコードベースに基づく簡易ドキュメントです。ライセンスや貢献方法はリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

以上が基本的な README です。必要があれば、導入手順の詳細（systemd ユニットファイル例、Docker 化、CI 設定、より詳しい環境変数リスト）を追加で作成します。どの情報を優先して追加しますか？