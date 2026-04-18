# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム KabuSys のコア実装です。  
戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI（ニュースセンチメント／レジーム判定）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されます。

- ExecutionEngine
  - ブローカークライアント経由で発注を実行するエンジン
  - paper_trading 環境では MockBroker を使用して本番 DB と分離（data/paper_trading.db）
- Monitoring
  - System / Trade / Risk の各モニタをポーリングして状態を記録・アラートする
  - Kill Switch による停止シグナル発行
- Research / Portfolio
  - ファクター計算、特徴量探索、ポートフォリオ構築（候補選定、重み、ポジションサイズ算出）
- AI
  - ニュースを LLM（OpenAI）でスコアリング（news_nlp）
  - マクロ + ETF MA200 から市場レジームを判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプトなど

設計上の特徴:
- 設定は .env（および .env.local）または環境変数で管理
- DuckDB（分析用）と SQLite（監視・発注ログ）を使用
- ログはコンソール＋日次ローテートファイル（logs/）に出力
- OpenAI を利用する機能は API キー必須でフェイルセーフ設計

---

## 機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading.db に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定（デフォルト 60 秒）
  - 監視は環境にかかわらず production sqlite_path を使用
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.score_news (ニュースセンチメントを ai_scores に書き込む)
  - kabusys.ai.regime_detector.score_regime (市場レジームを判定して書き込む)
- ポートフォリオ関連:
  - 候補選定、等重・スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算
- 監視 DB スキーマ自動作成・マイグレーション（monitoring_db.init_monitoring_db）

---

## 依存関係（主なもの）

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML （config 検証で任意・未インストール時は YAML 検証をスキップ）
- 標準ライブラリの sqlite3 等

インストール例:
```
pip install duckdb psutil openai PyYAML
```
（requirements.txt があれば `pip install -r requirements.txt` を推奨）

---

## 環境変数（主な項目）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・推奨:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- MONITOR_POLL_INTERVAL — 監視ポーリング秒数（run_monitoring 用、デフォルト 60）
- PID_FILE_PATH — execution.pid のパス（デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1, デフォルト 0)

.env の自動生成には `python -m kabusys.config_setup` を使用してください。

---

## セットアップ手順（ローカルでの起動準備）

1. リポジトリをクローンして作業ディレクトリに移動
2. Python 3.10+ の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後、`python -m kabusys.validate_config` で検証
5. 必要ディレクトリを作成（通常はスクリプトが自動作成しますが確認）
   - mkdir -p data logs
6. OpenAI を使う場合は OPENAI_API_KEY を .env に設定

---

## 使い方（実行例）

- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 注意: 起動前に data/stop_requested.flag が存在すると起動せず終了します
  - paper_trading モード起動例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
- Monitoring を起動
  - MONITOR_POLL_INTERVAL で間隔を指定可能（秒、デフォルト 60）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するとループが終了します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db、`--db PATH` で上書き可能
- AI スコアリング／レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、DB に結果を書き込みます。OPENAI_API_KEY を設定してください。

停止・Kill Switch:
- ExecutionEngine に停止を指示する方法
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止指示を送る設計（monitoring が検出して書き込む）
  - run_execution/run_monitoring の終了用フラグ: data/stop_requested.flag（存在すると起動/ループ中に終了します）
- 起動時に kill.flag を自動クリアする設定:
  - KILL_FLAG_CLEAR_ON_START=1（本番では推奨しない）

ログ:
- コンソール出力に加え logs/<app_name>.log に日次ローテート出力（デフォルト 30 日保持）
- ログディレクトリは環境変数 LOG_DIR で変更可能

---

## ディレクトリ構成（主なファイル）

リポジトリ内 src/kabusys 以下の主要ファイル・パッケージ:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & 永続化層
    - system_monitor.py
    - trade_monitor.py       (含まれるもの: TradeCheckResult 等)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       (アラート管理)
  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体）
    - broker_factory.py      — BrokerClientFactory（本番 / モック選択）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py

- data/     — デフォルトの DB / フラグを置く想定ディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/     — ログファイル出力先（logs/execution.log, logs/monitoring.log 等）

---

## データベース（概要）

- DuckDB（分析用）: デフォルト data/kabusys.duckdb（prices_daily, raw_financials, raw_news, ai_scores などを想定）
- SQLite（監視・注文ログ）: data/monitoring.db（monitoring_db.init_monitoring_db がテーブルを作成）
  - 主なテーブル:
    - system_status (システム稼働記録)
    - trade_logs (発注イベントログ、latency_ms カラム含む)
    - positions
    - risk_logs
    - dashboard

注意: run_monitoring は KABUSYS_ENV にかかわらず sqlite_path を使用します。run_execution は paper_trading の場合 paper_sqlite_path を使用して本番 DB と分離します。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストで便利）
- OpenAI 呼び出し部分はテストしやすいように内部 API 呼出関数をモック可能（例: unittest.mock.patch）
- monitoring/run のポーリング間隔は MONITOR_POLL_INTERVAL で調整可能（短くしてテスト実行）
- ログレベルは LOG_LEVEL で調整（DEBUG にして詳細な挙動を確認）

---

## 注意事項

- 本番環境（KABUSYS_ENV=live）は強力な操作を伴います。設定（API キー、KILL FLAG の扱い、ログ等）を入念に確認してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup も README に記載のヘッダで注意喚起します）。
- OpenAI や外部 API 利用時は利用料・レート制限に注意してください（リトライ・バックオフは実装済みですがコストは発生します）。

---

もし README に追加したい内容（例: サンプル .env、シーケンス図、運用手順、テストスクリプトなど）があれば教えてください。必要に応じて追記します。