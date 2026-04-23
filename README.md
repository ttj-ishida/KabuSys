# KabuSys

日本株向け自動売買システムのコードベース。ポートフォリオ構築、発注実行、監視、リサーチ、AI（ニュースNLP / レジーム判定）などのコンポーネントを含みます。

## プロジェクト概要
KabuSys は日本株自動売買を想定したモジュール群です。主な目的は以下です。

- 戦略に基づくシグナルからポートフォリオを構築し、発注数量を決定する（portfolio）。
- ブローカークライアントを通じて発注を実行する実行エンジン（execution）。`paper_trading` 環境ではモックブローカーにより実際の注文とは分離して動作します。
- システム状態・データ鮮度・取引ログ等を継続監視し、閾値超過でアラートや Kill Switch を発動する（monitoring）。
- DuckDB を使ったファクター計算やリサーチ用ユーティリティ（research）。
- OpenAI を利用したニュースのセンチメント評価やマクロセンチメントを使った市場レジーム判定（ai）。
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証など）。

バイナリや外部サービスへの直接依存を最小化し、設定は .env ファイル（または環境変数）で行います。

## 機能一覧
- 設定管理
  - Settings クラスで環境変数を型付きで取得
  - .env / .env.local 自動ロード（無効化可能）
  - 対話式設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 実行エンジン（ExecutionEngine 起動スクリプト）
  - 本番 / ペーパー取引の DB 分離（PAPER_TRADING 用 SQLite）
  - ブローカー抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）、注文管理、再整合（Reconciler）
- 監視（Monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存チェック / データ鮮度
  - TradeMonitor：注文ログの異常検出（滞留注文、異常約定など）
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：フラグファイルを書き込んで Execution を停止させる仕組み
  - monitoring_engine による統合ポーリングループ
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベースポジション決定
  - セクター上限、レジーム乗数（bull/neutral/bear の考慮）
- リサーチ
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores に書き込む
  - マクロニュース + ETF MA を使った市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
- ロギング・運用支援
  - 共通の logging 設定ユーティリティ（TimedRotatingFileHandler を使用）
  - process_priority による優先度設定
  - PID / stop/kill フラグファイルで外部から停止制御が可能

## 前提（依存パッケージ）
（最低限）
- Python 3.9+（typing 表記に依存）
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（設定 YAML 検証を行う場合、任意）

インストール例:
```bash
python -m pip install duckdb psutil openai PyYAML
```
（AI 機能を使わない場合は openai は不要。PyYAML も任意。）

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール（上記参照）
4. 初期設定（.env の作成）
   - 対話式ウィザードを実行して .env を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動で .env を用意。
   - 自動ロードは既定で有効。自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告もFAIL扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ / ログディレクトリ
   - デフォルトで `data/` と `logs/` を使用します。`LOG_DIR` 環境変数でログ出力先を変更可能。
   - 実行時にディレクトリがなければ自動で作成する箇所がありますが、権限等に注意してください。

### 重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能利用時）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO）
- LOG_DIR（ログ出力ディレクトリ）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動でクリアするか。0/1）

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、モックブローカーが使用され、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- 監視プロセス起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用します（環境にかかわらず）。
  - 停止フラグ: data/stop_requested.flag を配置するとループが停止します。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング（プログラムから呼び出す）:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キーが必要（引数で渡すか環境変数 OPENAI_API_KEY を設定）。

- ロギング:
  - setup_logging(app_name="execution") を各起動スクリプトで呼んでいるため、`logs/<app_name>.log` に日次ローテートで出力されます。
  - LOG_LEVEL / LOG_DIR で出力レベル・先を変更可能。

### Kill Switch / Stop 制御
- Kill Switch の書き込み対象ファイル（デフォルト）: data/kill.flag（Settings.kill_flag_path）
  - KillSwitch は RiskMonitor の結果等に基づき kill.flag を書き込むことで Execution の停止をトリガーします。
- 外部から即時停止を要求する場合は:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループは停止します。
- 起動時に既存の kill.flag を自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1（本番では 0 推奨）。

## ディレクトリ構成（抜粋）
（リポジトリの src/kabusys 配下を簡易的に示します）

- src/kabusys/
  - __init__.py
  - config.py                — 設定読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/               — 発注エンジン関連（broker, engine, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

- config/                    — 各種 YAML 設定ファイル（system_config.yaml 等、生成/管理）
- data/                      — デフォルト DB やフラグファイル（data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag など）
- logs/                      — ログ出力先（LOG_DIR で変更可）

## サンプル .env（最小）
以下は .env に必要な主要項目の例（実運用時は secrets を適切に設定し Git 管理外にしてください）。

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

KABUSYS_ENV=development
LOG_LEVEL=INFO

OPENAI_API_KEY=sk-...
```

## 運用上の注意
- 本番環境（KABUSYS_ENV=live）では kill.flag / KILL_FLAG_CLEAR_ON_START 等の設定に注意してください。validate_config は live 時に追加警告を出します。
- OpenAI を使った処理は外部 API に依存するため、失敗やレートリミット、結果の妥当性に備えたフェイルセーフが設計されていますが、運用監視を推奨します。
- DB（特に本番の monitoring.db）はバックアップとアクセス権限管理を行ってください。
- 実際に資金を動かす場合は paper_trading で十分に検証した上で live 運用へ移行してください。

---

何か追加したいセクション（例: API ドキュメント、ユニットテスト、具体的な起動 & systemd / cron の設定例など）があれば教えてください。README に追記します。