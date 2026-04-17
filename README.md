# KabuSys

日本株向け自動売買システムのコアライブラリ群（モジュール群の抜粋）。  
このリポジトリは発注エンジン、監視、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などの機能を提供します。

## プロジェクト概要
KabuSys は日本株の自動売買を想定したコンポーネント群です。主な役割は以下のとおりです。

- ExecutionEngine（発注エンジン）の起動／管理（run_execution）
- 監視ループ（System / Trade / Risk）と Kill Switch による自動停止（run_monitoring / monitoring/*）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB ベース）
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI API）
- ペーパートレードの検証レポート生成ツール

設計方針として、ルックアヘッドバイアス回避・フェイルセーフ性・本番とペーパートレードの分離などが考慮されています。

---

## 主な機能一覧
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を使いデータを paper_trading.db に保存。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を変更可（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を参照（環境に依らず）。
- 設定管理
  - config_setup.py：.env を対話式に作成/更新するウィザード
  - validate_config.py：環境変数／config/*.yaml の整合性チェック（--strict で警告もエラー扱い）
  - config.Settings：環境変数読み取り（.env 自動ロード機能あり）
- 監視関連
  - monitoring/system_monitor.py：CPU/メモリ/Disk、プロセス、データ鮮度を監視
  - monitoring/trade_monitor.py：滞留注文、約定価格異常の検出
  - monitoring/risk_monitor.py：ドローダウン・ポジション上限監視とリスクログ記録
  - monitoring/kill_switch.py：kill.flag による ExecutionEngine 停止
  - monitoring/monitoring_db.py：SQLite による永続化層（テーブル作成・CRUD）
  - monitoring/monitoring_engine.py：各 Monitor をまとめて定期実行、アラート発火等
- ポートフォリオ
  - portfolio/*：候補選定、重み付け、単元丸め、セクター上限、レジーム乗数
- リサーチ
  - research/*：モメンタム / ボラティリティ / バリュー等のファクター計算、IC・統計
  - DuckDB を用いた SQL + Python ベースの処理
- AI
  - ai/news_nlp.py：ニュース記事を OpenAI でスコアリングし ai_scores テーブルへ書込
  - ai/regime_detector.py：ETF の MA とマクロニュースを組み合わせ市場レジーム判定
- ツール
  - tools/paper_verification_report.py：ペーパートレード検証レポートの生成（稼働率・成功率・レイテンシ等）

---

## 必要要件（主な依存ライブラリ）
- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config で YAML 検証を行う場合。任意）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成
   - 対話式で作成する:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動作成（例）
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - 自動ロードを無効化したいテスト等では:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
4. 設定検証（必須項目チェック、YAML 構文など）
   ```bash
   python -m kabusys.validate_config
   # 警告も含めて失敗にしたい場合
   python -m kabusys.validate_config --strict
   ```
5. data ディレクトリ（DB・PID・FLAG の格納場所）を作る:
   ```bash
   mkdir -p data
   ```

---

## 使い方（よく使うコマンド）

- 監視ループを起動（MONITOR_POLL_INTERVAL でポーリング間隔を秒指定）
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  注意: 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使います。

- ExecutionEngine を起動
  ```bash
  python -m kabusys.run_execution
  ```
  KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定の検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（コード呼出し例）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API を使うために OPENAI_API_KEY を .env に設定するか、api_key 引数で渡してください。

---

## 重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（PAPER トレード用 DB、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の Fill 動作: instant | partial | never | reject、デフォルト instant）
- LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）
- OPENAI_API_KEY（AI 機能使用時）
- KILL_FLAG_CLEAR_ON_START（ExecutionEngine 起動時に kill.flag を自動クリアするか: 0|1、デフォルト 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））

.env の自動読み込みの優先順位:
- OS 環境変数 > .env.local > .env  
自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## kill.flag / stop_requested.flag / PID
- data/kill.flag:
  - Kill Switch によって作成される停止フラグ。ExecutionEngine はこのファイルの有無で停止判定を行う。
- data/stop_requested.flag:
  - run_monitoring / run_execution で参照される停止フラグ（存在するとループを終了）。
- data/execution.pid:
  - ExecutionEngine の PID を書き込むファイル。SystemMonitor はこのファイルを参照してプロセスの存否をチェック。

Kill フラグの自動クリアは本番では危険なためデフォルトで無効（KILL_FLAG_CLEAR_ON_START=0 推奨）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/.env 読み込みと Settings
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
- utils/
  - process_priority.py          — プロセス優先度・CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py             — SQLite 永続化層（テーブル初期化、CRUD）
  - system_monitor.py            — CPU/メモリ/Disk/データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常監視
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag 書き込みユーティリティ
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - alert_manager.py             — （アラート送信管理、実装ファイルあり）
- execution/                      — 発注関連（OrderManager 等、参照あり）
- portfolio/
  - portfolio_builder.py         — 候補選定・重み付け
  - position_sizing.py           — 株数決定（単元・リスク・上限処理）
  - risk_adjustment.py           — セクター制限・レジーム乗数
- research/
  - factor_research.py           — モメンタム・ボラティリティ・バリュー等
  - feature_exploration.py       — IC / 未来リターン / 統計
- ai/
  - news_nlp.py                  — ニュースセンチメント（OpenAI）
  - regime_detector.py           — 市場レジーム判定（OpenAI + MA）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

（注）一部モジュールはこの抜粋に含まれていない補助モジュールを参照します（例: execution 内の実装等）。実行時は参照先モジュールが揃っていることを確認してください。

---

## 運用上の注意
- 本番（KABUSYS_ENV=live）での起動前には validate_config で設定を慎重に確認してください。LINE 通知設定等が未設定だとアラートが届きません。
- kill.flag や stop_requested.flag による停止はファイルベースのシンプルな制御です。誤操作に注意してください。
- AI（OpenAI）呼出しはコストとレイテンシが発生します。API キーとレート制限・リトライ設計を理解した上で運用してください。
- run_monitoring は監視用 DB（settings.sqlite_path）を使用します。ペーパートレード DB は run_execution の場合に分離されます。

---

その他、詳しい設計やアルゴリズム（PortfolioConstruction.md, StrategyModel.md 等）は別ドキュメントに準拠しています。必要があれば README の拡張（開発フロー、テスト手順、CI 設定など）を追加できます。