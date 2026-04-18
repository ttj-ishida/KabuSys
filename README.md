# KabuSys

日本株自動売買システムのリポジトリ（簡易版）。  
この README はリポジトリの主要コンポーネント、セットアップ、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / 研究用ユーティリティ群を備えたパッケージです。主な機能は以下の通りです。

- 発注・約定管理（ExecutionEngine、OrderManager 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ計算、セクターキャップ）
- 研究・ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI 支援（ニュースセンチメント解析、レジーム判定。OpenAI を利用）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード・設定検証 CLI
- ロギング・プロセス優先度ユーティリティ

設計上のポイント：
- 設定は .env または環境変数から読み込み（自動読み込みはプロジェクトルートが検出できれば有効）
- Paper Trading（KABUSYS_ENV=paper_trading）時は本番 DB と分離して専用 SQLite を使う
- 監視（monitoring）は環境にかかわらず本番用 sqlite_path を参照する（監視専用）

---

## 機能一覧（ハイレベル）

- config: 設定読み込み / Settings クラス、自動 .env 読み込み（無効化可）
- config_setup: 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- validate_config: 起動前の設定検証 CLI（python -m kabusys.validate_config）
- run_execution: ExecutionEngine 起動スクリプト（実際の発注／ペーパートレード切替）
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト
- monitoring: DB 永続化層（SQLite）／各種 Monitor／KillSwitch／Alert 管理
- portfolio: 候補選定、重み計算、ポジションサイジング、セクター制限、レジーム乗数
- research: DuckDB を用いたファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- ai: OpenAI を使ったニュース NLP（score_news）・市場レジーム判定（score_regime）
- tools: ペーパートレード検証レポート生成スクリプト
- utils: ロギング設定、プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件（主な依存）

ソース内の型表記や使用モジュールにより Python 3.10+ を推奨します。主な外部依存：

- duckdb
- psutil
- openai
- （任意）PyYAML（config 検証で YAML のパースを行う場合）
- sqlite3（標準ライブラリ）

推奨インストール例（pip）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

※ 実際の requirements.txt は本リポジトリに含まれていません。環境に合わせて依存を揃えてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <このリポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードに従って J-Quants トークンや kabu API パスワードなどを設定します。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの確認
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/<app>.log
     - kill flag: data/kill.flag
     - stop flag: data/stop_requested.flag
     - execution pid: data/execution.pid

   必要に応じて .env の DU CKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定してください。

---

## 使い方（主要コマンド）

- 実行前に .env を適切に設定してください（必須項目は JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルを送れます。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動でクリアします（本番では 0 を推奨）。

- Monitoring（SystemMonitor）を起動
  ```bash
  # ポーリングループを開始（デフォルト 60 秒間隔）
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を上書き:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視ループは project_root/data/stop_requested.flag を検知すると終了します。
  - 監視は環境にかかわらず本番 sqlite_path を使用してログを永続化します。

- Paper Trading 検証レポート生成ツール
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（ニュースセンチメント / レジーム判定）
  - OpenAI API キーは環境変数 OPENAI_API_KEY で設定するか、関数引数で渡します。
  - モジュール関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行例はプロジェクトの運用スクリプトに合わせて実装してください（直接 CLI は用意されていませんが、上記関数を呼ぶスクリプトは作成可能です）。

---

## 主要環境変数（概要）

必須（少なくとも設定すること）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/上書き可能項目
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（ai モジュールを使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）
- PID_FILE_PATH / KILL_FLAG_PATH などは Settings 経由で取得可能

.env は .env.example を参考に作成してください（config_setup で自動作成できます）。自動 .env 読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 運用上の注意

- Paper Trading は本番 DB と完全に分離するよう設計されています。KABUSYS_ENV=paper_trading を利用してください。
- 監視は常に本番用 sqlite_path を使用するため、監視 DB と運用 DB の扱いに注意してください。
- Kill Switch（data/kill.flag）は ExecutionEngine に停止を促す重要な安全スイッチです。本番での自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は危険なので推奨しません。
- ログは logs/<app>.log に日次ローテーションで出力されます。ログディレクトリの作成に失敗するとコンソール出力のみになります。
- OpenAI API 呼び出しはレート制限や API エラーに対してリトライ・フェイルセーフが実装されていますが、API キーの漏洩やコスト管理には注意してください。

---

## ディレクトリ構成

リポジトリの主要ファイル / 目次（src/kabusys 以下）。一部抜粋：

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（冪等初期化）
    - monitoring_engine.py     — モニタ群を束ねるエンジン
    - system_monitor.py        — システム状態・データ鮮度監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - trade_monitor.py         — （該当ファイルあり）取引監視
    - kill_switch.py           — kill.flag 書込・評価
    - alert_manager.py         — （該当ファイルあり）アラート送信
  - execution/
    - execution_engine.py      — 実行エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュースセンチメント（OpenAI）
    - regime_detector.py        — 市場レジーム判定（OpenAI）
  - data/                      — 実行時に使用するファイル（DB / flag / pid など）

（注）一部ファイルはここに抜粋して示しました。完全なファイル一覧はリポジトリを参照してください。

---

## 開発者向けメモ

- DB スキーマ更新は monitoring_db.init_monitoring_db が冪等に対応しています。マイグレーション的なカラム追加処理も含まれます。
- utils.setup_logging() を全ての起動スクリプトに最初に呼ぶことでログの統一が行われます。
- process_priority.set_process_priority() はプラットフォーム差分（Windows / POSIX）を吸収します。アクセス権限不足時は警告に留まります。
- AI 関連の API 呼び出しはテスト容易性のため _call_openai_api をパッチ可能にしてあります。

---

## ライセンス・貢献

（この README はコードベースの説明用で、ライセンス情報や貢献ガイドラインはリポジトリのルートにある LICENSE / CONTRIBUTING.md を確認してください。）

---

必要であれば、README に実際の .env.example、より詳細な起動例、ユニットテスト実行方法、デプロイ手順などを追記できます。どの情報を優先的に追加しますか？