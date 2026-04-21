# KabuSys

日本株自動売買システム（KabuSys）の簡易 README。

このリポジトリは取引エンジン、監視サブシステム、ポートフォリオ構築、リサーチ／ファクター計算、LLM を使ったニュース解析などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定した（実運用／ペーパートレード両対応の）コンポーネント群です。主な目的は：

- シグナル生成 → ポートフォリオ設計 → 発注（ExecutionEngine）
- 実行監視（System / Trade / Risk）と自動停止（Kill Switch）
- DuckDB を用いたリサーチ（ファクター計算・特徴量解析）
- OpenAI（GPT 系）を使ったニュース NLP / レジーム判定
- ペーパートレード検証レポート生成などのユーティリティ

設計方針として、DB 層（SQLite / DuckDB）や外部 API 呼び出しは明確に分離され、フェイルセーフ（API失敗時のフォールバック）を組み込んでいます。

---

## 機能一覧

- Execution
  - ExecutionEngine：発注・リスク管理・再整合化（reconciler）など
  - BrokerClientFactory：実ブローカー or Mock（ペーパートレード）を切り替え
  - Paper trading 用に専用 SQLite（data/paper_trading.db）を使用

- Monitoring / Safety
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存監視
  - TradeMonitor：注文滞留・約定異常などの監視（trade_logs）
  - RiskMonitor：ドローダウン・ポジション数上限の監視、dashboard の更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記をまとめてポーリング、アラート送信（AlertManager 経由）

- Portfolio construction
  - 候補選定、等重/スコア重み、リスクベースの株数計算、セクターキャップ、レジーム乗数等

- Research
  - ファクター計算（momentum/value/volatility 等）
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリー

- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄毎のセンチメントスコアを ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定・永続化

- ユーティリティ / ツール
  - config_setup: .env を対話式に生成・更新
  - validate_config: 起動前の設定検証 (.env / config/*.yaml)
  - paper_verification_report: ペーパートレードログから検証レポートを生成

- ロギング・プロセス管理
  - 統一的なログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発用）

前提
- Python 3.10 以上（typing の | などを使用しているため）
- sqlite3 は標準ライブラリ、外部依存は以下

推奨パッケージ（最低限）
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合に必要）

インストール例（venv を想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
# （プロジェクトを editable install する場合）
pip install -e .
```

環境変数（.env）の作成:
- 対話式ウィザードで生成することを推奨:
  ```bash
  python -m kabusys.config_setup
  ```
- 作成後、設定の妥当性をチェック:
  ```bash
  python -m kabusys.validate_config
  ```
  --strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋・デフォルト）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- PAPER_FILL_MODE（paper_trading の MockBroker の約定挙動: instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト: 60）

注意:
- .env は Git にコミットしないこと。
- validate_config は .env の存在・キー・config/*.yaml の基本的チェックを行います（PyYAML 未インストール時は YAML 検証スキップ）。

---

## 使い方（実行例）

- Execution Engine 起動（通常はプロセス管理ツールで起動）
  - ペーパートレードで起動する例:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実運用（live）では KABUSYS_ENV=live を設定すること。起動時に data/kill.flag をクリアする設定等に注意してください。

- Monitoring 起動（常駐ポーリング）
  ```bash
  # ポーリング間隔を変更する場合（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視ループは data/stop_requested.flag が作られると終了します（管理プロセスから停止させる際に使用）。
  - Monitoring は Settings.sqlite_path（本番 sqlite_path）を常に使用します（環境に依らず）。

- 設定の対話式作成
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定・DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI（ニューススコアリング / レジーム判定）
  - これらはライブラリ関数として提供されています。例:
    ```python
    from kabusys.ai.news_nlp import score_news
    # DuckDB 接続を作成して score_news(conn, target_date, api_key=...)
    ```
  - 実行には OPENAI_API_KEY が必要です。

ログ
- デフォルトで logs/<app_name>.log に日次ローテートで出力されます（例: logs/execution.log, logs/monitoring.log）。
- 標準出力にも出力されます。

停止・フラグ
- 実行ループ（run_monitoring/run_execution）はプロジェクトルートの data/stop_requested.flag を検知して終了します。
- KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine がこれを検出して停止する仕組みです。

---

## ディレクトリ構成（主なファイル）

（src/kabusys をルートとした主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・Settings 管理（.env 自動読み込み等）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （上記 YAML は環境に合わせて生成/編集。存在しない場合は validate_config が警告）

- data/
  - monitoring.db（SQLite、デフォルト: data/monitoring.db）
  - paper_trading.db（ペーパートレード DB、デフォルト: data/paper_trading.db）
  - kill.flag, stop_requested.flag, execution.pid などのフラグ / PID ファイル（プロセス間通信用）

- logs/
  - execution.log, monitoring.log ...（日次ローテーション）

---

## 追加メモ / 注意点

- Monitoring の初期化関数 init_monitoring_db は起動スクリプトから自動で呼ばれ、必要なテーブル・簡易マイグレーションを行います。
- ExecutionEngine は KABUSYS_ENV によって実際のブローカークライアントと DB を切り替えます（paper_trading 時は MockBrokerClient + paper_trading DB）。
- AI 関連は OpenAI API を利用するため API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライ・バックオフやレスポンス検証を組み込んでいますが、API 使用コストに注意してください。
- 設定ファイルや機密情報（API トークン等）は .env に保存し、必ず Git 等にコミットしないでください。

---

必要であれば、README に「起動フロー図」「サンプル .env のテンプレート」や「よくあるトラブルシューティング（ポート問題、権限、psutil のアクセス拒否）」を追加できます。どの情報がさらに必要か教えてください。