# KabuSys — 日本株自動売買システム

このリポジトリは日本株を対象とした自動売買システムのコードベースです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 検証、LLM を用いたニュースセンチメント解析等のコンポーネントを含みます。

以下は本プロジェクトの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 環境変数（主な設定項目）
- 制御ファイル（停止・Kill Flag 等）
- ディレクトリ構成
- 開発者向けメモ

---

プロジェクト概要
- KabuSys は、DuckDB / SQLite をバックエンドに用いる日本株向け自動売買フレームワークです。
- 収集済みの時系列データや財務データを DuckDB で解析し、ファクター計算、ポートフォリオ構築、発注ロジックを提供します。
- 発注部分は実運用（live）・ペーパートレード（paper_trading）・開発（development）モードを切り替え可能で、Paper Trading は本番 DB と分離して動作します。
- 監視コンポーネントはシステム稼働状況、滞留注文、ドローダウン等を監視し、必要に応じて kill.flag を生成して ExecutionEngine を安全に停止します。
- OpenAI を利用したニュース NLP（センチメント）および市場レジーム判定モジュールを備えます（APIキー必須）。

---

主な機能一覧
- データ解析 / 研究
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC 等の統計解析
- ポートフォリオ構築
  - シグナル集約、候補選定、等重・スコア重み付け
  - ポジションサイズ計算（リスクベース、単元株丸め、利用可能資金に基づくスケール）
  - セクター上限適用、レジーム乗数
- 発注・実行エンジン
  - BrokerClientFactory により実環境／Mock を切り替え（KABUSYS_ENV）
  - RiskManager / OrderManager / Reconciler 等
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor: 注文ログの異常検出（滞留、約定異常など）
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - MonitoringEngine: 各モニタのポーリングとアラート制御
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
- AI/LLM 機能
  - ニュースセンチメント（OpenAI）を用いた ai_scores の書き込み
  - マクロニュース + ma200 を使った市場レジーム判定
  - API 呼び出しはリトライ / フェイルセーフ設計
- ユーティリティ
  - ログ設定ユーティリティ（console + 日次ローテーションファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - .env 向けウィザード（interactive）と設定検証 CLI
- ツール
  - Paper Trading 検証レポート出力スクリプト（注文成功率、レイテンシ、稼働率評価）

---

セットアップ手順（ローカル）
- 前提
  - Python 3.9 以上を推奨（コードは型ヒントに Python 3.9+ を想定）
  - システムに DuckDB／psutil などの依存があるため pip でインストールします

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他の依存パッケージを追加してください）

   ※ requirements.txt が無い場合は上記パッケージを目安にインストールしてください。

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 生成した .env をレビューし、必須項目（下記参照）を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数が未設定の場合はエラーになります。--strict を付与すると警告も失敗扱いになります。

6. DB／データディレクトリ
   - デフォルトでは `data/` に DuckDB (`data/kabusys.duckdb`) と監視用 SQLite (`data/monitoring.db`) を使用します。別パスを使う場合は .env で `DUCKDB_PATH` / `SQLITE_PATH` を上書きしてください。
   - Paper Trading の DB は分離され `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用します。

---

使い方（主要スクリプト / CLI）
- 実行時スクリプト（モジュールとして実行可能）
  - 監視ループを起動（SystemMonitor を定期実行）
    - python -m kabusys.run_monitoring
    - 環境変数: MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト: 60）
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず）

  - ExecutionEngine を起動（発注エンジン）
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 sqlite に記録します
    - 実行中に `data/stop_requested.flag` が作られると安全に停止します

  - .env ウィザード（対話式）
    - python -m kabusys.config_setup

  - 設定検証
    - python -m kabusys.validate_config
    - --strict を付けると警告を FAIL 扱いします

  - Paper Trading 検証レポート
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- ライブラリ的に使う（Python API）
  - 研究モジュール例:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - conn: duckdb connection を渡して使用
  - AI スコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

- ロギング
  - setup_logging(app_name="execution") を各起動スクリプトで呼び出します。ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。

---

主な環境変数（要点）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading: MockBrokerClient を使い発注は分離 DB に記録
    - live: 本番
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Flag パス（デフォルト: data/kill.flag）
- ログ / 動作
  - LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効）
- OpenAI
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI モジュールを使う場合）

詳しいプロパティは kabusys.config.Settings クラスで確認できます。

---

制御ファイル（停止・Kill Flag 等）
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルを検知すると自プロセスを終了します（外部から停止させたい場合に使用）。
- data/kill.flag
  - KillSwitch が危険状態（例: ドローダウン閾値超過・ポジション上限超過）を検出したときに書き込むファイルです。ExecutionEngine はこれを見て停止します。
  - 起動時に自動クリア（KILL_FLAG_CLEAR_ON_START=1）を設定することもできますが、本番では 0 を推奨します。
- data/execution.pid
  - 実行中の ExecutionEngine が PID を書き込みます。SystemMonitor は PID ファイル存在とプロセス存続を確認します。

---

ディレクトリ構成（主要ファイル）
（リポジトリルート /src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数／設定読み込み（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（console + file）
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成・永続化層（MonitoringDB）
    - system_monitor.py       — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - trade_monitor.py        — （注文監視ロジック）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — KillSwitch（kill.flag 書き込み）
    - monitoring_engine.py    — 各 Monitor を束ねるランナー
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py     — ExecutionEngine（セッション開始 / 発注ループ）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文 / 取引ログ永続化
    - reconciler.py           — 注文状態整合処理
    - broker_factory.py       — Broker クライアント生成（Mock / 実クライアント 切替）
    - risk_manager.py         — 発注リスク制御
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・単元丸め・aggregate cap
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 計算
    - feature_exploration.py  — forward returns / IC / rank / summary
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py      — ma200 + macro sentiment でレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力

（上記は主要モジュールの抜粋です。細かな実装ファイルはリポジトリ内を参照してください）

---

開発者向けメモ / 注意点
- Paper Trading は本番 DB と完全に分離される設計です。KABUSYS_ENV=paper_trading を利用すると `PAPER_TRADING_SQLITE_PATH` を使用します。
- OpenAI などの外部 API 呼び出しはリトライ・フェイルセーフ実装になっていますが、APIキーの管理とコストに注意してください。
- ロギングは各起動スクリプトから setup_logging を呼んで統一して扱います。ログファイルは logs/ 以下に日次ローテーションで保存されます。
- テスト時は API 呼び出しや時刻参照をモックすることが設計文書で想定されています（関数を差し替えてテスト可能）。
- MonitoringDB のマイグレーションは init_monitoring_db() 内で簡単な ALTER 等を実行します。運用時の DB バージョン管理は注意して行ってください。
- Process priority / CPU affinity はプラットフォーム依存（psutil 使用）で、権限が不足すると設定できない場合があります。ログに警告が出ます。

---

よく使うコマンド例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 発注エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

サポート / 貢献
- バグ報告や改善提案は Issue を作成してください。
- 機能追加やリファクタリングは Pull Request でお願いします。テストやドキュメントの追加を歓迎します。

---

以上がプロジェクトの README です。必要があれば、利用の流れ（初回起動の具体的手順）、詳細な環境変数一覧（すべて列挙）や運用手順書（デプロイ / 再起動 / ログローテーション運用等）を追記します。どの項目を詳しく書くか指示してください。