# KabuSys

日本株向け自動売買システムのコアライブラリ群とユーティリティ群。  
このリポジトリは、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AIベースのニューススコアリング等のコンポーネントを含みます。

## プロジェクト概要
- 自動売買の実行ロジック（発注・リスク管理・約定追跡）と、監視・アラート・Kill Switch を備えた運用基盤。
- DuckDB / SQLite をデータ層に用い、AI（OpenAI）を使ったニュースセンチメント評価やレジーム判定機能を提供。
- 開発／ペーパートレード／本番の環境隔離をサポート（`.env` による設定）。

## 主な機能一覧
- Execution
  - ExecutionEngine を起動して注文発行・注文管理・リスク制御を実行
  - ペーパートレード（`KABUSYS_ENV=paper_trading`）時は MockBroker により本番 DB と分離（`data/paper_trading.db`）
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、Execution プロセス監視）
  - TradeMonitor（滞留注文/約定異常の検出）
  - RiskMonitor（ドローダウンやポジション上限の監視）
  - KillSwitch（条件に応じて `data/kill.flag` を書き、ExecutionEngine を停止）
  - MonitoringEngine による定期ポーリング
- Portfolio
  - 候補選定、等加重／スコア加重、ポジションサイズ計算（単元株丸め含む）
  - セクターキャップ、レジームに応じた乗数適用
- Research
  - ファクター計算（mom, value, volatility 等）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ
- AI
  - ニュース NLP による銘柄別センチメントスコアリング（OpenAI）
  - マクロニュース + ETF MA による市場レジーム判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（console + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report）

---

## セットアップ手順（概略）
1. Python インストール
   - 推奨: Python 3.9+（コードは typing の union 型等を利用）
2. 依存ライブラリをインストール
   - 例:
     ```bash
     pip install duckdb psutil openai
     ```
   - 実行環境に応じて追加で PyYAML（`validate_config` の YAML 検証用）等を入れてください。
3. プロジェクトルート（`.git` または `pyproject.toml` を含む場所）に移動
4. 初期設定（`.env`）の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 完了後、`python -m kabusys.validate_config` で検証を行ってください。
   - `--strict` を付けると警告もエラー扱い（exit code=1）になります。
5. データディレクトリ作成（.env のデフォルト値を使用する場合）
   ```bash
   mkdir -p data logs
   ```
6. （ペーパートレードや AI 機能を使う場合）環境変数の設定
   - `OPENAI_API_KEY`（AI 機能）
   - `KABUSYS_ENV`（development / paper_trading / live）
   - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`（必須）
   - 各パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` 等）

---

## 主要な環境変数（抜粋・デフォルト）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行モード
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- ログ
  - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: logs/
- 監視
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- その他
  - KILL_FLAG_CLEAR_ON_START: 起動時に `kill.flag` を自動クリアするか（0/1）

（`.env` は機密情報を含むため、決して Git にコミットしないでください）

例（簡易）:
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

## 使い方（起動コマンド例）
- 実行エンジン（ExecutionEngine）を起動
  - 本番またはペーパー（env により挙動が変わる）
  ```bash
  python -m kabusys.run_execution
  ```
  - 注意: `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、paper_trading 用の DB を使用します（設定で分離）。
  - 実行中は `data/execution.pid` を作成し、`data/stop_requested.flag` を検出すると終了します。

- 監視ループを起動
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に設定で指定される（本番）`sqlite_path` を使用します（環境に関係なく本番 monitoring DB を参照します）。
  - `data/stop_requested.flag` が存在するとループを終了します。

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config      # 通常モード
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（プログラム呼び出し）
  - 関数としては kabusys.ai.score_news（ニューススコアリング）や kabusys.ai.regime_detector.score_regime が提供されます。API キーを `OPENAI_API_KEY` に設定してください。

---

## 停止／Kill Switch の仕組み
- 管理ファイル
  - data/stop_requested.flag — 起動スクリプトが監視している「停止リクエスト」フラグ（これが存在すると run_* スクリプトは終了する）
  - data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine 側はこれを検出して安全停止するための信号
- KillSwitch は RiskMonitor などの判定結果に応じて `kill.flag` を書き込みます。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアしますが、本番では推奨されません。

---

## ロギング
- 共通のロギング設定ユーティリティ（kabusys.utils.logging_setup）を使用：
  - コンソール（stdout）出力 + 日次ローテートファイル（logs/<app_name>.log）
  - デフォルト保持日数: 30 日
  - 環境変数 `LOG_DIR` や `LOG_LEVEL` で調整可能

---

## ディレクトリ構成（抜粋）
以下はソースツリー中の主要モジュールの構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py         # （実装参照）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         # （実装参照）
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のリポジトリには上記以外の補助モジュールやデータ定義が含まれる可能性があります）

---

## 推奨ワークフロー
1. `.env` を作成（`python -m kabusys.config_setup`）
2. 設定を検証（`python -m kabusys.validate_config`）
3. 必要な DB ファイルを準備（`data/` 配下）
4. まず監視を起動して動作を確認（`python -m kabusys.run_monitoring`）
5. Execution を起動（`python -m kabusys.run_execution`）
6. ペーパートレードで検証 → `tools.paper_verification_report` でレポート生成

---

## 注意事項 / 運用上のヒント
- .env に API キーやパスワード等の機密情報を含めないよう注意し、Git 管理下にコミットしないでください。
- 本番運用時は `KABUSYS_ENV=live` を使用する前に設定検証を入念に行ってください（`validate_config` は live 特有の注意点を警告します）。
- Kill Switch（`kill.flag`）や Stop フラグ（`stop_requested.flag`）の運用ルールを運用チームで明確にしておくことを推奨します。
- OpenAI 経由の機能は API 利用料とレイテンシを考慮してください。失敗時はフェイルセーフ（スコア 0 やスキップ）となるよう実装されていますが、頻繁な失敗は監視対象にしてください。

---

README に書かれていない詳細や各モジュールの API（関数引数や戻り値等）については、該当ソースファイル内の docstring を参照してください。追加でドキュメント化したい箇所があれば教えてください。