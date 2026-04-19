# KabuSys

日本株向け自動売買システムの実装（モジュール群）。  
このリポジトリは戦略生成・ポートフォリオ構築・発注実行・監視・レポート生成・研究ユーティリティなどを含む小規模なフルスタック自動売買フレームワークです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのプロトタイプ実装です。主な責務は以下です。

- 市場データ（DuckDB 上の prices_daily 等）を用いたファクター算出・特徴量作成（research）
- ポートフォリオ候補選定、重み計算、ポジションサイズ算出（portfolio）
- 発注管理・リスク管理・実行エンジン（execution）
  - 本番 / ペーパートレード（分離された SQLite DB）をサポート
- システム監視・アラート・Kill Switch（monitoring）
- ニュースの NLP による銘柄スコアリング・レジーム判定（ai）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

設計上の特徴:
- DB は DuckDB（分析）と SQLite（監視・発注ログ）を併用
- OpenAI を用いた自然言語処理機能（ai）を備える（環境変数 `OPENAI_API_KEY` 必須）
- .env による環境変数管理。`config_setup` ウィザードと `validate_config` による検証を提供
- 実行・監視プロセスはフラグファイル（data/kill.flag, data/stop_requested.flag）で制御可能

---

## 機能一覧

- 環境構成
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 起動前チェック（kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine（run_execution.py）
  - BrokerClientFactory による本番 / モックブローカー切替（KABUSYS_ENV）
  - Paper trading 用に専用 SQLite (data/paper_trading.db) を使用
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - 監視結果の永続化（monitoring_db）
  - KillSwitch による自動停止シグナル生成（data/kill.flag）
- ポートフォリオ構築
  - 候補選定、等配分/スコア配分、リスクベースの単位株決定、セクター制限、レジーム乗数
- 研究用機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続を受け取る）
  - 将来リターン計算、IC（Information Coefficient）等の解析関数
- AI（OpenAI）統合
  - ニュースのセンチメント算出と ai_scores への書き込み（kabusys.ai.news_nlp）
  - マクロセンチメント + ETF ma200 乖離を使った市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（代表的な依存）
   - 必須: duckdb, psutil, openai
   - 推奨: PyYAML（config ファイル検証用）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （リポジトリに requirements.txt がない場合は上記を参考にインストールしてください）

4. .env の作成
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env` を手動で作成（以下の必須キーを設定）
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 主要オプション:
       - KABUSYS_ENV (development | paper_trading | live)
       - DUCKDB_PATH (default: data/kabusys.duckdb)
       - SQLITE_PATH (default: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (paper 用 DB, default: data/paper_trading.db)
       - LOG_LEVEL (DEBUG/INFO/...)
       - OPENAI_API_KEY (AI 機能を使う場合)
       - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （アラート通知）
       - PAPER_FILL_MODE (instant | partial | never | reject)

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ等の準備
   - デフォルトでは `data/` や `logs/` にファイルを作成します。必要に応じて権限や所有者を確認してください。

---

## 使い方（起動／主要コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - 本番 / ペーパーの動作は KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```

- 監視ループを起動（SystemMonitor 等）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
  ```
  python -m kabusys.run_monitoring
  # 例: 30 秒間隔
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- .env を対話的に作成 / 編集
  ```
  python -m kabusys.config_setup
  ```

- 設定チェック
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニューススコアリング / レジーム判定）
  - `OPENAI_API_KEY` を設定してから、コード内の関数を呼び出すか、将来的に CLI を用意している場合はそれを使用してください。
  - 例（ライブラリとして使用）:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect("data/kabusys.duckdb")
    score_news(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

- 停止制御 / フラグ
  - 実行中のプロセスを外部から止めるには `data/stop_requested.flag`（run_monitoring/run_execution が監視）を作成します（存在を検知してループを抜ける）。
  - Kill Switch（リスク閾値到達時に Execution を停止）: `data/kill.flag` が生成されると Execution 停止シグナルとして扱われます。
  - Execution の PID 管理: `data/execution.pid` を利用

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- OPENAI_API_KEY — OpenAI を使う機能で必須
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- LOG_LEVEL — ログ出力レベル
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

（詳細は `kabusys.config.Settings` を参照してください）

---

## ログ / ファイル配置（デフォルト）

- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / フラグ:
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag
- ログ: logs/<app_name>.log（日次ローテーション、30日保存）
  - ログ設定は kabusys.utils.logging_setup.setup_logging により統一

---

## 開発向けメモ

- DuckDB を用いる研究・ファクター計算関数は duckdb 接続を受け取る設計なので、単体テストで簡単にモックや一時 DB を差し替え可能です。
- OpenAI 呼び出しはモジュール内でラップされており、テスト時は該当関数を patch してスタブ化できます（例えば `_call_openai_api` をモック）。
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml を探す）を基準に行われます。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `kabusys.monitoring.monitoring_db.init_monitoring_db` は冪等で、既存 DB へのマイグレーション（カラム追加）を行います。

---

## ディレクトリ構成

（src/kabusys 以下の主なファイル/モジュール）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - config_setup.py                — 対話式 .env ウィザード
  - validate_config.py             — 起動前の設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py         — 候補選定 / 重み計算
    - position_sizing.py           — 株数 (lot) 算出・集約キャップ
    - risk_adjustment.py           — セクター上限 / レジーム乗数
  - monitoring/
    - monitoring_db.py             — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py         — 複数 Monitor を束ねる
    - system_monitor.py            — システム状態 / データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 書き込みロジック
    - (trade_monitor.py, alert_manager.py などが参照されます)
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory, RiskManager 等 — 実行ロジック)
  - research/
    - factor_research.py           — モメンタム/ボラ/バリュー等
    - feature_exploration.py       — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — レジーム判定（ma200 + macro sentiment）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

備考: 実行時に参照される追加ファイル（config/*.yaml, data/*.db 等）はプロジェクトルートに配置されます。

---

## よくある運用注意

- KABUSYS_ENV=live の場合は特に LINE 通知や Kill Switch の設定を慎重に行ってください（validate_config で警告が出ます）。
- Paper trading モードは本番 DB と分離されます。ペーパーデータは `PAPER_TRADING_SQLITE_PATH` に保存されます。
- OpenAI API 呼び出しはレート制限・ネットワークエラー対策のリトライロジックを含みますが、API キーの漏洩や料金に注意してください。
- ログディレクトリ作成に失敗した場合はコンソールにワーニングが出てファイル出力が無効化されます。

---

必要があれば README にサンプル .env テンプレートや起動用 systemd / supervisord の Unit ファイル例、CI 用のテスト手順などを追加できます。どの情報を追加しますか？