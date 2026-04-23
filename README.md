# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプトを含むリポジトリ。  
本READMEはコードベース（src/kabusys 以下）をもとに機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

注意: .env ファイルや API キー等の機密情報は Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買（本番 / ペーパートレード）を想定したモジュール群です。主な要素:

- ExecutionEngine（発注エンジン）とそれに付随する OrderManager / RiskManager / Reconciler 等
- Monitoring（システム稼働監視・データ鮮度・リスク監視・Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- Research（ファクター計算・特徴量解析）
- AI 関連（ニュース NLP による銘柄センチメント評価、レジーム判定）
- 各種ユーティリティ（ロギング設定、プロセス優先度設定等）
- CLI ツール：環境設定ウィザード、設定検証、ペーパートレード検証レポート

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading なら MockBrokerClient を使用して paper_trading DB に記録。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔指定可能（デフォルト 60 秒）。
- 設定管理
  - config.Settings: 環境変数 / .env を読み込み・解釈する中心クラス。KABUSYS_ENV（development / paper_trading / live）を扱う。
  - config_setup.py: .env を対話式で作成・更新するウィザード（python -m kabusys.config_setup）。
  - validate_config.py: 起動前に.env と config/*.yaml を検証する CLI（python -m kabusys.validate_config）。
- 監視
  - monitoring/monitoring_db.py: SQLite を使った監視ログテーブル定義と読み書き層（冪等な初期化・マイグレーションを含む）。
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py：システム状態・注文・リスクをチェックし DB に記録。
  - monitoring/kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る。
  - monitoring/monitoring_engine.py: 各モニタを束ねてポーリングし、AlertManager に通知（AlertManager 実装は別）。
- ポートフォリオ
  - portfolio.portfolio_builder: 候補選定と重み計算（等金額・スコア加重）。
  - portfolio.position_sizing: 発注株数計算（risk_based / equal / score）、単元株丸め、aggregate キャップ適用。
  - portfolio.risk_adjustment: セクター上限・レジーム乗数の適用。
- Research
  - research.factor_research: Momentum / Value / Volatility 等のファクター計算（DuckDB を使用）。
  - research.feature_exploration: 将来リターン計算・IC（情報係数）算出・統計サマリ。
- AI
  - ai.news_nlp: raw_news を LLM（OpenAI）で評価し銘柄ごとの ai_score を生成・保存。
  - ai.regime_detector: ma200 乖離とマクロニュースセンチメントを合成して日次の市場レジームを判定・保存。
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成（稼働率、成功率、レイテンシ等）。

---

## 必要要件（依存パッケージ）

実行に必要な主要パッケージ（最低限の例）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を有効にする場合）
- sqlite3（標準ライブラリ）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（実際の requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動。

2. 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. 環境変数 (.env) を作成:
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ※ .env のデフォルトはプロジェクトルートの .env（config_setup が書き込みます）。
   - 必要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
     - LOG_LEVEL, LOG_DIR, OPENAI_API_KEY（AI を使う場合）

4. 設定を検証:
   ```
   python -m kabusys.validate_config
   # strict モード: 警告も失敗扱い
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じて data/ ディレクトリや logs/ を作成（多くは自動作成されますが、権限に注意）。

---

## 使い方（起動 / 操作）

- ExecutionEngine の起動（実際に発注を行うモジュール）
  ```
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録します。
  - ExecutionEngine は data/stop_requested.flag や data/kill.flag により停止要求を検出します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- Monitoring の起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  挙動:
  - SystemMonitor をポーリングして監視データを SQLite（settings.sqlite_path）に書き込みます。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）。
  - 停止フラグ: data/stop_requested.flag を検知してループ終了。
  - 監視 DB は環境にかかわらず本番 sqlite_path を使用（monitoring は paper_trading と分離しない設計になっています）。

- Monitoring / Execution の停止方法
  - 手動で停止する（CTRL+C）
  - 監視側の KillSwitch が条件を満たすと data/kill.flag を作成（ExecutionEngine は起動時や実行中に kill.flag を検出して停止します）。
  - 外部から停止を要求する場合は data/stop_requested.flag を作成すると両プロセスは検知して終了します。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  レポートは stdout に出力され、稼働率、注文成功率、レイテンシ等を評価します。

- AI 関連（プログラム呼び出し）
  - ニューススコア付与:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date（日付）を渡し、OPENAI_API_KEY を環境変数または引数で指定します。
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI API 呼び出しには OPENAI_API_KEY が必要。失敗時はフェイルセーフ（部分的に 0 やスキップ）を行う設計です。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0/1、デフォルト 0）

---

## ロギング

- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（LOG_DIR 環境変数で変更可）
- デフォルトで 30 日分のログを保持する設定になっています。

---

## 開発メモ / 注意点

- .env 自動ロード: configモジュールはプロジェクトルートに .git または pyproject.toml がある場合、自動で .env / .env.local を読み込みます。テスト等で自動ロードを抑制するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を試みます。
- プロセス優先度: 起動時に set_process_priority("high") を呼びます。プラットフォーム・権限によっては警告が出ますが処理は継続します。
- レイクヘッドバイアス対策: AI / リサーチ系は date.today()/datetime.today() を直接参照しない設計になっており、target_date を明示的に渡すことを推奨します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・ディレクトリのツリー（抜粋）:

```
src/kabusys/
├─ __init__.py
├─ config.py
├─ config_setup.py
├─ validate_config.py
├─ run_execution.py
├─ run_monitoring.py
├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py
│  └─ process_priority.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ monitoring_engine.py
│  ├─ kill_switch.py
│  └─ alert_manager.py  (実装が別ファイルまたは未提供の可能性あり)
├─ execution/
│  ├─ execution_engine.py
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ broker_factory.py
│  ├─ reconciler.py
│  └─ risk_manager.py
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ monitoring/
│  └─ ... (監視関連)
├─ tools/
│  ├─ __init__.py
│  └─ paper_verification_report.py
└─ data/                 (実行時に作成されるデータ・フラグファイル類)
   ├─ monitoring.db       (デフォルト)
   ├─ paper_trading.db
   ├─ kill.flag
   └─ stop_requested.flag
```

（上記はコードベースの一部を抜粋した構成です。実際のリポジトリにはさらにファイルやサブモジュールがあります）

---

## よくある操作コマンドまとめ

- .env を作成:
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
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

以上がコードベース（src/kabusys）に基づく README の概要です。README に追記してほしい具体的な情報（例: 実際の requirements.txt、AlertManager 的確な使い方、ExecutionEngine のコマンド引数仕様など）があれば教えてください。必要に応じてサンプル .env テンプレートや起動例を追加します。