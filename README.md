# KabuSys

日本株向け自動売買システム（ライブラリ/実行スクリプト群）の README（日本語）

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・研究ツール・AI 補助機能を含むモジュール群を提供します。  
以下はコードベースの概要、主要機能、セットアップと使い方、ディレクトリ構成の説明です。

※ 本ドキュメントはソース内の docstring・コメントに基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するコンポーネント群です。主な役割は以下:

- データ格納・分析（DuckDB）
- ポートフォリオ構築（候補選定 / 重み付け / 株数計算）
- 発注処理（ExecutionEngine。paper_trading は MockBroker で分離）
- システム監視（System/Trade/Risk モニタ）と Kill Switch
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュースを LLM でスコア化する AI モジュール（OpenAI）
- CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成 など）

設計方針の要点:
- 本番 DB とペーパートレード DB は原則分離（環境に応じた sqlite パス切替あり）
- ルックアヘッドバイアス防止のため日付参照方法に配慮
- フェイルセーフ（API失敗時のフォールバック、部分失敗時の DB 保護 等）

---

## 機能一覧（主要モジュール）

- 実行 / 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）

- 設定・検証
  - config_setup.py — .env を対話式に作成/更新するウィザード
  - validate_config.py — 環境変数・config/*.yaml の事前検証 CLI

- 監視
  - monitoring/* — MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, AlertManager など
  - stop / kill フラグにより安全に Execution を停止可能

- 注文/実行関連
  - execution/* — BrokerFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（詳細は該当モジュール）

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 / 等分配 / スコアウェイト
  - portfolio.position_sizing: 単元丸め・リスクベースの株数計算
  - portfolio.risk_adjustment: セクター上限・レジーム乗数

- 研究（Research）
  - research.factor_research: momentum / volatility / value ファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算・IC (Spearman)・統計サマリー

- AI（OpenAI 経由）
  - ai.news_nlp: ニュースを LLM でスコアリングして ai_scores に書き込み（OpenAI API 必須）
  - ai.regime_detector: ETF MA とマクロニュース LLM を組み合わせて市場レジーム判定・保存

- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率・注文成功率・レイテンシなど）

---

## 前提依存パッケージ（推奨）

最低限必要なパッケージ（pip インストール）例:

- duckdb
- psutil
- openai
- PyYAML（config/*.yaml のパース検証を行う場合、必須）
- その他: Python 標準の sqlite3 等

例:
```bash
pip install duckdb psutil openai PyYAML
```

（requirements.txt は本リポジトリに含まれていない想定なので、環境に合わせてパッケージを追加してください）

---

## 環境変数と設定 (.env)

自動ロード:
- デフォルトではプロジェクトルート（.git または pyproject.toml を検出）から .env / .env.local を自動読み込みします。
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB。デフォルト: data/paper_trading.db)
- LOG_LEVEL (INFO 等)
- LOG_DIR (ログの保存先。デフォルト: logs/)
- OPENAI_API_KEY（AI モジュール利用時に必要）
- PAPER_FILL_MODE（paper_trading 時の約定挙動。instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険。デフォルト: 0）

.env は絶対に Git にコミットしないでください（config_setup もその旨注意書きがあります）。

簡易例（.env のサンプル行）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをチェックアウト
2. Python 仮想環境を作成して activate
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参考に手動作成
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL と扱う場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（起動 / 実行）

基本的にモジュールは以下のコマンドで起動します（プロジェクトルートで実行することを想定）。

- ExecutionEngine 起動（デフォルトは KABUSYS_ENV に従う）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、デフォルトで data/paper_trading.db を使用して本番 DB と完全に分離します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書き込みます。

- Monitoring 起動（SystemMonitor のポーリングループ）
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視は環境にかかわらず本番 sqlite_path を使用する（monitoring 用の DB は共通に保管される設計）。
  - data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 系（ニューススコア付与 / レジーム判定）は関数呼び出しベースですが、必要な環境変数:
  - OPENAI_API_KEY をセットしてください。
  - 例: ai.news_nlp.score_news() / ai.regime_detector.score_regime() をスクリプト/ジョブから呼び出す設計。

停止 / Kill Switch:
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時や実行中にこのフラグをチェックして停止します）。
- 手動で解除する場合はファイルを削除:
  ```bash
  rm data/kill.flag
  ```
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では危険なので推奨されません。

ログ:
- デフォルトは logs/ ディレクトリに日次ローテーションで保存（kabusys.utils.logging_setup.setup_logging により設定）。
- 標準出力にも出ます（stdout）。

---

## 実行上の注意点 / 運用メモ

- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）を使って外部から安全に停止できます。運用で使う際は stop フラグの存在を確認してください。
- Monitoring の DB 操作は init_monitoring_db() により冪等にテーブルを作成します。既存 DB 欄のマイグレーション対応も実装されています（列追加等）。
- paper_trading と本番の DB は分離して扱うようにしてください（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API 呼び出しはレート制御・リトライロジックを持ちますが、API キーの管理・コストに注意してください。
- .env の自動ロードは、.env と .env.local の順序で行われ、OS 環境変数が優先されます。テスト環境等で自動ロードを回避したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル/ディレクトリのツリー（src/kabusys 配下）:

```
src/kabusys/
├── __init__.py
├── config.py
├── config_setup.py
├── validate_config.py
├── run_execution.py
├── run_monitoring.py
├── utils/
│   ├── __init__.py
│   ├── logging_setup.py
│   └── process_priority.py
├── monitoring/
│   ├── monitoring_db.py
│   ├── system_monitor.py
│   ├── trade_monitor.py        # (ソースあり)
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   ├── monitoring_engine.py
│   └── alert_manager.py        # (ソースあり)
├── execution/
│   ├── execution_engine.py     # (主要ロジック)
│   ├── broker_factory.py
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── reconciler.py
│   └── risk_manager.py
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── tools/
│   ├── __init__.py
│   └── paper_verification_report.py
└── data/                       # 実行時に作成されることが多い
    ├── monitoring.db           # デフォルト SQLITE_PATH
    ├── paper_trading.db        # PAPER_TRADING_SQLITE_PATH（ペーパートレード）
    ├── kabusys.duckdb         # デフォルト DUCKDB_PATH (別ファイル)
    ├── execution.pid
    ├── stop_requested.flag
    └── kill.flag
```

（実際のリポジトリにはさらにファイル/モジュールがあります。上記は主要部分の抜粋です）

---

## よくある操作例

- .env をウィザードで作成
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Execution の起動（フォアグラウンド）
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring の起動（60秒ごとにチェック）
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 開発者向けメモ

- Settings クラス (config.py) を通してアプリケーション設定へアクセスしてください。settings = Settings() で使用可能です。
- DB 関連は DuckDB（分析）と SQLite（監視/発注履歴）で分割されています。duckdb_conn は大量データ分析向けに使用します。
- logging_setup.setup_logging を各起動スクリプトの最初に呼び出して統一ログ出力を行います。
- process_priority.set_process_priority("high") により、起動スクリプトは優先度を設定しようとします（プラットフォームに依存し、失敗時は警告のみ）。

---

この README はコードのトップレベル説明を目的としています。各モジュールの詳細な使い方や API 仕様については対応ソースファイル（docstring）を参照してください。必要であれば、特定モジュールの詳細なドキュメントを追加で作成します。