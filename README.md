# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要スクリプト・モジュールに基づいて、導入・起動方法や各機能の概要を日本語でまとめたものです。

注意: 実行前に必ず `.env` を適切に設定し、`python -m kabusys.validate_config` で検証してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 動作環境・依存関係
- セットアップ手順
- 使い方（起動 / CLI）
- 重要な環境変数（抜粋）
- 運用上の注意点
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。  
主な目的は以下の通りです。

- シグナル -> ポートフォリオ構築 -> 発注までの Execution Engine（発注、リスク管理、リコンシリエーション等）
- システム稼働監視（Monitoring）と Kill Switch（リスク条件で発注エンジンを止める）
- DuckDB を使ったリサーチ/ファクター計算（ファクター研究モジュール）
- OpenAI を利用したニュース NLP（センチメント評価）・市場レジーム判定
- ペーパートレード用の検証・レポート作成

設計方針として、実運用での安全性（本番・ペーパーの分離、kill flag、ログ、監視）を重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントのファクトリ（本番 / モック切替）
  - OrderManager / Reconciler / RiskManager（発注・リスク制御）
  - ペーパートレードと本番の DB 分離（PAPER_TRADING_SQLITE_PATH）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度
  - TradeMonitor: 注文滞留や約定異常検知（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件合致で data/kill.flag を作成し ExecutionEngine に停止指示
  - MonitoringEngine/run_monitoring.py: ポーリングループで定期実行

- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算 / IC（Information Coefficient）解析
  - ポートフォリオ候補選定・重み計算・ポジションサイズ算出・セクター上限適用

- AI（OpenAI）
  - ニュースのセンチメント評価（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI の呼び出しは堅牢性（リトライ・フォールバック）を考慮

- ツール
  - 環境設定ウィザード（config_setup.py）で `.env` を対話的生成
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート（tools/paper_verification_report.py）

- 共通ユーティリティ
  - ロギング設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - 設定管理（config.Settings）

---

## 動作環境・依存関係

推奨 Python バージョン: Python 3.10+

主な Python ライブラリ（抜粋）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config で YAML 検証を行いたい場合）
- sqlite3（標準ライブラリ）
- その他（requirements.txt があればそれに従ってください）

例:
```
python -m pip install -r requirements.txt
```
存在しない場合は最低限以下をインストールしてください:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```
   pip install -r requirements.txt
   ```
   または最低限:
   ```
   pip install duckdb psutil openai
   pip install PyYAML  # validate_config の YAML 検査を使う場合
   ```

4. 環境変数（.env）の作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、内容を確認して `python -m kabusys.validate_config` で検証します。
     ```
     python -m kabusys.validate_config
     # 警告も厳密に扱いたい場合:
     python -m kabusys.validate_config --strict
     ```

5. デフォルトデータディレクトリ（data/）やログディレクトリ（logs/）は起動時に自動作成されますが、権限等に注意してください。

---

## 使い方（起動 / CLI）

主要スクリプトの起動例。

- ExecutionEngine を起動
  - 本番（デフォルト）:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード（MockBroker を使用し、データは data/paper_trading.db に保存）
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

- Monitoring を起動
  - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（正の整数）。
    ```
    # 例: 30秒間隔で監視ループを回す
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 注意: Monitoring は環境にかかわらず本番 sqlite_path を監視に使用します（monitoring DB は本番パスがデフォルト）。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  # 指定期間のレポート（--from/--to は YYYY-MM-DD）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- AI 機能（プログラムから呼ぶ例）
  - OpenAI API キーを環境変数または引数で渡す必要あり:
    - 環境変数:
      ```
      export OPENAI_API_KEY="sk-..."
      ```
    - プログラム内から呼び出す:
      ```
      from kabusys.ai.news_nlp import score_news
      score_news(conn=duckdb_conn, target_date=date(2026,4,1))
      ```

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用・動作制御:
- KABUSYS_ENV — 実行環境（development, paper_trading, live）
  - paper_trading: MockBroker を使用、DB は PAPER_TRADING_SQLITE_PATH で分離
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログファイル保存ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイル path（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag の path（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB path（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant / partial / never / reject）
- OPENAI_API_KEY — OpenAI を使う場合は必須（news_nlp / regime_detector）

モニタ調整:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

しきい値（監視／リスク系の閾値）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — Monitoring が利用する閾値

---

## 運用上の注意点

- 本番運用時は KABUSYS_ENV=live を設定し、.env に十分な安全対策をしてください（LINE 通知等の設定、KILL_FLAG_CLEAR_ON_START は 0）。
- kill.flag / stop_requested.flag:
  - KillSwitch は条件合致で KILL_FLAG_PATH（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine は kill.flag を検出して安全に停止します。
  - デバッグや強制停止には data/stop_requested.flag を使用するコードパスが存在します（run_* スクリプトで監視）。
- ログ:
  - setup_logging は stdout と日次ローテートされたファイル（logs/<app>.log）を設定します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
  - ログ保持は 30 日（日次ローテーション・バックアップ数 30）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する軽微なスキーマ追加（カラム追加）も行います。重要なスキーマ変更は慎重に行ってください。
- OpenAI 呼出:
  - API 呼び出しで 429/タイムアウト/5xx が返る場合は指数バックオフで再試行します。API キー未設定時は例外を投げます（呼び出し側でキャッチしてください）。
- テスト／開発:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env の読み込みを無効化できます（テスト目的）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成と役割の要約です。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の取得・検証、デフォルト値
    - .env 自動読み込みロジック
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新
  - validate_config.py
    - 起動前に環境変数・config/*.yaml 等の検証を行う CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV によりペーパー/本番の DB 切替
  - run_monitoring.py
    - SystemMonitor をポーリングする起動スクリプト（MONITOR_POLL_INTERVAL で間隔設定可）
  - utils/
    - logging_setup.py — ログ共通設定（stdout + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite への永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・Execution プロセス監視
    - trade_monitor.py — 発注履歴の監視（滞留注文や異常約定の検出）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（kill.flag 書き込み）
    - monitoring_engine.py — 各モニタを束ねて実行
    - alert_manager.py — （通知管理、コード中で参照）
  - execution/
    - execution_engine.py — Engine 本体（run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      （発注ロジック・リスク制御・ブローカ抽象化）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み算出
    - position_sizing.py — 株数算出、最大利用率・単元丸め、aggregate cap
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB を利用）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM ベースセンチメント評価（ai_scores への書き込み）
    - regime_detector.py — ETF MA200 と LLM マクロセンチメントの合成でレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/（ランタイム生成推奨）
    - monitoring DB、paper trading DB、kill.flag、pid ファイル、stop_requested.flag などが置かれる想定
  - logs/（起動時に作成されることが多い）

---

以上が本コードベースの概要・セットアップ・運用メモです。  
何か特定のモジュール（例: ExecutionEngine の詳細、AI モジュールの使い方、DB スキーマや log のカスタマイズ）についてさらに詳しい README やサンプルを作成したい場合は、対象を指定して教えてください。