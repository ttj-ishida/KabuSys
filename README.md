# KabuSys

日本株向け自動売買システムの一部実装（ライブラリ & 起動スクリプト群）。

このリポジトリは、戦略研究・ポートフォリオ構築・発注実行・監視・AI を組み合わせた
自動売買プラットフォームのコアコンポーネント群を含みます。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株の自動売買に必要な以下機能群を提供する
  - データパイプライン / DuckDB を用いたファクター計算（research）
  - ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
  - 発注エンジン（ExecutionEngine）とブローカークライアント抽象化
  - 監視（System / Trade / Risk）および Kill Switch
  - AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
  - 運用用ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード / 検証）
  - 運用ツール（ペーパートレード検証レポート作成等）
- 実装言語: Python 3.x

---

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（.env, .env.local、OS 環境変数を保護）
  - 対話式ウィザードで .env を作成する `kabusys.config_setup`
  - 起動前設定検証 `kabusys.validate_config`
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 監視
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン、ポジション上限監視
  - KillSwitch: しきい値超過時に data/kill.flag を書き込み ExecutionEngine 停止を促す
  - MonitoringDB: 監視ログを SQLite に永続化（テーブル作成/マイグレーション機能含む）
  - MonitoringEngine: 各 Monitor を束ねて定期実行・アラート発行
- 発注周り
  - BrokerClientFactory: 環境に応じて実ブローカー or MockBroker を切り替え
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine（起動・停止制御）
  - Paper Trading: `KABUSYS_ENV=paper_trading` 時は MockBroker を使い `data/paper_trading.db` に記録
- ポートフォリオ構築（純関数）
  - 候補選定、等金額/スコア重み、セクター上限の適用、レジーム乗数、株数決定（lot 単位丸め・集約キャップ）
- 研究用機能（DuckDB ベース）
  - ファクター計算: Momentum / Volatility / Value 等
  - 将来リターン計算、IC（Information Coefficient）算出、ファクター統計
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメント取得 & ai_scores テーブルへの書き込み
  - regime_detector: ETF（1321）の MA 离散度 + マクロセンチメントを合成して日次レジーム判定
- 運用ツール
  - paper_verification_report: ペーパートレード DB を基に PASS/FAIL 判定付きレポート生成

---

## セットアップ手順

1. Python をインストール（Python 3.9+ 推奨）
2. 必要パッケージをインストール（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証時にあれば YAML を解析）
   - 任意: その他の依存は実行する機能に応じて必要
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）
3. リポジトリルートで .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で .env を作成（.env.example を参考に）
   - 自動ロードはデフォルトで有効。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - 警告をエラーとして扱う場合は `--strict` を付ける
5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 起動時に自動で作成される場合もありますが、アクセス権等を事前確認してください

必須の環境変数（代表例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- OPENAI_API_KEY — AI モジュールを使う場合（任意だがないと AI 機能は不可）
主な環境変数（デフォルト値）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- MONITOR_POLL_INTERVAL: 60（run_monitoring のポーリング間隔秒）
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0（1 にすると起動時に kill.flag を自動クリア）

---

## 使い方

起動スクリプト（例）

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可（デフォルト 60 秒）
  - 監視は常に settings.sqlite_path（.env の SQLITE_PATH）を使用します（monitoring は環境に依存しない実 DB を想定）

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 SQLite に記録して本番 DB と分離します
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中は data/execution.pid に PID を書きます

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` で DB パスを指定するか、環境変数 `PAPER_TRADING_SQLITE_PATH` を設定

停止 / Kill:
- run_monitoring / run_execution のループを優雅に停止させるにはルートプロジェクトの data/stop_requested.flag を作成します。
  - 例: `touch data/stop_requested.flag`
- KillSwitch が発動すると data/kill.flag に理由が書かれ、ExecutionEngine 停止のトリガーになります。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

ログ:
- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。
- ローテーションは日次、30日分保持

注意:
- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。API キーが必要です。
- Monitoring は production sqlite_path を使用する設計です。開発環境でも監視 DB の取り扱いに注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の解決・自動ロード・Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロ + ETF MA を合成して market_regime を算出
- monitoring/
  - monitoring_db.py — SQLite のスキーマ初期化と永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
  - risk_monitor.py — ドローダウン・ポジション上限検出
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py (参照のみ; アラート送信の実装が期待される)
  - trade_monitor.py (注文監視ロジック)
- execution/
  - execution_engine.py — エンジン本体
  - broker_factory.py — BrokerClient の生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注系ロジック
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター制限・レジーム乗数
  - position_sizing.py — 株数決定・キャップ処理
- research/
  - factor_research.py — ファクター算出（momentum/volatility/value）
  - feature_exploration.py — 将来リターン・IC・統計
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — 共通ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/monitoring_db.py, monitoring/risk_monitor.py, ...（監視関連）
- data/ (実行時に使用するディレクトリ、DB・フラグファイル等を置く)
  - data/monitoring.db (デフォルト)
  - data/paper_trading.db (paper_trading 用)
  - data/kabusys.duckdb（分析用）
  - data/kill.flag, data/stop_requested.flag, data/execution.pid

（プロジェクトルート）
- pyproject.toml / .git / README.md（本ファイル） など

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では、LINE 通知や KILL フラグの設定に注意してください。validate_config は本番向けの追加チェックを行います。
- .env は決して Git に含めないでください。
- Monitoring は本番の sqlite_path を参照する実装になっているため、開発時に監視ログを汚したくない場合はパスを個別に設定してください。
- AI モジュールは API 呼び出しのリトライやフォールバックを備えていますが、API 利用料やレート制限に注意してください。
- process priority / cpu affinity 設定は psutil を使います。権限不足で設定に失敗することがありますが、その場合は警告が出てスキップされます。

---

必要であれば、この README に以下を追加できます:
- 実行時のログ出力サンプル
- DB スキーマの詳細（各テーブルのカラム説明）
- BrokerClient の実装/接続設定方法（kabuステーション）
- CI / デプロイ手順（systemd / supervisor 用 unit ファイルの例）

ご希望があれば追記します。