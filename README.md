README — KabuSys（日本株自動売買フレームワーク）
================================

概要
---
KabuSys は日本株の自動売買を目的としたモジュール型フレームワークです。  
戦略・ポートフォリオ構築、発注（ExecutionEngine）、監視（Monitoring）、研究（Research）、AI 補助（ニュース NLP / レジーム判定）などの機能を分離して提供します。  
設計方針として「本番データと研究処理の分離」「ルックアヘッドバイアスの排除」「失敗に対するフェイルセーフ」を重視しています。

主な特徴
---
- ExecutionEngine：ブローカークライアント経由で注文を管理。KABUSYS_ENV=paper_trading 時は MockBroker を使用し、本番 DB とは別の data/paper_trading.db に記録。
- Monitoring：システム（CPU/メモリ/ディスク）、データ鮮度、取引ログ、リスク（ドローダウン・ポジション上限）を監視。Kill Switch（data/kill.flag）で ExecutionEngine を停止可能。
- Portfolio モジュール：候補選定、重み計算（等金額/スコア加重）、セクター上限適用、ポジションサイズ計算（単元株丸め・集約キャップ適用）を純粋関数として提供。
- Research：DuckDB を用いたファクター計算（モメンタム/バリュー/ボラティリティ）、将来リターン・IC 計算、特徴量サマリー等の研究ユーティリティ。
- AI（OpenAI）統合：ニュース記事のセンチメントスコアリング（news_nlp）、マクロ + ETF MA200 を組み合わせた市場レジーム判定（regime_detector）。
- ユーティリティ：ログ設定の共通化、プロセス優先度・CPU affinity 設定、.env ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）。
- 分離された永続層：監視用 SQLite（monitoring_db）、分析用 DuckDB（kabusys.duckdb）、ペーパートレード用 SQLite（paper_trading.db）。

セットアップ手順
---
前提
- Python 3.10 以上（本コードは型ヒントに「|」を使用）
- SQLite は標準ライブラリで利用可能
- DuckDB, psutil, OpenAI SDK などを使用（下記参照）

インストール（例）
1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）YAML 検証に PyYAML が必要: pip install pyyaml

（プロジェクト配布に requirements.txt がある場合はそれを利用してください：pip install -r requirements.txt）

環境変数設定
- 本システムは .env ファイルや環境変数から設定を読み込みます。必須の環境変数:
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
- その他の重要な環境変数（主なもの）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- .env 作成支援:
  - python -m kabusys.config_setup を実行すると対話式で .env を生成できます。

設定検証
- 起動前に設定検証を実行:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります。

使い方（主なコマンド）
---
- Execution Engine（取引エンジン）を起動:
  - python -m kabusys.run_execution
  - 説明: 起動時にプロセス優先度を "high" に設定。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient で動作します。data/stop_requested.flag が存在すると起動を中止します。
  - 実行中に停止させたい場合は監視側から書き込まれる data/kill.flag（KillSwitch）が使用されます。外部から停止を要求するには data/stop_requested.flag を作成できます。

- Monitoring（監視ループ）を起動:
  - python -m kabusys.run_monitoring
  - 説明: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能。監視は常に（環境に関係なく）本番 sqlite_path を使用して監視ログを保存します。

- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定、もしくは PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。

- AI モジュールの利用（プログラムから呼び出す例）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")

手動での Kill / Stop
- 停止フラグ（監視/実行プロセス共通）
  - data/stop_requested.flag: run_execution/run_monitoring の外部停止トリガーとして使用
  - data/kill.flag: KillSwitch が条件を満たすと書き込み、ExecutionEngine を停止させるために利用

デフォルトファイル配置・ログ
- データベース（デフォルト）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db（ペーパートレード用）
- ログディレクトリ（デフォルト）
  - logs/（各アプリケーションごとに日次ローテートされたログファイルが生成されます。例: logs/execution.log, logs/monitoring.log）

ディレクトリ構成（主なファイルと説明）
---
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- config_setup.py
  - .env を対話式で作成するウィザード
- validate_config.py
  - .env と config/*.yaml の検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading 対応）

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL）

- utils/
  - logging_setup.py: ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
  - process_priority.py: 優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: 監視用 SQLite 永続化層
  - system_monitor.py: システム状態 / データ鮮度監視
  - trade_monitor.py: （取引ログ監視 — 実装ファイルあり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - kill_switch.py: Kill Switch 実装
  - alert_manager.py: （アラート送信管理 — 実装ファイルあり）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
  - （発注ロジック・ブローカー抽象化・リスク制御等）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・集約キャップ
  - risk_adjustment.py: セクターキャップ・レジーム乗数
  - __init__.py: API エクスポート

- research/
  - factor_research.py: momentum / value / volatility 計算
  - feature_exploration.py: 将来リターン, IC, 統計サマリー
  - __init__.py: API エクスポート

- ai/
  - news_nlp.py: ニュース記事を OpenAI でスコアリングして ai_scores テーブルへ書込
  - regime_detector.py: ETF + マクロニュース → 市場レジーム判定
  - __init__.py

- data/（実行時に生成される想定）
  - *.db, *.flag, *.pid

- tools/
  - paper_verification_report.py: ペーパートレード運用の検証レポート生成スクリプト

注意事項 / 運用上のヒント
---
- 本番起動時は KABUSYS_ENV=live の設定に注意し、LINE 通知・Kill Switch 設定などを十分に確認してください（validate_config.py に live 時のガードチェックがあります）。
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも記載あり）。
- OpenAI を使用する機能は API キーが必要で、コストが発生します。API 呼び出しはリトライ・フェイルセーフを組み込んでいますが、運用コストに注意してください。
- ペーパートレード（paper_trading）モードは本番 DB と分離されます。検証や開発では paper_trading を推奨します。
- monitoring はデフォルトで本番 sqlite_path を使用します（run_monitoring の実装に準拠）。環境に関係なく監視対象 DB を参照する点に注意。

開発者向け
---
- 研究用の関数群（research/*）は DuckDB 接続を受け取り副作用なしに計算結果を返します。ローカルで DuckDB を準備して分析ワークフローを試せます。
- AI 周りのテストでは API 呼び出し関数をモックできる設計になっています（テスト用に _call_openai_api を patch）。

ライセンス・貢献
---
- 本リポジトリにライセンスファイルが含まれていない場合は、運用前にライセンス方針を決定してください。貢献する際は PR・Issue を利用してください（組織の運用方針に従ってください）。

お問い合わせ
---
開発・運用に関する質問や改善提案はリポジトリ内の Issue に投稿してください。README に不足している実行例・環境変数の詳細をドキュメント化していくと運用が楽になります。

以上。必要があれば、セットアップ手順を Docker 化した例や systemd サービスの起動例（run_execution/run_monitoring のサービス化）を追加で作成します。どのような形式（例: systemd ユニット例、Dockerfile、requirements.txt）を希望しますか？