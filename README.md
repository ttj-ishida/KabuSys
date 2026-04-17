# KabuSys

日本株自動売買システムのコアライブラリ / ランタイムコンポーネント群です。  
このリポジトリには、ExecutionEngine（発注実行）・監視（Monitoring）・研究用ファクター計算・AI ベースのニュース解析などの実装が含まれます。

## プロジェクト概要
KabuSys は日本株の自動売買を実行・監視・検証するためのモジュール群です。主な設計方針は以下の通りです。

- 本番・ペーパートレードを環境変数で切り替え可能（`KABUSYS_ENV`）。
- 発注ロジック（ExecutionEngine）と監視（Monitoring）は独立して動作。
- DuckDB を用いた分析用データ（prices_daily など）と、SQLite を監視/履歴用に使用。
- OpenAI を用いたニュース NLP / レジーム判定をサポート（API キー必須）。
- .env による設定管理 + 対話式ウィザード / 設定検証ツールを提供。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution）
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い paper_trading DB に記録（本番 DB と分離）。
  - PID 管理、停止フラグの監視（data/stop_requested.flag 等）。
- Monitoring（監視）関連
  - システム状態監視（CPU/MEM/DISK、プロセス生存確認、データ鮮度）
  - 注文滞留・約定異常チェック
  - ドローダウン・ポジション上限監視（KillSwitch で Execution を停止可能）
  - 監視ログ永続化（SQLite）
  - 監視ループ起動スクリプト（run_monitoring）
- 研究 / ファクター計算（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額／スコア加重、リスクに基づく株数計算、セクター制約、レジーム乗数
- AI 機能（ai）
  - ニュースのセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（ETF MA + マクロニュース + LLM）
- ツール
  - ペーパートレード検証レポート生成（tools/paper_verification_report）
- 設定管理
  - .env 対話式作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

## 前提 / 必要条件
- Python 3.10 以上（ソースで `X | Y` 型注記を利用）
- 主な Python パッケージ（必要に応じて）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定検証で YAML を検証したい場合）
- OS: Linux / macOS / Windows（process priority 設定は一部 OS で限定的）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトの requirements.txt がある場合はそれを利用してください）

## セットアップ手順（基本）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール
3. .env を作成
   - 対話式ウィザードで作成する:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` は必須）
4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. DuckDB / SQLite ファイルの配置（デフォルトは data/ 配下）
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db（`KABUSYS_ENV=paper_trading` 時に使用）
   これらは自動で作成されることがありますが、権限やディレクトリがない場合に警告が出ます。

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

その他主要:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI を用いる機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring で使用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 実行時に kill flag を自動クリアするか（"1" で有効）

注意: `.env` は絶対に Git へコミットしないでください。

## 使い方（実行例）
- ExecutionEngine を起動（デフォルトで Settings に従う）
  ```bash
  # 例: 本番環境（実際に発注されます）
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

  # 例: ペーパートレード（Mock Broker を使用、DB は data/paper_trading.db）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 起動時に `data/execution.pid`（デフォルト）が作成されます。停止には kill flag（data/kill.flag）や stop_requested.flag を使用できます（下記参照）。

- Monitoring を起動
  ```bash
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番の sqlite_path を使って監視ログを書きます（`Settings` に従う）
  - 終了 / 停止: `data/stop_requested.flag` を作成するとループは検知して終了します（run_monitoring/run_execution 両方で検出）。

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB を明示的に指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（`OPENAI_API_KEY`）が必要です。
  - プログラム的に呼び出す:
    ```python
    from kabusys.ai import score_news
    # duckdb_conn は duckdb.connect(...) で生成
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```

## 停止 / Kill の扱い
- run_execution / run_monitoring はプロセス外部からの停止フラグ（data/stop_requested.flag）を監視して安全に終了します。
- KillSwitch（監視モジュール）は `data/kill.flag` を書き込むことで ExecutionEngine に停止を促します。これによりリスクルール（例: ドローダウン閾値超過）で自動停止できます。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill flag を自動でクリアする設定になります（本番では推奨されません）。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数 / Settings
  - config_setup.py          : .env 対話式ウィザード
  - validate_config.py       : 設定検証 CLI
  - run_execution.py         : ExecutionEngine 起動スクリプト
  - run_monitoring.py        : SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py    : プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       : SQLite 監視ログ永続化層
    - system_monitor.py      : システム / データ鮮度監視
    - trade_monitor.py       : 注文滞留 / 約定異常監視
    - risk_monitor.py        : ドローダウン / ポジション制限監視
    - kill_switch.py         : Kill Switch 実装（flag 書き込み）
    - monitoring_engine.py   : 各 Monitor を束ねるエンジン
    - alert_manager.py       : （アラート送信の管理、未表示の詳細実装）
  - execution/                : Execution 系（OrderManager, ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     : モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py : 将来リターン / IC / 統計解析
  - ai/
    - news_nlp.py            : ニュース NLU スコアリング（OpenAI）
    - regime_detector.py     : レジーム判定（ETF MA + マクロ NLP）
  - tools/
    - paper_verification_report.py
  - data/                    : 実行時に使用する DB / フラグ / PID 等（デフォルト）

（上記は主要ファイルの抜粋です。実際のツリーはさらにサブモジュールや補助スクリプトを含みます）

## 開発・デバッグのヒント
- DB ファイルを直接確認してログやテーブル内容を確認できます（SQLite / DuckDB）。
- research モジュールは DuckDB 接続を受け取り SQL で完結するため、分析/検証が容易です。
- AI 呼び出しは外部 API に依存するため、テスト時は該当呼び出し関数をモックすることを推奨（コード内で _call_openai_api を分離している箇所が多い）。
- プロセス優先度や CPU affinity 設定は OS に依存するため、権限不足で警告が出ることがありますがフェールセーフになっています。

## ライセンス / 注意事項
- .env に含まれるシークレット（API キー・パスワード等）は決してリポジトリにコミットしないでください。
- 本番環境（`KABUSYS_ENV=live`）での運用は十分な理解と試験の上で実施してください。自動発注システムの運用はリスクを伴います。

---

不明点や README に追加してほしい使用例（ExecutionEngine のデバッグ方法や特定の設定例など）があれば教えてください。README を拡張して手順や具体的なコマンド例を追加します。