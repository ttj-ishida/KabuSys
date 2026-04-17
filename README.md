# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・研究プラットフォームです。本リポジトリはシグナル生成、ポートフォリオ構築、発注エンジン、監視（Monitoring）、AIによるニュースセンチメント評価などのコンポーネントを含みます。

以下はこのコードベースの概要、機能、セットアップ・起動手順、各種ツールの使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 自動売買のコア機能（ExecutionEngine、OrderManager、RiskManager、Reconciler 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch による自動停止
- Portfolio Construction（銘柄選定、重み計算、ポジションサイズ算出等）
- リサーチ用モジュール（ファクター計算、特徴量解析、IC 計算）
- AI モジュール（ニュースセンチメント評価、マーケットレジーム判定） — OpenAI API を利用
- Paper Trading（本番 DB と分離して動作するモード）と実行環境の切り替え
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

---

## 主な機能一覧

- Execution
  - ExecutionEngine を用いた発注の実行・セッション管理
  - BrokerClientFactory による実環境 / モック（paper_trading）切替
  - RiskManager による発注制約（最大ポジション率・利用率・サーキットブレーカー等）
  - OrderRepository / OrderManager による注文保管・管理

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 監視結果に基づく停止フラグ (data/kill.flag) 書き込み
  - MonitoringEngine: 各 Monitor の統合ポーリング、アラート送信フック

- Portfolio
  - 銘柄候補選定（スコア順）、等配分 / スコア配分の重み計算
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分、aggregate cap）

- Research
  - momentum / value / volatility 等のファクター計算（DuckDB 上で SQL による実装）
  - 将来リターン計算、IC（Spearman ランク相関）計算、統計サマリー

- AI
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- ユーティリティ / ツール
  - config_setup: .env を対話形式で生成・更新するウィザード
  - validate_config: .env と config/*.yaml の整合チェック（--strict あり）
  - tools.paper_verification_report: Paper Trading の性能レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 依存パッケージ（少なくとも以下をインストールしてください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML のパースを行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. ディレクトリ作成
   - data ディレクトリを作成しておくこと（デフォルト DB 等を置く場所）
     - mkdir -p data

4. .env の作成
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成（.env は決してリポジトリにコミットしないこと）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります

注意:
- Monitoring は run_monitoring.py 実行時に指定の SQLite パス（Settings.sqlite_path）を使用します。run_monitoring は環境にかかわらず本番 sqlite_path を使う旨に注意してください。
- Execution は KABUSYS_ENV により paper_trading モード時は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して DB を分離します。

---

## 必須 / 主要な環境変数

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）

- データベース・ログ
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/...）

- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY: AI モジュールを使う場合に必須

- 監視 / Kill Switch
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか: "1" でクリア）

- 監視ポーリング間隔（run_monitoring 用）
  - MONITOR_POLL_INTERVAL（秒, デフォルト: 60）。0 以下や不正値は無視されデフォルトにフォールバックします。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジンの起動（デフォルト: Settings.env に依存）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中は data/execution.pid に PID を書き込み、stop フラグで停止できます

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）
    - data/stop_requested.flag を作成するとループは終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db を指定して PAPER_TRADING_SQLITE_PATH を上書き可能

- AI モジュールの呼び出し（コードから）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します（未設定だと例外）

- その他ユーティリティ
  - MonitoringEngine を用いた単発実行 / テストに run_once を使う等、各クラスはユニットテストしやすい設計になっています。

---

## Kill / Stop の仕組み

- 停止フラグ（外部からの停止要求）
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検出して停止します（run_execution は起動時に既に存在している場合は起動しません）。

- Kill Switch（自動停止）
  - monitoring 側の条件（ドローダウン超過やポジション上限超過）で KillSwitch が data/kill.flag を作成します。ExecutionEngine はこのフラグを検出して停止できます（Settings.kill_flag_clear_on_start を使って起動時に自動クリアも可能だが、本番では 0 を推奨）。

- PID ファイル
  - Execution 側は data/execution.pid に PID を書き込みます。SystemMonitor はこの PID ファイルの存在・プロセス生存をチェックし、stale PID を検出すると削除してリスクログに記録します。

---

## トラブルシューティング（簡易）

- OpenAI API キーがない / 未設定
  - AI モジュールを呼ぶと ValueError が出ます。OPENAI_API_KEY または関数引数でキーを渡してください。

- DuckDB / SQLite ファイルが見つからない
  - 設定検証で警告が出ます。必要なら作成されたり、config_setup で適切なパスを設定してください。

- psutil によるプロセス優先度設定でアクセス拒否
  - 管理者権限が必要な場合があります。失敗時は警告が出て処理は継続します。

- YAML 検証がスキップされる
  - PyYAML が未インストールの場合は config/*.yaml の検証をスキップします（validate_config で警告が出ます）。

---

## ディレクトリ構成（主要ファイル/モジュール）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン、エクスポート）
  - config.py — Settings クラス（環境変数／.env 自動ロード、検証用ユーティリティ）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前チェック CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — raw_news を LLM に送って銘柄別センチメントを ai_scores に書き込む
    - regime_detector.py — MA とマクロニュースを合成して市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/Data Freshness 監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor の統合ポーリング
    - alert_manager.py — （アラート送信の抽象層、実装は別途）

  - execution/ (発注関連、サンプル実装があることを前提)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - order_record.py
    （※これらのファイルはコードベースに含まれており、発注ロジックを実装）

  - portfolio/
    - portfolio_builder.py — 銘柄選定・等重/スコア配分
    - position_sizing.py — 株数決定・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — momentum/value/volatility のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー

  - data/ （実行時に生成／使用する）
    - デフォルト DB: data/kabusys.duckdb
    - 監視 DB: data/monitoring.db
    - paper trading DB: data/paper_trading.db
    - フラグ / PID: data/kill.flag, data/stop_requested.flag, data/execution.pid

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - その他ユーティリティ群

---

## 開発・貢献メモ

- .env をリポジトリにコミットしないでください（機密情報を含みます）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- AI 関連の API 呼び出し部はテスト容易性を考慮してラップ／差し替え可能になっています（unittest.mock.patch などで _call_openai_api をモック可能）。
- データベーススキーマのマイグレーションは monitoring_db.init_monitoring_db 内で簡易的に行われます（既存カラムチェック → ALTER）。

---

必要であれば README に入れるサンプル .env テンプレートや、より詳細な実行例（systemd ユニット、Docker Compose、CI ワークフロー）も作成します。どの部分を拡張しますか？