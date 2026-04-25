# KabuSys

日本株向けの自動売買・リサーチ基盤（KabuSys）のリポジトリ向け README（日本語）。

本 README は提供されたコードベースに基づき、プロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチを支援するパイロット実装です。  
主な役割・目的は次のとおりです。

- シグナル → ポートフォリオ構築 → 発注までの Execution Engine（実発注 / ペーパートレード対応）
- 実行状況やシステム状態の常時監視（監視エンジン、Kill Switch、アラート）
- DuckDB を用いたファクター計算・リサーチ（ファクター計算、IC 計測、特徴量解析）
- ニュースを LLM（OpenAI）で評価する NLP モジュール（銘柄別センチメント）
- ペーパートレード結果の検証用レポート生成ツール

設計方針としては「DBアクセスと計算を分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」などに配慮されています。

---

## 機能一覧

- Execution
  - 実口座（live）とペーパートレード（paper_trading）対応
  - RiskManager / OrderManager / Reconciler による発注管理
  - プロセス優先度設定・PID ファイル管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン監視
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み Execution を停止
  - Monitoring DB（SQLite）による履歴保存（system_status, trade_logs, positions, risk_logs, dashboard）
- Portfolio
  - 候補選定、等金額／スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - 株数決定（単元株丸め、aggregate cap、cost buffer）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - DuckDB を使った SQL+Python 実装
- AI
  - news_nlp：OpenAI（gpt-4o-mini）でニュースを銘柄別にセンチメント化して ai_scores に書き込み
  - regime_detector：MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定
- Tools
  - paper_verification_report：ペーパートレードログから検証レポートを生成
- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env 対話式ウィザード / 設定検証スクリプト

---

## 必要条件（依存）

最低限の実行に必要な主要依存例（抜粋）:

- Python 3.9+（型ヒントの記述から想定）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証を行う場合）
- sqlite3（標準ライブラリ）
- （推奨）仮想環境（venv / virtualenv）

requirements.txt がない場合は次を参考にインストールしてください（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実際のプロジェクトでは requirements.txt / constraints を用意してください。

---

## 環境変数（主要）

Settings クラスで扱われる環境変数（主要なもの）とデフォルト：

- 必須（例）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution 用 PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグ（デフォルト: data/kill.flag）
- ログ / 動作
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- Paper Trading
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能を使う場合）
- 監視しきい値（任意でカスタマイズ）
  - CPU_THRESHOLD_PCT（デフォルト: 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト: 85.0）
  - DISK_THRESHOLD_PCT（デフォルト: 90.0）

.env.example を参考に .env を作成してください（.env は絶対に VCS にコミットしないこと）。

---

## セットアップ手順（推奨）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成してアクティベート
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt  # もし存在する場合
   # ない場合は手動で必要パッケージをインストール
   pip install duckdb psutil openai pyyaml
   ```

3. ディレクトリ作成（デフォルトで使用するパス）
   ```bash
   mkdir -p data logs
   ```

4. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   または手動で `.env` を作成し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を設定してください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. （任意）ログディレクトリ権限確認／その他 OS 設定

---

## 実行方法（主要コマンド）

- Execution エンジンを起動（常用: systemd / supervisor / screen などで実行）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、記録先 DB は `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）になります。
  - ストップは kill.flag / stop flag を用いて行います（下記参照）。

- Monitoring を起動（監視ループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます。
    例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

## 停止・Kill フラグの管理

- 監視・実行ループを停止するための仕組み：
  - data/stop_requested.flag — run_monitoring / run_execution のループ停止を即時検出するためのファイル。
    - ループ中にこのファイルが存在すると安全に終了します。
    - 例: `touch data/stop_requested.flag`（停止要求）
  - data/kill.flag — KillSwitch による ExecutionEngine 停止指示。Monitoring 側の判定によって書き込まれる。
    - ExecutionEngine は起動時に kill.flag をチェックできます（Settings.kill_flag_clear_on_start を参照）。
    - 実行停止・再開の制御に利用します。
  - PID ファイル: data/execution.pid（デフォルト）。ExecutionEngine 起動時に PID を書き込みます。

- kill.flag を手動でクリアする（注意して実行）
  ```bash
  rm -f data/kill.flag
  ```

---

## 注意点 / 運用上のヒント

- production（KABUSYS_ENV=live）での運用は十分な事前検証と監視設定が必要です。validate_config の本番向け警告に注意してください。
- OpenAI API（news_nlp, regime_detector）を利用する場合、API キー（OPENAI_API_KEY）と利用料金・レート制限に注意してください。LLM 呼び出しはリトライ等の保護があるものの安易なスケジュール運用は避けてください。
- .env は機密情報を含むため絶対にコミットしないでください。
- ログは既定で logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）。ログディレクトリのディスク容量を監視してください。
- ペーパートレード環境は本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH）。

---

## ディレクトリ構成（主要ファイルの説明）

以下はソースツリー（src/kabusys）内の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数/設定読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — 監視用 SQLite DB 初期化と読み書きラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （コードベースに含まれる想定の監視）
    - risk_monitor.py — ドローダウン / ポジション数監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — Kill Switch 実装（フラグ書き込み）
    - alert_manager.py — アラート送信ラッパ（LINE など）
  - execution/
    - execution_engine.py — ExecutionEngine（セッション実行の中核）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
    - broker_factory.py — ブローカークライアント生成（実/Mock 切替）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（丸め・キャップ）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 計算（DuckDB）
    - feature_exploration.py — 将来リターン/IC/summary 等
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py — MA200 + マクロニュースでレジーム判定
  - data/  (ランタイムに使用)
    - monitoring.db, paper_trading.db, stop_requested.flag, execution.pid, kill.flag など（自動作成／利用）
  - logs/  (ランタイムログ保存先)

---

## 追加情報 / 開発者向け

- DB 初期化: run_monitoring / run_execution は起動時に monitoring DB のテーブルを作成（init_monitoring_db）します。
- DuckDB 接続は read-only な分析用途や研究モジュールで使用します。prices_daily / raw_financials / raw_news 等のテーブル設計に依存します。
- AI モジュールはテスト容易性を考慮して API 呼び出し関数を差し替え可能（ユニットテストでモック化推奨）。
- 処理における時間参照は "ルックアヘッド対策" として日次関数で datetime.today()/date.today() を直接参照しない設計方針が採られています（テストやバックテストの再現性向上）。

---

もし README に含めたい追加の項目（API ドキュメント、ユニットテストの実行方法、CI 設定、requirements.txt 生成など）があればその内容を教えてください。README をさらに拡張します。