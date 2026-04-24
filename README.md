# KabuSys — README

KabuSys は日本株向けの自動売買・リサーチ基盤です。  
このリポジトリには実行エンジン、監視コンポーネント、ポートフォリオ構築、ファクター計算、LLM を使ったニュース解析等のモジュールが含まれます。

以下はプロジェクトの概要、機能、セットアップと使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

- 自動売買の実行エンジン（ExecutionEngine）とそれを監視する Monitoring（System / Trade / Risk Monitor）を提供します。
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）、リスク調整ロジックを純粋関数として実装しています（ユニットテストしやすい設計）。
- DuckDB を使ったリサーチ用ファクタ計算（momentum, volatility, value など）と、DuckDB を DB 層として利用する設計。
- OpenAI（gpt-4o-mini）を用いたニュース NLP によるセンチメント評価や市場レジーム判定機能を内包。
- Paper Trading モードをサポートし、本番 DB と分離された専用 SQLite に記録できます。

---

## 主な機能一覧

- 実行系
  - ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
  - Broker クライアントファクトリ（本番 / モックの切り替え）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）: MockBrokerClient を使用し `data/paper_trading.db` に記録

- 監視系
  - SystemMonitor：CPU/メモリ/Disk・プロセス生存・データ鮮度をチェック
  - TradeMonitor：注文の滞留 / 約定異常などを検知
  - RiskMonitor：ドローダウンやポジション上限を監視し必要時にログ／Kill Switch を発動
  - MonitoringEngine：上記をポーリングしてアラートや kill.flag 書き込みを行う
  - SQLite ベースの監視 DB（monitoring_db）

- ポートフォリオ
  - 候補選定（score/rank ソート）
  - 重み付け（等分配／スコア加重）
  - ポジションサイズ計算（リスクベース、上限・単元考慮）
  - セクターキャップ適用、レジーム倍率

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（LLM）
  - ニュース NLP（news_nlp.score_news）：記事を集約して OpenAI に投げ、ai_scores テーブルへ格納
  - レジーム判定（regime_detector.score_regime）：ETF の MA とマクロ記事センチメントを合成して market_regime に書き込み
  - OpenAI API のキーは環境変数 `OPENAI_API_KEY` で指定

- CLI / ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - 監視プロセス起動: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

- ユーティリティ
  - 統一的なロギング設定（logs/<app>.log、日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発 / 実行）

以下は一般的な手順です。環境や OS に合わせて適宜調整してください。

1. リポジトリをクローンしてソースルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - または最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config で YAML の検証をしたい場合）
     - （SQLite は標準ライブラリで利用可）

4. .env を用意
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）

   - 自動ロード: デフォルトでプロジェクトルートの `.env` / `.env.local` を起動時に読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DB / ディレクトリの作成
   - 実行スクリプトが必要な親ディレクトリ（data/, logs/）を自動作成しますが、必要に応じて手動で作成してください。

---

## 基本的な使い方（実行例）

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（Engine）起動
  - 本番/開発/ペーパートレードは `KABUSYS_ENV` を設定
  - Paper Trading の場合、MockBrokerClient が使用され `PAPER_TRADING_SQLITE_PATH` に書き込みます
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- 監視プロセス起動
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可
  - 監視は常に（環境にかかわらず）`Settings.sqlite_path`（デフォルト data/monitoring.db）を使用します
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 強制停止（Kill Switch / stop フラグ）
  - 実行停止を外部から指示するにはプロジェクトの data ディレクトリにフラグファイルを書きます:
    - 実行系停止を要求する stop フラグ: data/stop_requested.flag（run_* スクリプトが監視）
    - ExecutionEngine を停止する「kill.flag」は KillSwitch が生成します（場所は Settings.kill_flag_path、デフォルト data/kill.flag）
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると、起動時に kill.flag を自動クリアします（本番では推奨しません）

