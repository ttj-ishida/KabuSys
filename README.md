# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装したコードベースです。本リポジトリには設定管理、実行エンジン起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、リサーチ用ファクター計算、AI を用いたニュース NLP などのモジュールが含まれます。

以下はプロジェクトの概要、機能一覧、セットアップ手順、主要コマンドの使い方とディレクトリ構成の説明です。

重要: 本 README はリポジトリ内のソースコードを参照して作成しています。実行にあたっては環境に応じて .env の設定や DB ファイル配置、外部 API キー等の準備が必要です。

---

## プロジェクト概要

- 自動売買システム（ExecutionEngine 等）および周辺ユーティリティ群の実装。
- 監視（Monitoring）機能によりプロセスの生存確認、データ鮮度チェック、注文滞留・約定異常やリスク（ドローダウン・ポジション上限）を検出してログ／アラート／Kill Switch を管理。
- DuckDB を用いたリサーチ（ファクター計算、特徴量解析）、OpenAI を用いたニュースセンチメント評価（AI モジュール）を含む。
- paper_trading（ペーパートレード）モードをサポートし、本番 DB と分離して検証が可能。

---

## 主な機能一覧

- 設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
  - 設定ウィザード（kabusys.config_setup）で .env の対話的生成
  - 設定検証 CLI（kabusys.validate_config）

- 実行エンジン関連
  - run_execution.py: ExecutionEngine の起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード用 DB（data/paper_trading.db など）へ記録
    - 停止フラグ / PID 管理（data/execution.pid, data/stop_requested.flag）

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングスクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔指定可）
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor をまとめて定期実行し、KillSwitch、AlertManager と連携可能
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブル管理

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定、等配分 / スコア配分、ポジションサイズ決定、セクターキャップ適用、レジーム乗数

- リサーチ
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索、将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini 想定）でスコアリングして ai_scores テーブルへ書き込み（news_nlp）
  - 市場レジーム判定（regime_detector）: ETF MA とマクロニュースの LLM センチメントを合成

- ツール
  - paper_verification_report: paper_trading DB の検証レポート生成（稼働率・注文成功率・レイテンシ等の集計と PASS/FAIL 判定）

---

## 前提・依存

- Python 3.10 以上（typing の `X | Y` 構文を使用しているため）
- 必要ライブラリ（最低限）
  - duckdb
  - psutil
  - openai
- 任意（検証用）
  - PyYAML（validate_config の YAML 検証に使用。未インストールでも動作するが警告が出ます）

インストール例（仮）:
```
python -m pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使用し DB を分離して記録
  - live: 本番（注意喚起）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — Paper Trading の fill モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 実行時に kill.flag を自動クリアするか（0/1、デフォルト 0）

.env の自動読み込み:
- プロジェクトルートが検出されると .env（既存の OS 環境変数を上書きしない）を読み込み、
  .env.local（上書き可）を読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. Python 環境を用意（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. .env を用意
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに .env を生成（または既存ファイルを更新）します。
   - あるいは手動で .env を作成してください（.env.example があれば参照）。

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. DB 初期化
   - run_execution/run_monitoring 起動時に MonitoringDB の初期化が行われます（init_monitoring_db が冪等にテーブル作成）。
   - DuckDB 用のデータファイル（prices_daily などのテーブルを含む）は別途生成・投入が必要（リサーチ用途）。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（実行エンジン）
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading にすると MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録されます。例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

  - 実行はバックグラウンドスレッドで行われ、data/execution.pid が生成されます。停止は data/stop_requested.flag を作るか外部から Stop シグナルで行います（stop フラグ検知でエンジン停止）。

- SystemMonitor（監視）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定可能（例: 30 秒）
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視ループは data/stop_requested.flag が存在すると終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト: data/paper_trading.db）。

- AI 関連（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡してニュースの AI スコアを計算・書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジームを判定し DB に書き込み
  - これらはスクリプト化されていないため、スクリプトやスケジューラから呼び出してください。OPENAI_API_KEY が必要です。

---

## 停止／Kill Switch の扱い

- run_execution / run_monitoring それぞれで停止用のフラグファイルや PID を使用します:
  - 停止（外部）: プロセスに対して data/stop_requested.flag を作成すると、run_execution/run_monitoring はそれを検知して終了します。
  - Kill Switch（自動停止）: 監視ロジック（KillSwitch）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させます。kill.flag はデフォルトで手動クリアが必要。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では推奨されません。

---

## 主要ファイル / ディレクトリ構成

以下は主要なファイルとサブパッケージの概要（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動ロード）
  - config_setup.py          — .env 作成ウィザード（対話式）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py  — paper_trading 検証レポート
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム状態 / データ鮮度の監視
    - trade_monitor.py       — 注文滞留 / 約定異常の監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor の統合ループ（テスト / 本番用）
    - alert_manager.py       — アラート送信の抽象（実装ファイルは省略）
  - execution/                — 実行エンジン関連（OrderManager, ExecutionEngine など、複数ファイル）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP）
  - data/ （実行時に使う DB ファイル・フラグ等）
    - monitoring.db (default: SQLITE_PATH)
    - kabusys.duckdb (default: DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

（上記は主要モジュールの一覧であり、実際のファイルはさらに細分化されています）

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV が `live` の場合は本番扱いの警告が多数出ます。LINE 通知や kill flag の扱いなどを慎重に設定してください。
- Paper Trading は本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- .env は機密情報が含まれるため決して Git にコミットしないでください（config_setup もヘッダに注意書きを出します）。
- OpenAI 呼び出しはコストがかかります。テスト時はモック化して _call_openai_api を差し替えることを推奨します（コードにそのためのコメントがあります）。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news など）は別途データ投入が必要です（リサーチ・AI モジュールが参照）。
- run_monitoring/run_execution は stop フラグ / PID を使って制御します。運用時は監視（systemd / supervisor / cron）と合わせて使うと安全です。

---

## よく使うコマンドまとめ

- 仮想環境作成・依存インストール
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml
  ```

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン（ペーパートレード）
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視ループ起動（ポーリング間隔を 30 秒に設定）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。運用環境での導入・本番移行時は設定（.env、DB バックアップ、LINE 通知、監視・再起動の仕組み等）を十分に確認してください。質問や追加で README に入れたい具体的な使用例があればお知らせください。