# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、取引実行エンジン、監視基盤、ポートフォリオ構築・サイズ計算、研究用ファクター計算、ニュース NLP（LLM）連携などを含む自動売買システムのコア実装を集めたものです。

---

## 概要

- 実行（ExecutionEngine）と監視（MonitoringEngine）を分離して実装。
- Paper Trading（検証用）と Live（本番）を環境変数で切り替え可能。paper_trading では MockBroker を用い、DBは本番と分離されます。
- DuckDB を用いた分析用データ、SQLite を用いた監視・ログ永続化を利用。
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価・市場レジーム判定を実装（任意）。
- ログはコンソール出力 + 日次ローテートファイル出力（logs/<app>.log）で管理。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動
  - run_monitoring.py — SystemMonitor ポーリングループ起動
- 環境設定 / 検証
  - config_setup.py — .env の対話式ウィザード生成
  - validate_config.py — .env / config/*.yaml の事前検証 CLI
- 監視（monitoring）
  - system_monitor: CPU/メモリ/ディスク・データ鮮度・プロセス死活監視
  - trade_monitor: 注文ログの整合性・滞留注文など監視（実装参照）
  - risk_monitor: ドローダウン・ポジション上限の監視とリスクログ
  - kill_switch: リスク条件に基づく停止フラグ（data/kill.flag）生成
  - monitoring_db: SQLite スキーマの初期化および永続化 API
  - monitoring_engine: 各 Monitor を束ねて定期実行
- 実行（execution）
  - BrokerFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler 等（発注ロジック）
  - ペーパートレード時には専用 DB（data/paper_trading.db）を使用
- ポートフォリオ構築（pure functions）
  - 銘柄選定、等配分・スコア配分、セクター制約、ポジションサイズ計算（lot 単位処理・スケーリング等）
- リサーチ
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB SQL ベース）
  - feature_exploration: 将来リターン計算、IC（情報係数）等
- AI（任意）
  - news_nlp: ニュース記事を集約し OpenAI にて銘柄別センチメント算出 → ai_scores テーブルへ書込
  - regime_detector: ETF 指標 + マクロニュースで日次レジーム判定（market_regime テーブルへ書込）
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成
- ユーティリティ
  - logging_setup: コンソール + 日次ローテートログの一元設定
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - config: .env 自動読み込み、Settings クラスによる環境変数管理（必須・デフォルト値の定義）

---

## 前提 / 必要パッケージ

- Python 3.9+
- 必要な外部ライブラリ（代表例）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（validate_config で YAML 検証を行う場合、必須ではない）
- 標準ライブラリ: sqlite3, logging, threading, argparse など

インストール例（pip）:
```bash
pip install duckdb psutil openai PyYAML
```
※ requirements.txt は本リポジトリに含まれていないため、実行環境に応じて上記パッケージを導入してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化（推奨）
3. 必要なパッケージをインストール（上記参照）
4. 対話式で .env を作成:
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config でも検出）
   - KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか
5. 設定検証（起動前推奨）:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（代表的なコマンド）

- ExecutionEngine 起動（実行エンジン）
  - 本番/ペーパートレード分離: KABUSYS_ENV により挙動が変わります。
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレードで起動したい場合:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 停止: data/stop_requested.flag を作成するとループを検知して停止します（run_execution/run_monitoring ともに）。また監視側でリスクトリガー発生時に data/kill.flag を書き込むことで実行エンジンを停止できます。

- Monitoring 起動（ポーリング）
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可能:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。Monitoring は環境にかかわらず本番 sqlite_path を参照する実装になっています（注意）。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または環境変数で DB 指定:
  ```bash
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数）。
  - モジュールを直接呼び出してスコアを書き込むことができます（DuckDB 接続を渡す必要あり）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (ニュース NLP / レジーム判定で必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （通知用、任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、推奨は 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

詳細は `kabusys.config.Settings` を参照してください（デフォルト値・検証ロジックが実装されています）。

---

## 停止・フラグファイル

- 停止要求（強制停止）:
  - data/stop_requested.flag — run_execution / run_monitoring のポーリングループはこのフラグ存在を検知して優雅に終了します。
- Kill Switch（監視による自動停止）:
  - monitoring 側の KillSwitch がリスク条件を検出すると data/kill.flag に理由を書き込みます。ExecutionEngine は起動時やループ中にこのフラグを検知して停止します。
- フラグのクリア:
  - 監視アプリまたは手動でファイルを削除してください。設定により起動時に自動クリアすることも可能（KILL_FLAG_CLEAR_ON_START=1。※本番では注意）。

---

## ロギング

- ログ出力は `kabusys.utils.logging_setup.setup_logging` により統一されます。
- デフォルトは stdout と `logs/<app>.log`（日次ローテーション、30日保持）。
- ログディレクトリは環境変数 `LOG_DIR` または引数で上書き可能。

---

## 簡易トラブルシューティング

- 必須環境変数未設定:
  - `python -m kabusys.validate_config` を実行して不足を確認してください。
- run_monitoring がすぐ終了する:
  - プロジェクトルート/data/stop_requested.flag が存在していないか確認。ある場合は削除して再起動。
- ExecutionEngine が即停止する（起動時）:
  - run_execution は起動時に stop フラグをチェックします。data/stop_requested.flag を削除してください。
- AI 呼び出しが失敗する:
  - OPENAI_API_KEY の設定、ネットワーク、利用モデルの使用制限を確認してください。API 呼び出しはリトライ/フォールバック実装がありますが、キー未設定時は例外になります。

---

## ディレクトリ構成

（重要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — Settings クラス・.env 自動ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ・永続化 API
    - system_monitor.py — システム状態チェック
    - trade_monitor.py — 注文ログ監視（実装参照）
    - risk_monitor.py — ドローダウン・ポジション制限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py —（アラート送信管理、実装を確認）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金配分ロジック
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度／CPU affinity
  - execution/  — ExecutionEngine 関連（OrderManager, BrokerFactory, 等）

プロジェクトルートには以下のようなディレクトリ/ファイルが想定されます:
- .env / .env.local
- data/ (デフォルト: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid)
- logs/ (ログ出力)

---

## 開発者向けメモ

- モジュールの多くは外部依存（DuckDB / OpenAI / psutil 等）を受け取り、テスト時に差し替え可能な設計（依存性注入）になっています。
- データベース操作はなるべく冪等に実装（CREATE IF NOT EXISTS / DELETE→INSERT のパターン等）。
- AI 呼び出し部は JSON モードで厳格出力を期待するが、外部エラーに対してフォールバックを行うように実装されています。

---

README は概観と基本的な運用手順を示すことを目的としています。各モジュールの詳細な使用方法や API（関数シグネチャ、戻り値、例外仕様など）は各ソースコードの docstring を参照してください。必要があれば、各コンポーネント毎の詳細ドキュメントを別途作成します。