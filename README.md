# KabuSys — 自動日本株トレード基盤（README）

この README はコードベースの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

※ 本リポジトリは Python パッケージ `kabusys` を想定しています。以下ではパッケージルートをプロジェクトルート（`pyproject.toml` や `.git` のある場所）とします。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコアライブラリ群です。  
主な役割は以下の通りです：

- 信号生成・ポートフォリオ構築（research / portfolio）
- 発注エンジン（execution）※実際のブローカー or ペーパートレード分離
- 実行状況・リスク監視（monitoring）
- ニュース NLP によるセンチメント評価（AI モジュール）
- Paper Trading 検証レポート生成ツール（tools）
- 環境設定ウィザード・設定検証（config_setup / validate_config）
- ロギング・プロセス優先度などのユーティリティ（utils）

設計上の特徴：
- DuckDB を用いた分析用データ（prices_daily 等）
- SQLite を簡易ログ / 監視 DB に利用（monitoring.db / paper_trading.db）
- 実環境（live）・ペーパートレード（paper_trading）・開発（development）を切替可能
- OpenAI を用いたニュース NLP / レジーム判定機能（API キーが必要）

---

## 機能一覧

主な機能（抜粋）：

- 環境・設定管理
  - .env ウィザード生成（python -m kabusys.config_setup）
  - 起動前の設定検証（python -m kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine を起動するエントリ（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper DB に記録（完全分離）
  - PID / stop flag 管理（data/execution.pid、data/stop_requested.flag）

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン
  - 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - kill.flag による安全停止機構（デフォルトパス: data/kill.flag）
  - 監視ログ永続化（SQLite: monitoring.db）

- ポートフォリオ関連（純粋関数)
  - 候補選定、等金額/スコア加重配分
  - セクターキャップ、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め・リスクリミット適用）

- 研究・解析
  - Momentum / Volatility / Value 等ファクター算出（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）
  - ニュースを集約して LLM でセンチメントスコア化（ai.news_nlp）
  - マクロニュース + ETF MA で市場レジーム判定（ai.regime_detector）
  - OpenAI API リトライ・バリデーション・結果書き込みロジックを備える

- ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローンする（例）:
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. Python 仮想環境を作成・有効化（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必須依存パッケージをインストール（少なくとも以下が必要です）:
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（config YAML 検証用）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

   注: 実プロジェクトでは requirements.txt / pyproject.toml に依存関係が記載されている想定です。存在する場合はそれに従ってください。

4. .env を作成する:
   - 対話式ウィザードで作成
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成する（.env.example を参照）。

5. 設定の検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになる
   python -m kabusys.validate_config --strict
   ```

6. DB / ディレクトリの準備:
   - デフォルトで以下のパスが使用されます（環境変数で上書き可能）
     - DuckDB: data/kabusys.duckdb  (環境変数: DUCKDB_PATH)
     - SQLite (監視): data/monitoring.db (SQLITE_PATH)
     - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
   - ログディレクトリ: logs/（LOG_DIR で変更可）

---

## 使い方（主要コマンド）

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 監視（Monitoring）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。0 以下の値は無効でデフォルトにフォールバックします。

  - 監視は Settings.env にかかわらず、本番の sqlite_path（SQLITE_PATH）を使用して monitoring テーブルを初期化します。

  - 実行中にプロセス停止をしたい場合はプロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します（または Ctrl+C）。

- 発注エンジン（Execution）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV による動作:
    - development: 開発用（発注なし）
    - paper_trading: MockBrokerClient を使用。発注ログは `data/paper_trading.db` に記録（本番 DB と分離）
    - live: 実ブローカーで発注（要設定）
  - Execution 側も `data/stop_requested.flag` をチェックしており、存在すれば起動を行わず終了します。
  - Execution 用 PID ファイル: `data/execution.pid`（Settings.pid_file_path）

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。
  - 期間指定は YYYY-MM-DD 形式。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定する必要があります（または関数に api_key を渡す実装）。
  - ニューススコアリング:
    - プログラム単位で使用する場合は `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)` を呼び出します。
  - レジーム判定:
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意事項：
- `set_process_priority("high")` がスクリプト起動時に呼ばれます。環境により権限不足で警告が出ることがあります（問題ない場合はスキップされます）。
- ロギングは統一ユーティリティ `kabusys.utils.logging_setup.setup_logging(app_name=...)` を使用し、`logs/<app_name>.log` に日次ローテーションで保存されます。出力先は環境変数 `LOG_DIR` で変更可能。

---

## 主要環境変数

必須（起動前に設定が必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant, partial, never, reject）

その他は `.env.example` を参照してください（プロジェクトに存在する場合）。

---

## 停止・Kill Switch の仕組み

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py / run_execution.py などはループ中にこのファイルの存在をチェックします。ファイルが存在すると安全にループを抜け終了します。

- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）
  - KillSwitch により重大なリスク（例: ドローダウン閾値超過、ポジション上限超過）を検出した場合に書き込まれます。
  - ExecutionEngine は kill.flag の存在を検出すると停止する設計です。
  - 設定 KILL_FLAG_CLEAR_ON_START により起動時に自動でクリアする挙動を制御できます（本番では無効を推奨）。

---

## ログ

- 標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。ファイルは日次ローテート、30 日分保持されます。
- ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一されています。

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの抜粋（src/kabusys 配下）。実際の構成はプロジェクトにより若干異なる可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数 / Settings 管理
    - config_setup.py             — .env 対話式ウィザード
    - validate_config.py          — 設定検証 CLI
    - run_monitoring.py           — 監視ループ起動スクリプト
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py        — 市場レジーム判定（MA + LLM）
    - research/
      - __init__.py
      - factor_research.py        — Momentum/Volatility/Value 等
      - feature_exploration.py    — forward return / IC / summary
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - monitoring/
      - monitoring_db.py          — SQLite テーブル初期化 / ラッパ
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py          — （コードベースに含まれる想定のモジュール）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py          — （通知管理、実装想定）
    - utils/
      - __init__.py
      - logging_setup.py          — ロギング初期化
      - process_priority.py       — プロセス優先度 / CPU affinity 設定
    - execution/
      - execution_engine.py       — 発注エンジン本体（想定）
      - broker_factory.py         — ブローカークライアント生成
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/, portfolio/, research/, ai/ ...（詳細は上記）

---

## 開発上の注意・ベストプラクティス

- .env は絶対にリポジトリにコミットしないこと（config_setup.py のヘッダにも注記あり）。
- 本番環境（KABUSYS_ENV=live）では kill スイッチ等の設定を慎重に確認すること（validate_config は live 時にアラートを出す）。
- Paper trading は本番 DB と完全に分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 利用時は API キーの管理に注意する（環境変数または安全なシークレット管理を推奨）。

---

## 参考コマンドまとめ

- ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 監視起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードから抽出できる仕様・使い方を中心にまとめています。実際の運用や追加の設定はプロジェクトのドキュメント（Documentation / README の他ファイル）や config/ 以下の YAML を参照してください。質問や補足があれば教えてください。