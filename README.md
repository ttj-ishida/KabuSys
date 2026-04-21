# KabuSys

日本株向け自動売買システム（KabuSys）の簡易 README（日本語）

概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成を記載します。

※この README はリポジトリ内のソースコード（src/kabusys）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（ExecutionEngine）とそれを補助する監視・分析ツール群を含む小規模フレームワークです。  
主な要素は以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理・約定照合など実行系ロジック
- Monitoring：システム稼働監視、取引ログ監視、リスク監視、Kill Switch（停止フラグ）
- Research / Portfolio：ファクター計算、ポートフォリオ構築、ポジションサイズ計算
- AI モジュール：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、設定（.env）ウィザード、設定検証
- Tools：Paper Trading 向けの検証レポート生成など

設計方針の例：
- 本番とペーパートレードは DB を明確に分離
- ルックアヘッド（現在時刻参照）に注意した実装（テスト再現性・バイアス防止）
- 外部 API 呼び出し（例: OpenAI）はリトライ処理とバリデーションを実装

---

## 主な機能一覧

- 実行系
  - 発注管理、OrderRepository/OrderManager、RiskManager、Reconciler、ExecutionEngine（スレッドで実行）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper DB に記録
- 監視
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存・データ鮮度の監視
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウン・ポジション上限監視
  - MonitoringEngine：個別モニタを束ね定期実行、KillSwitch による停止フラグ出力
- AI / NLP
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメントスコア（ai_scores へ書き込み）
  - regime_detector: ETF とマクロニュースを使った日次レジーム判定
- Research / Portfolio
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等
  - portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター上限調整
- 管理ユーティリティ
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証（python -m kabusys.validate_config）
  - ログ設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度・CPU affinity 設定
- Tools
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL レポート出力

---

## セットアップ手順（概要）

前提：Python 3.10+ 相当の環境（ソースで | 型注釈を使用しているため 3.10 以上を想定）

1. リポジトリをクローン / ソース配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
   - 任意（YAML 検証など）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML
   - もしパッケージ管理ファイル（requirements.txt）があればそれを使用してください:
     - pip install -r requirements.txt
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 実行後、生成される .env をプロジェクトルートに保存
5. 設定検証
   - python -m kabusys.validate_config
   - 本番前は --strict を使用して警告も FAIL 扱いにできます:
     - python -m kabusys.validate_config --strict
6. DB / ディレクトリの準備
   - デフォルトのパス（必要に応じて .env で変更）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_DIR=logs
   - 必要なディレクトリ（data, logs）を作成するか、実行時に自動作成されます

注意:
- 重要な環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI を使用する機能を実行する場合:
  - OPENAI_API_KEY を .env に設定するか、各関数の引数で渡す

---

## 使い方（主要コマンド）

基本的に各スクリプトはモジュールとして実行できます。

- 設定ウィザード（.env を生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict
- 監視（Monitoring）プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に「本番 sqlite_path」を使用して監視テーブルを操作します
  - 停止方法: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します
- 実行（ExecutionEngine）プロセス起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_db（PAPER_TRADING_SQLITE_PATH）に記録されます
  - 実行中の PID は data/execution.pid に書かれます
  - 停止方法:
    - data/stop_requested.flag を作成すると ExecutionEngine に停止シグナルが送られます
    - Kill Switch は data/kill.flag を書き込み、ExecutionEngine の安全停止をトリガーします
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）

運用に関する注意点:
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）
- ログはデフォルトで logs/<app>.log に日次ローテーションで出力されます
- Execution の本番実行は KABUSYS_ENV=live で行います（十分な確認を行ってください）

---

## 主要な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR: logs
- MONITOR_POLL_INTERVAL: 監視ループの秒数（run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の約定挙動)

詳細は src/kabusys/config.py および config_setup.py を参照してください。

---

## 停止・Kill Switch の仕組み（運用メモ）

- Stop flag:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution 内のループを終了します（外部からの安全停止用）。
- Kill Switch:
  - RiskMonitor 等が基準を満たすと KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのファイルの存在を検知して安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に kill.flag を自動クリアできます（本番では推奨されません）。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートの src/kabusys 以下を中心に記載）

- src/kabusys/
  - __init__.py
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — Monitoring ポーリング起動スクリプト
  - config.py                      — 環境変数 / 設定読み込みロジック（Settings）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py            — 市場レジーム判定（AI + ETF MA）
  - monitoring/
    - monitoring_db.py              — SQLite 永続層（監視ログ）
    - system_monitor.py             — システム状態・データ鮮度監視
    - trade_monitor.py              — 注文ログ監視（存在）
    - risk_monitor.py               — ドローダウン・ポジション数監視
    - monitoring_engine.py          — モニタ群の統合
    - kill_switch.py                — kill.flag の作成 / 管理
    - alert_manager.py              — アラート送信（LINE など、存在）
  - execution/
    - execution_engine.py           — ExecutionEngine（存在）
    - broker_factory.py             — BrokerClient 作成（Mock/実ブローカ）
    - order_manager.py              — 注文管理
    - order_repository.py           — 発注ログ / 永続化
    - reconciler.py                 — 約定照合
    - risk_manager.py               — リスク管理
  - research/
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — IC / 将来リターン / 統計
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 発注株数計算・キャップ調整
    - risk_adjustment.py            — セクター制限・レジーム乗数
  - data/                           — データファイル（data/kabusys.duckdb, monitoring.db 等）
  - utils/
    - logging_setup.py              — ログの統一セットアップ
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
    - その他ユーティリティ

（実際のファイル一覧はリポジトリの内容を参照してください）

---

## 開発・運用における注意点

- 本番モード（KABUSYS_ENV=live）では十分な事前検証、LINE 等の通知設定、Kill Switch の取り扱い確認が必要です。
- OpenAI を利用するモジュールは API キーとコストを伴います。API の失敗やレート制限に対してはリトライとフォールバック（0.0等）を実装していますが、運用時は料金と呼び出し頻度に注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は簡易なマイグレーション（カラム追加）を実行しますが、重要な変更は慎重に検討してください。
- ロギング: logs ディレクトリに日次ローテーションでログが出力されます。ログディレクトリのパーミッションやディスク容量に注意してください。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視起動
  - python -m kabusys.run_monitoring
- 実行起動
  - python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 監視停止（外部から）
  - touch data/stop_requested.flag
- Kill Switch 確認 / クリア
  - ls data/kill.flag
  - rm data/kill.flag

---

必要であれば README に次の項目を追加します（要望に応じて）:
- より詳細な運用手順（systemd / supervisor / cron での起動例）
- 本番導入チェックリスト
- 各コンポーネントのシーケンス図・フロー図
- 単体テスト・統合テストの実行方法

追加したい内容があれば教えてください。