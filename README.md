# KabuSys

日本株向け自動売買システムのコアライブラリ / 実行スクリプト群です。  
このリポジトリは戦略のためのリサーチ／ファクター計算、ポートフォリオ構築、実行エンジン、監視機能、AI（ニュースセンチメント・レジーム判定）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するコンポーネント群です。主な目的は以下の通りです。

- ファクター計算・特徴量探索（DuckDB を利用）
- ポートフォリオ構築（候補選定・配分・株数計算）
- ExecutionEngine（発注・注文管理・リスク管理）
- 監視（システム状態、注文滞留、リスク監視、Kill Switch）
- Paper Trading の検証レポート生成
- ニュースを LLM（OpenAI）でスコアリングし、レジーム判定に利用

設計方針として、本番口座への不必要なアクセスを避けるため、リサーチ／AI モジュールは外部 API に依存しないか、明示的に API キーを要求する形になっています。

---

## 機能一覧

- config_setup: 対話式で `.env` を作成 / 更新するウィザード（python -m kabusys.config_setup）
- validate_config: 起動前の設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV によって paper_trading モードは MockBroker を用い、paper DB（data/paper_trading.db）に分離
- Monitoring（System / Trade / Risk）起動スクリプト（python -m kabusys.run_monitoring）
  - system_status / trade_logs / risk_logs / positions / dashboard 等を SQLite に記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能
- MonitoringEngine: 各監視をまとめてポーリングし、Kill Switch や LINE 通知を管理
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメント計算・ai_scores への書き込み
  - regime_detector: ETF（1321）の MA とマクロニュースのセンチメントを合成して market_regime に書き込み
- Research モジュール: ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリ
- Portfolio モジュール: 候補選定・等重/スコア重み・ポジションサイズ計算、セクターキャップ、レジーム乗数
- tools.paper_verification_report: Paper Trading の検証レポート生成（期間指定可）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.9+（ソースは型ヒントに union types 等を使用）
- system 用パッケージ: duckdb, psutil, requests, openai（AI 機能利用時）、PyYAML（config 検証で任意）

1. リポジトリをクローンしワークディレクトリに移動
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存のインストール（requirements.txt がある場合）
   ```
   pip install -r requirements.txt
   ```
   手動で必要パッケージを入れる場合（最低限）:
   ```
   pip install duckdb psutil requests
   ```
   AI 機能を使う場合:
   ```
   pip install openai
   ```
   config.yaml の検証をしたい場合:
   ```
   pip install pyyaml
   ```

4. 環境変数設定
   - 対話式ウィザードで `.env` を生成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を直接作成。最低必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
   - AI を使う場合:
     - OPENAI_API_KEY を `.env` または環境変数に設定

5. 設定検証（起動前推奨）
   ```
   python -m kabusys.validate_config
   ```
   警告まで失敗にしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

6. 初回起動に際して DB フォルダ（data/）は自動作成されることが多いですが、開発時に手動で用意しておくとよいです:
   ```
   mkdir -p data
   ```

注意:
- `.env` はシークレット情報を含むため絶対に Git にコミットしないでください。
- 自動的に .env をロードする仕組みは Settings モジュールで行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数とデフォルト

（主なもののみ抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルト:
- KABUSYS_ENV — execution 環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定なら通知はスキップ）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

運用注意:
- 本番時は KABUSYS_ENV=live を設定します。KILL_FLAG_CLEAR_ON_START の値は 0 推奨（1 にすると起動時に kill flag を自動クリアします。危険）。

---

## 使い方（起動例・コマンド）

各コンポーネントはモジュール実行可能（python -m kabusys.<module>）です。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine（戦略発注エンジン）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```

- Monitoring（監視ループ）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # またはデフォルト DB を使う:
  python -m kabusys.tools.paper_verification_report
  ```

- AI モジュール（プログラムから呼ぶ例）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  例（簡易）:
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 4, 1), api_key="sk-...")
  ```

停止方法 / Kill スイッチ:
- 実行ループの外部停止: リポジトリルートの `data/stop_requested.flag` を作成すると `run_execution` / `run_monitoring` のループが検知して終了します。
- Kill Switch（監視コンポーネントが条件を満たした際に書き込む）: `data/kill.flag`。ExecutionEngine は `Settings.kill_flag_path`（デフォルト data/kill.flag）を参照して停止します。
- kill.flag を削除するには:
  - 手動で削除: `rm data/kill.flag`
  - KillSwitch クラス経由: KillSwitch.clear()（エンジン起動時にクリア機能を利用する設定あり）

ログレベルや詳細は `.env` の LOG_LEVEL で調整してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 起動前チェックツール
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト
  - execution/                — 実行エンジン関連（OrderManager, BrokerFactory, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成・永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - process_priority.py

その他:
- data/ — 実行時に生成される SQLite / DuckDB / PID / flag ファイルの保存場所（デフォルト）
  - data/kabusys.duckdb（DuckDB）
  - data/monitoring.db（監視 SQLite）
  - data/paper_trading.db（ペーパートレード SQLite）
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag

---

## 実装上の注意点 / 運用メモ

- run_execution/run_monitoring は起動直後にプロセス優先度を「high」に設定しようとします（psutil を使用）。権限不足の場合は警告が出ますが処理は継続します。
- Monitoring は Settings.env にかかわらず監視用の sqlite_path を使用します（監視ログは本番 DB と別に保管する想定）。
- ペーパートレード時は ExecutionEngine が paper_sqlite_path を使用するため本番 DB と分離されます。
- ai モジュールは OpenAI の呼び出しを行います。API 呼び出しはリトライやバックオフに配慮した実装になっていますが、API キーの漏洩・コストに注意してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等で実行可能です。起動時に必要な列追加（ALTER TABLE）を試みます。
- データの鮮度や PID の stale 検出など、いくつかのチェックで self-healing（例: 古い PID ファイルを削除）を行います。これらの動作はログで確認してください。

---

## 参考コマンド一覧

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定チェック:
  ```
  python -m kabusys.validate_config
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

必要であれば README に含めるコマンドの実例や .env のサンプル（.env.example の内容）を追加で作成します。どの情報をより詳しく載せたいか教えてください。