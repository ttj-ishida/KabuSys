# KabuSys

日本株向け自動売買システムのコアライブラリと起動スクリプト群。

このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AIベースのニューススコアリング等を含むモジュール群を提供します。設計方針としては本番環境とペーパートレード（検証）を分離し、環境変数/.env を中心に設定を管理します。

---

## 機能一覧

- 起動スクリプト
  - ExecutionEngine 起動: 実際の注文処理を行う（本番/ペーパー両対応）
  - Monitoring 起動: システム・注文・リスクの定期チェック、Kill Switch の評価
- 環境設定
  - 対話式 .env ウィザード（config_setup）
  - 起動前設定検証ツール（validate_config）
- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor: 注文滞留・約定異常チェック（trade_logs）
  - RiskMonitor: ドローダウン・ポジション数上限の監視
  - KillSwitch: 重大リスク時に flag ファイルを書き実行エンジンを停止
  - MonitoringDB: SQLite に監視ログを永続化
  - MonitoringEngine: 各モニタをまとめてポーリング、アラート発行
- 発注 / 実行（execution）
  - ブローカークライアントファクトリ（本番と Mock を切り替え）
  - OrderManager / OrderRepository / Reconciler / RiskManager 等
  - Paper trading（KABUSYS_ENV=paper_trading）時は MockBroker を使用し専用 DB に記録
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ決定、セクター上限・レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（ai）
  - ニュース NLP（OpenAI）での銘柄センチメント採点（news_nlp）
  - 市場レジーム判定（regime_detector）— ETF 指標 + LLM を合成
- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提・要件

- Python 3.10+
- 推奨パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証に任意）
- （任意）venv / virtualenv を利用した仮想環境作成を推奨

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
requirements.txt をプロジェクトに含める場合は duckdb, psutil, openai, pyyaml 等を列挙してください。

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成して依存をインストール
3. 環境変数（.env）作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートの `.env` が作成/更新されます。
4. 設定の検証:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。
5. データディレクトリ等の確認
   - デフォルトの DB / ログパスは `data/` と `logs/` です。`.env` で上書き可能。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject） デフォルト: instant
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） デフォルト: INFO
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- MONITOR_POLL_INTERVAL: monitoring スクリプトのポーリング間隔（秒、デフォルト 60）

注: `.env.example` をプロジェクトに含めている場合は参考にしてください（存在する想定）。

---

## 使い方

### 設定関連

- 対話式 .env 作成 / 更新:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

### 実行エンジン（ExecutionEngine）

- 本番またはペーパーで動かす:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db など）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag が作成されると Engine.stop() を呼んで安全に停止します。
  - 実行時は execution 用の PID ファイル（data/execution.pid など）を作成します。

### 監視（Monitoring）

- 監視ポーリングループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を参照してログを書きます（環境に依存せず監視 DB を使用）。
  - 停止フラグ（data/stop_requested.flag）を検知するとループを抜けて終了します。

### Paper Trading 検証レポート

- ペーパートレード DB から検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  DB パス未指定時は環境変数 PAPER_TRADING_SQLITE_PATH または `data/paper_trading.db` を使います。

### ライブラリ API（スクリプト以外の利用例）

- AI ニューススコアリング:
  ```
  from kabusys.ai import score_news
  # duckdb_conn: duckdb の接続オブジェクト、target_date: datetime.date
  count = score_news(duckdb_conn, target_date, api_key="sk-...")
  ```

- リサーチ / ファクター計算:
  ```
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  # calc_* に duckdb_conn と target_date を渡して使用
  ```

- ポートフォリオ構築ユーティリティ:
  ```
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  ```

---

## Kill / Stop フロー（運用メモ）

- ExecutionEngine の強制停止トリガーは `data/kill.flag`（KillSwitch）および `data/stop_requested.flag`。
  - KillSwitch は RiskMonitor 等の判定で `data/kill.flag` を書くことでエンジン停止を促します。
  - `data/stop_requested.flag` は run_execution/run_monitoring の外部制御用（存在すると監視/実行ループが終了）。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると Kill Flag を自動でクリアします（本番では推奨しません）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py      — SQLite 保存層（テーブル初期化・CRUD）
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （注文関連の監視）※実装ファイルを参照
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag 制御
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — アラート送信管理（LINE 等、実装に依存）
  - execution/
    - execution_engine.py   — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py     — Broker クライアント生成（本番/Mock 切り替え）
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
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - data/                   — デフォルトの DB / flag / pid 等（実行時に生成）

---

## 運用上の注意

- 本番環境 (KABUSYS_ENV=live) に切り替える際は必須環境変数を必ず設定し、validate_config で警告・エラーを確認してください。
- .env ファイルは機密情報（API トークン等）を含むため、絶対に VCS にコミットしないでください。
- OpenAI を利用する機能は API キーの使用料が発生します。API コールの頻度・バッチサイズに注意してください。
- ペーパートレードは本番 DB と物理的に分離されています（PAPER_TRADING_SQLITE_PATH を使用）。検証時に本番 DB を上書きしないこと。

---

この README はコード内コメント・設計注釈を参照して作成しています。詳細な挙動や追加設定は該当モジュールの docstring / ソースコメントを参照してください。改良や追加の実行例が必要であれば指示ください。