# KabuSys

日本株向け自動売買システムのコアライブラリおよび起動スクリプト群です。本リポジトリは取引実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ・ファクター計算、AI を使ったニュースセンチメント評価などの主要機能を持ちます。

---

## 概要

- Python パッケージ形式で実装された自動売買システムの主要コンポーネント群。
- DuckDB / SQLite を用いた時系列データ・ログ保存、監視 DB。
- 実行環境（本番 / ペーパートレード / 開発）に応じた挙動切替。
- OpenAI を用いたニュース NLP（センチメント）やレジーム判定機能（任意）。
- ポートフォリオ構築、位置サイズ計算、リスク調整の純粋関数群を提供。
- コマンドラインの環境セットアップウィザードと設定検証ツールを同梱。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（paper_trading モードでは MockBroker を使用）
  - 注文管理、リスク管理、照合（reconciler）などの実装骨格
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - system_status / trade_logs / risk_logs / dashboard / positions の永続化（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み Execution を停止）
  - run_monitoring.py によるポーリングループ起動
- Research / Factors
  - momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - forward returns, IC（Spearman）計算、統計サマリ
- Portfolio
  - 候補選定、等ウェイト・スコア重み、リスクベースのポジションサイズ計算
  - セクター制限（sector cap）とレジーム乗数
- AI（任意）
  - OpenAI を用いたニュースセンチメントスコアリング（kabusys.ai.news_nlp）
  - マクロ＋ETF MA の合成による市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - .env 対話式生成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 動作前提 / 必須要件

- Python 3.10 以上（PEP 604 の | 型ヒント等を使用）
- 推奨ライブラリ（最低限）：
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を利用する場合）
- これらはプロジェクトの requirements.txt にまとめることを推奨します。

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存関係をインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数の初期設定（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは .env を生成／上書きします。
   - 主要な必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - AI 機能を使う場合は OPENAI_API_KEY を環境変数に設定してください（ウィザードでは扱っていません）。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

---

## 環境変数（主なものとデフォルト）

- 必須（例）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB / ファイル
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
- ログ関連
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - LOG_DIR: logs/
- Monitoring
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
- AI
  - OPENAI_API_KEY（news_nlp / regime_detector 用）
- その他
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定挙動、デフォルト instant）

注: Settings モジュールは起動時に .env / .env.local を自動ロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 基本的な使い方（起動コマンド）

- 監視ループ（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings に基づく sqlite_path（監視 DB）と duckdb を使用します。
  - 停止: ワークスペース内に data/stop_requested.flag が作られるとループを抜けます。

- 実行エンジン（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag の作成で検知します。

- .env 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite ファイルパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

---

## ログ

- ログはデフォルトで stdout に出力され、ファイルにも日次ローテーションで保存されます（logs/<app_name>.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging により統一されています。
- LOG_LEVEL / LOG_DIR で制御できます。

---

## ファイルベースの制御・フラグ

- 停止フラグ:
  - data/stop_requested.flag — スクリプトがループ終了を検知するための旗（run_monitoring / run_execution が参照）
- Kill Switch:
  - data/kill.flag — KillSwitch が書き込むと ExecutionEngine に停止シグナルを与える用途
- PID:
  - data/execution.pid — Execution エンジンの PID を記録

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要なファイル/ディレクトリ（src/kabusys 配下）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / .env 自動読み込みと Settings
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py           — ログ設定ユーティリティ
      - process_priority.py        — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, ...）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py                 — OpenAI を用いたニュースセンチメント
      - regime_detector.py          — 市場レジーム判定
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py

- config/
  - system_config.yaml (期待されるがプロジェクトにより生成)
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

（上記 YAML ファイルは validate_config で存在チェック・パース検証が行えます。PyYAML 未導入時はパース検証はスキップされます。）

---

## 注意事項 / 運用ヒント

- 本番運用（KABUSYS_ENV=live）では特に以下に注意してください：
  - LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の設定
  - KILL_FLAG_CLEAR_ON_START は 0 推奨（1 にすると起動時に kill.flag が自動クリアされます）
  - validate_config で警告・エラーを事前にチェックすること
- Paper Trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 関連機能（news_nlp, regime_detector）は API キーが必須で、API 呼び出しのリトライ・エラーハンドリングを実装しています。API 使用量やレート制限に注意してください。
- DB マイグレーション：monitoring_db.init_monitoring_db は冪等で、既存 DB に対して必要なカラム（例: peak_value, latency_ms）がない場合は追加します。

---

## トラブルシューティング

- .env が自動ロードされない場合:
  - プロジェクトルート検出に失敗している可能性あり（.git または pyproject.toml を探索）。必要なら環境変数を直接 export してください。
  - 自動ロードを無効化しているか確認: KABUSYS_DISABLE_AUTO_ENV_LOAD
- 権限やファイル作成失敗:
  - logs/ や data/ の作成に失敗するとファイルログが無効化され stdout のみになります。パーミッションを確認してください。
- psutil の呼び出しで AccessDenied が出る場合は、優先度設定や CPU affinity が管理者権限を要求している可能性があります。警告が出ますが処理自体は継続します。

---

必要に応じて README にさらに詳細（API ドキュメント、ユースケース別起動手順、設計ドキュメントへのリンクなど）を追加できます。どのセクションを拡張したいか教えてください。