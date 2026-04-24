# KabuSys

日本株自動売買システムの一部コードベース。  
本リポジトリは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築・リスク制御、リサーチ（ファクター計算）、および AI を使ったニュースセンチメント／レジーム判定のユーティリティ群を含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 戦略から得たシグナルを元に「銘柄選定 → 重み付け → 株数算出 → 発注」を行う ExecutionEngine（本番 / ペーパートレード対応）。
- 稼働状況・データ鮮度・注文状態・リスク（ドローダウン・ポジション上限）を定期的に監視する Monitoring。
- DuckDB を使ったファクター計算やリサーチユーティリティ。
- OpenAI（LLM）を用いたニュースセンチメントスコアリング / 市場レジーム判定。
- .env の対話式作成ウィザードと設定検証ツール、ペーパートレード検証レポート生成ツールなどの運用ツール群。

主要な設計方針として、ルックアヘッド（未来参照）を避ける実装、DB の分離（ペーパートレード用 DB を別ファイルに保持）、フェイルセーフ（API 失敗時のフォールバック）等が採用されています。

---

## 機能一覧

- Execution（発注）
  - ExecutionEngine（run_execution.py）
  - BrokerClientFactory により実際のブローカー or Mock を切り替え（KABUSYS_ENV=paper_trading 時は MockBrokerClient）
  - ペーパートレードは専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - kill.flag による Kill Switch（ExecutionEngine を停止するフラグ）
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）

- Portfolio（配分・サイズ算出）
  - 候補選定、スコア／等配分重みの計算、セクターキャップ、レジーム乗数、リスクベースの株数算出

- Research（リサーチ）
  - momentum / volatility / value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI（OpenAI を利用）
  - ニュース記事のセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース＋ETF（1321）MA200 の乖離に基づく市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ/バックオフ処理を実装

- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

以下は一般的なローカルセットアップ例です。

前提:
- Python 3.9+（実装が型ヒントに Path | None などを使用しているため推奨）
- Git

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb psutil openai pyyaml
   ```
   - openai: OpenAI API を使う AI モジュール用
   - duckdb: リサーチ・AI 用のクエリ処理
   - psutil: プロセス優先度やシステム計測
   - pyyaml: validate_config が YAML の内容検証を行う場合に必要（オプション）

   ※ 実際の requirements.txt がある場合はそれを利用してください。

4. 必要ディレクトリを作成
   ```
   mkdir -p data logs
   ```

5. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   または手動で .env を作成。主要な環境変数例:
   ```
   KABUSYS_ENV=development            # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   OPENAI_API_KEY=sk-...
   ```

6. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

主要なコマンド例（パッケージとしてインストールしていない場合はプロジェクトルートで実行）:

- ExecutionEngine（取引実行）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV 環境変数により動作が変わります:
    - development: 実際の発注なし（開発用）
    - paper_trading: MockBroker を使用、DB は data/paper_trading.db（本番 DB と分離）
    - live: 実際のブローカーを使用して発注（要注意）

  - 停止: プロセス停止や data/stop_requested.flag ファイルの作成で安全に停止します。
  - PID ファイル: data/execution.pid（デフォルト）にプロセス ID を書きます。

- Monitoring（監視ループ）を起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）

- Paper Trading 検証レポート（期間指定可）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI モジュール（プログラムから呼び出す）
  - ニューススコアリング:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Kill Switch / Stop 制御
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（run_execution/run_monitoring は存在確認・評価を行う）。
  - run_execution/run_monitoring は data/stop_requested.flag の存在で自プロセスを停止します。
  - Settings の KILL_FLAG_CLEAR_ON_START が "1" の場合、実行開始時に kill.flag を自動でクリアします（本番では推奨しません）。

- ロギング
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション・30日保持）に出力します。
  - 環境変数 LOG_DIR、LOG_LEVEL で制御可能。

---

## 環境変数（主なもの）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時ローカル）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モードで使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1"=クリア）

詳細は kabusys.config.Settings のプロパティにコメントがあります。自動で .env をロードする仕組みが入っており（プロジェクトルートの .env/.env.local）、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 配下の主要ファイル・モジュールのサマリです。

- src/kabusys/
  - __init__.py              — パッケージ定義、バージョン
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話式作成ウィザード（CLI）
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト

  - execution/               — 発注関連（ExecutionEngine, OrderManager 等） ※一部のみ参照される
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py        — SQLite スキーマ定義 / 永続化 API
    - system_monitor.py       — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py        — 注文・約定監視（滞留・異常検出）
    - risk_monitor.py         — ドローダウン & ポジション上限監視
    - kill_switch.py          — kill.flag の書き込み/評価
    - monitoring_engine.py    — 各モニタの統合ループ
    - alert_manager.py        — （通知）LINE 等へのアラート送信ラッパー

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出（risk_based / equal / score）
    - risk_adjustment.py      — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py      — momentum/volatility/value の計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
    - __init__.py

  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に格納
    - regime_detector.py      — ETF MA 乖離 + マクロニュースでレジーム判定
    - __init__.py

  - monitoring/monitoring_db.py — 監視用DBスキーマ（system_status, trade_logs, positions, risk_logs, dashboard）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
    - __init__.py

  - utils/
    - logging_setup.py        — 共通ログ設定（stdout + 日次ローテート）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

（上記は抜粋です。実際のファイルは src/kabusys 以下を参照してください。）

---

## 運用上の注意（重要）

- KABUSYS_ENV=live を使用する際は十分に注意してください。validate_config は live 時の追加警告チェックを行います。
- .env ファイルは機密情報を含みます。絶対に Git にコミットしないでください。
- プロセス優先度設定や CPU affinity の適用には管理者権限が必要な場合があります。失敗した場合は警告が出力され、処理は継続します。
- OpenAI API を使う機能は API コストが発生します。rate limit やエラー処理は組み込まれていますが、運用時は使用量を監視してください。
- Monitoring は常に（本番）monitoring.sqlite_path を参照します。ペーパートレードと混同しないよう DB パスを適切に設定してください。

---

## よく使うコマンドまとめ

- .env 作成（対話式）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README に環境変数のサンプル .env、より詳細なディレクトリツリー、または各モジュールの API 使用例（関数呼び出し例）を追加できます。どの内容を重点的に追記しますか？