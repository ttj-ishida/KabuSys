# KabuSys

日本株向け自動売買基盤（KabuSys）のリポジトリルート用 README。

このプロジェクトは、取引エンジン（発注）、監視（モニタリング）、ポートフォリオ構築・リサーチ、AI ベースのニュース NLP 等のコンポーネントを備えた自動売買システムの骨組みを提供します。

---

## プロジェクト概要

KabuSys は日本株自動売買を想定したモジュール群です。主な目的は以下：

- ExecutionEngine：ブローカークライアント経由での発注管理、リスク制御、約定管理
- Monitoring：システム稼働・データ鮮度・注文ログ・リスクを定期監視し、Kill Switch 等を自動発動
- Portfolio Construction：候補抽出・重み付け・ポジションサイズ計算・セクター制限などの純粋関数群
- Research：DuckDB 上の価格・財務データからファクター計算・将来リターン・IC 等を算出
- AI：ニュース記事から OpenAI を使ったセンチメント評価、マクロセンチメント合成によるレジーム判定
- Tools：ペーパートレード結果の検証レポート生成などユーティリティ

設計方針として、DuckDB や SQLite を使ったデータ処理、OpenAI を用いた NLP 連携、環境変数/.env による設定管理、プロセス優先度設定や統一的なログ設定が組み込まれています。

---

## 主な機能一覧

- 環境設定ウィザード（`.env` 作成補助）: `kabusys.config_setup`
- 設定検証 CLI（.env、config/*.yaml のチェック）: `kabusys.validate_config`
- 実運用・ペーパートレード両対応の Execution 起動スクリプト: `run_execution.py`
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使い `data/paper_trading.db` に分離記録
- 監視用ポーリングループ起動スクリプト: `run_monitoring.py`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔変更可（デフォルト 60 秒）
- MonitoringDB: SQLite での system_status / trade_logs / positions / risk_logs / dashboard 管理
- RiskMonitor / SystemMonitor / TradeMonitor / KillSwitch / AlertManager による総合監視とアラート
- Portfolio モジュール（候補選定・重み算出・ポジションサイズ計算・セクター制限）
- Research モジュール（モメンタム / ボラティリティ / バリュー等のファクター計算、IC 計算）
- AI モジュール
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント（`ai_scores` へ書き込み）
  - regime_detector: MA とマクロセンチメントを合成して市場レジーム判定（`market_regime` へ書込）
- ツール: Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report`

---

## 必要条件（推奨）

- Python 3.10+
  - 型ヒントに PEP 604（X | Y）を使用しているため Python 3.10 以上を推奨します
- SQLite（組み込み）
- 推奨／必須ライブラリ（pip インストール例は下記参照）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合に必要）
  - その他（依存パッケージにより増える可能性あり）

サンプル pip インストール:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実プロダクションでは requirements.txt／Poetry 等で依存管理を行ってください）

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. データ／ログ用ディレクトリを作成
   ```
   mkdir -p data logs
   ```
4. 環境変数（.env）を作成
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
   - 主要な任意/設定例:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）
     - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱い（exit != 0）
   python -m kabusys.validate_config --strict
   ```

注意:
- `.env` の自動ロードはデフォルトで有効です（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
- `.env.local` は `.env` を上書き可能（OS 環境変数は保護されます）。

---

## 使い方（実行例）

- ExecutionEngine（発注エンジン）を起動
  - 注意: `KABUSYS_ENV=live` の場合は実際に発注されます。事前に設定と Kill Flag を確認してください。
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading モードでは MockBroker を使い `PAPER_TRADING_SQLITE_PATH` に記録します。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要: `OPENAI_API_KEY` を環境変数に設定するか、関数引数で渡す設計
  - news_nlp.score_news / regime_detector.score_regime を呼び出して DuckDB 上の raw_news / prices_daily 等を利用してスコアを作成します。

- Kill Switch / 停止フラグ
  - `data/kill.flag` を作成すると ExecutionEngine に停止シグナルを送れます（KillSwitch 実装）。
  - `data/stop_requested.flag` は実行スクリプトがポーリングループ終了を検知するために使用されます。
  - 実行中の PID ファイル: `data/execution.pid`

---

## 主要な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用設定:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - OPENAI_API_KEY — OpenAI を利用する場合に必要
  - MONITOR_POLL_INTERVAL — 監視ポーリング秒数（run_monitoring 用、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading 用 MockBroker の fill モード（instant | partial | never | reject）

※ `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に実行されます。

---

## ディレクトリ構成

以下は `src/kabusys` ベースの主要ファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/.env 読み込み・Settings
  - config_setup.py               — 対話式 .env 作成ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証ツール
  - utils/
    - logging_setup.py            — 統一ログセットアップ
    - process_priority.py         — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, ...）
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - trade_monitor.py            — （取引関連の監視 — 実装参照）
    - kill_switch.py              — kill.flag 管理
    - alert_manager.py            — （アラート送信管理 — 実装参照）
  - execution/
    - execution_engine.py         — 発注セッションとワークフロー（Engine）
    - broker_factory.py           — BrokerClient の生成（mock / real）
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
  - data/ (ランタイム生成・静的ファイル)
  - logs/ (ログ出力ディレクトリ)

---

## 運用上の注意

- KABUSYS_ENV=live の設定では実際の発注が行われます。事前に必須設定やアラート設定を必ず確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` は本番で危険（自動で Kill Flag をクリアしてしまうため）。本番では 0 を推奨します。
- Monitoring は常に本番用の SQLite（Settings.sqlite_path）を参照します。paper_trading モードの Execution は専用 DB を使う点に注意。
- OpenAI 関連は external API 呼び出しを行うため、API キー・レート制限・コストに注意してください。失敗時のフェイルオーバーやバックオフが実装されていますが、運用上の監視を推奨します。
- ログは `kabusys.utils.logging_setup` により標準出力と日次ローテートのファイルに出力されます（デフォルト `logs/<app_name>.log`）。

---

## 参考コマンドまとめ

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

質問や README に追記したい具体的な使い方（環境別起動手順、systemd / docker 化、CI 用の設定等）があれば、その内容に合わせて追加の節を作成します。