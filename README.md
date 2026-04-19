# KabuSys

日本株自動売買システムの一部をまとめたリポジトリ。  
この README はコードベース（src/kabusys 以下）に基づく導入・使い方ドキュメントです。

> バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は日本株の自動売買・運用支援を目的としたモジュール群です。  
主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine）とブローカークライアント連携（実稼働 / ペーパートレード対応）
- システム監視（SystemMonitor / MonitoringEngine）とアラート・Kill Switch
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイジング）
- リサーチ（ファクタ計算、将来リターン、IC 等の解析）
- AI を用いたニュースセンチメント（OpenAI API 経由）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード / 設定検証 CLI
- SQLite / DuckDB を用いたデータ永続化・分析基盤

設計方針として、実際の発注系ロジックとリサーチ／分析ロジックを分離し、ペーパートレード用 DB による分離や、AI 呼び出しのフェイルセーフ等を重視しています。

---

## 主な機能一覧

- run_execution.py：ExecutionEngine 起動（KABUSYS_ENV によりペーパートレード/本番切替）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
  - 停止フラグ（data/stop_requested.flag）で安全停止
- run_monitoring.py：SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）
  - 監視ログは production の sqlite_path を使用
- monitoring/*：監視用コンポーネント（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine）
- monitoring/monitoring_db.py：監視用 SQLite の初期化・読み書き（冪等操作）
- portfolio/*：銘柄選定、重み計算、セクター制限、ポジションサイズ決定（純粋関数群）
- research/*：DuckDB を用いたファクター計算・特徴量解析
- ai/news_nlp.py：ニュースを OpenAI API でスコアリングして ai_scores テーブルに保存
- ai/regime_detector.py：マクロニュース + ETF MA 乖離を使った市場レジーム判定
- tools/paper_verification_report.py：ペーパートレード検証レポート生成 CLI
- config.py：環境変数 / .env 自動読み込みと Settings クラス
- config_setup.py：.env 作成・更新用対話式ウィザード
- validate_config.py：起動前の設定検証 CLI
- utils/*：ログ設定、プロセス優先度設定、その他ユーティリティ

---

## セットアップ手順

前提：
- Python 3.9+ を想定（リポジトリで使用している標準/サードパーティ機能に応じた環境）
- 必要なパッケージ（psutil, duckdb, openai, PyYAML 等）をインストールしてください。

例（pip）:
```
pip install -r requirements.txt
```
※ requirements.txt はリポジトリに含まれていない場合があります。使用する機能に合わせて以下をインストールしてください:
- psutil（プロセス優先度・リソース監視）
- duckdb（リサーチ・AI 前処理）
- openai（AI スコアリング・レジーム判定）
- PyYAML（設定検証時に config/*.yaml をパースする場合）
- sqlite3 は標準ライブラリに含まれます

環境変数の用意:
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db (ペーパートレード用)
  - OPENAI_API_KEY — AI 機能を使う場合必須
  - LOG_LEVEL — デフォルト INFO
  - その他（LINE_TOKEN 等）

.env の作成（対話ウィザード推奨）:
```
python -m kabusys.config_setup
```
ウィザードで .env を生成後、設定を検証:
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合
python -m kabusys.validate_config --strict
```

データディレクトリの準備:
```
mkdir -p data logs
```
monitoring などが自動作成しますが、明示的に作ると権限等で安心です。

注意（本番運用）:
- KABUSYS_ENV=live の場合は設定を慎重に確認してください（validate_config は警告を出します）。
- .env は機密情報を含むため Git にコミットしないでください。

---

## 使い方

基本的なワークフロー例:

1. .env を作成（config_setup）して必要な環境変数を設定
2. 設定検証
   ```
   python -m kabusys.validate_config
   ```
3. ExecutionEngine 起動（注文実行）
   - 通常起動:
     ```
     python -m kabusys.run_execution
     ```
   - ペーパートレード用 DB を使うには KABUSYS_ENV=paper_trading を .env で設定するか環境変数で指定してください。
   - 起動時、data/execution.pid が書かれ、data/stop_requested.flag があれば起動をスキップします。
   - 停止は data/stop_requested.flag を作成することで行えます（監視プロセスや管理者が書き込む）。

4. Monitoring 起動（監視ループ）
   ```
   python -m kabusys.run_monitoring
   ```
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
   - 監視は常に本番 sqlite_path を参照します（環境にかかわらず）。

5. Paper Trading 検証レポート生成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI 関連:
- news_nlp.score_news / regime_detector.score_regime を利用する際は OPENAI_API_KEY を設定してください。
- AI 呼び出しはフェイルセーフを備えており、API が使えない場合はデフォルト値で継続する設計です（ただしスコア・レジームの結果は異なります）。

ログ:
- デフォルトログディレクトリ: logs/
- setup_logging は stdout 出力と日次ローテートのファイル出力を設定します。
- LOG_LEVEL で出力レベルを調整できます。

停止フラグ・Kill Switch:
- 管理的に ExecutionEngine を停止したい場合は data/stop_requested.flag を作成してください（run_execution/run_monitoring はこのファイルを検出して終了します）。
- KillSwitch（監視コンポーネント）は特定条件（過大ドローダウン、ポジション上限等）で data/kill.flag を生成し、ExecutionEngine に停止を促します。
- 本番で KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアします（危険なので本番では 0 推奨）。

---

## 主要設定項目（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（分析用）
- SQLITE_PATH: 監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）

---

## ディレクトリ構成（src/kabusys の抜粋）

- __init__.py
- config.py — 環境変数/.env 読み込み・Settings
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリング
  - regime_detector.py — マクロ + MA を使ったレジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 + CRUD
  - system_monitor.py — システムリソース・データ鮮度監視
  - trade_monitor.py — （実装あり）発注・約定監視（ソース内参照）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （メール/LINE 等の通知管理）※ソース参照
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - ExecutionEngine のコアと周辺（ブローカ抽象 / リスク制御 / オーダー管理）
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数決定・投下上限・単元丸め
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — momentum/value/volatility 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- monitoring_db / utils / tools etc.
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — logging の集中設定
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの一覧です。詳細は src/kabusys 以下の各ファイルをご確認ください。）

---

## 注意事項・運用上のポイント

- .env に機密情報（API キー・パスワード等）を保存する場合、バージョン管理（Git）にコミットしないでください。
- KABUSYS_ENV=live の設定は本番での発注を伴います。十分なテストと設定確認（validate_config）をしてください。
- ペーパートレードは本番 DB と分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する機能は API コストが発生します。API キーの管理とコスト制御に注意してください。
- run_execution/run_monitoring は stop フラグ（data/stop_requested.flag）を用いてグレースフルシャットダウンできます。監視側は kill.flag（data/kill.flag）も使用します。
- ログはデフォルトで logs/ 以下に出力され、日次ローテーションが有効です。

---

## よく使うコマンドまとめ

- 対話式 .env 作成
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を拡張できます（デプロイ手順、systemd ユニット例、Dockerfile、CI 設定、各モジュールの詳細 API ドキュメントなど）。どの部分を優先して追記したいか教えてください。