- Paper Trading の検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` オプションで指定

- AI 機能を使う場合
  - OpenAI API キーをセット:
    ```
    export OPENAI_API_KEY="sk-..."
    ```
  - news_nlp.score_news や regime_detector.score_regime を呼び出すスクリプト／ジョブを実行

---

## 重要な環境変数とデフォルト

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- OPENAI_API_KEY: LLM 機能を利用する場合に必要
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB、監視プロセスは常にこちらを使用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（Paper Trading 用）
- LOG_LEVEL: INFO（デフォルト）
- LOG_DIR: logs/（ログ保存先）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の成行約定挙動）

---

## ログ・監視・プロセス

- ロギング: kabusys.utils.logging_setup.setup_logging が全スクリプトから呼ばれます
  - 出力先: stdout とファイル（logs/<app_name>.log 日次ローテーション、30日保持）
  - ログディレクトリの作成に失敗した場合はコンソール出力のみになります（警告が表示されます）

- プロセス優先度: run_* スクリプトは起動時に set_process_priority("high") を呼び、可能なら優先度を上げます（psutil を利用）

- フラグファイル:
  - data/stop_requested.flag: run_monitoring / run_execution が存在を監視して停止
  - data/execution.pid: ExecutionEngine の PID ファイル（Settings.pid_file_path）
  - data/kill.flag: KillSwitch が生成して ExecutionEngine に停止シグナルを送る

---

## ディレクトリ構成（主要ファイル）

概略ツリー:

```
src/
  kabusys/
    __init__.py
    config.py
    config_setup.py
    validate_config.py
    run_execution.py
    run_monitoring.py

    execution/        # 実行エンジン関連（broker, engine, order_manager, risk_manager 等）
      ...

    monitoring/
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      ...

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/
      news_nlp.py
      regime_detector.py
      __init__.py

    tools/
      paper_verification_report.py
      __init__.py

    utils/
      logging_setup.py
      process_priority.py
      __init__.py

config/
  system_config.yaml
  data_config.yaml
  strategy_config.yaml
  risk_config.yaml
  execution_config.yaml
  monitoring_config.yaml

data/      # 実行時に使用する DB / フラグ / pid 等（デフォルト）
logs/      # ログ出力先（デフォルト）
```

（実際のサブモジュール・ファイルは上記ツリー内に多数あります。詳細はソースを参照してください。）

---

## 開発・運用上の注意点

- モジュール設計は「本番 DB とペーパートレード DB を分離する」ことを想定しています。Paper Trading を利用する際は必ず `KABUSYS_ENV=paper_trading` を設定してください。
- 監視プロセス（run_monitoring）は、環境にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視ログは本番監視 DB に記録されます。
- .env の自動読み込み:
  - 起動時にプロジェクトルートの `.env` / `.env.local` を自動ロードします（OS 環境変数が優先）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
- OpenAI 等外部 API を利用する機能は、API の失敗を想定してフェイルセーフに実装されています（リトライやフォールバック値あり）。
- ローカルでのテストや CI では環境変数のモックや `KABUSYS_DISABLE_AUTO_ENV_LOAD` の利用を検討してください。

---

## トラブルシューティング（よくある項目）

- ログファイルが作成されない / ファイルハンドラのエラー:
  - `LOG_DIR` の権限やパスを確認。作成に失敗すると stdout のみ出力される設計です。
- .env の値が読み込まれない / テストで環境を上書きしたい:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動ロードを無効化し、必要な環境変数を明示的に設定する。
- ExecutionEngine がすぐ停止する / kill.flag が常に存在する:
  - `KILL_FLAG_CLEAR_ON_START` の設定や `data/kill.flag` を確認。起動前に不要な kill.flag が残っていると起動不能になります（ウィザードでの初期設定に注意）。

---

この README はリポジトリの主要な使い方・構成を簡潔にまとめたものです。詳細な設計仕様やアルゴリズム（PortfolioConstruction.md、StrategyModel.md 等）が別ドキュメントにある想定なので、実装や運用時はそれらの設計ドキュメントも参照してください。必要があれば README に更に具体的な運用手順や例を追加します。