# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト群のリポジトリです。  
この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を備えたモジュール群です。

- データ収集・分析（DuckDB を用いたファクター計算 / 研究用ユーティリティ）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制約）
- ExecutionEngine（注文送信・注文管理・リスク管理） — 本番 / ペーパートレードを切替可能
- 監視（System / Trade / Risk の監視、Kill Switch、アラート）
- ニュース NLP（OpenAI を用いたニュースセンチメント評価）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針の一部：
- DB は DuckDB（分析） と SQLite（監視 / 発注ログ）を併用
- Paper Trading は本番 DB と完全分離（専用 SQLite）
- ルックアヘッドバイアスに注意した設計（datetime.today()/date.today() を直接参照しない等）
- フェイルセーフを重視（API 失敗時はフォールバックして継続）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV により MockBroker を使用）
  - run_monitoring.py : SystemMonitor のポーリングループを起動（監視ログの永続化）
- 設定管理
  - config_setup.py : 対話式 .env 作成ウィザード
  - validate_config.py : .env と config/*.yaml の整合性検証
  - Settings クラス（環境変数からアプリ設定を取得）
- 監視
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py
  - MonitoringDB: SQLite を用いた永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py
- 研究・リサーチ
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン・IC・統計サマリ等
- AI（OpenAI）
  - ai.news_nlp: ニュース記事を LLM でスコアリングして ai_scores に書込
  - ai.regime_detector: MA200 とマクロニュースを統合して市場レジーム判定
- 運用ツール
  - tools.paper_verification_report.py : ペーパートレード DB から検証レポートを生成

---

## 要件（推奨）

- Python 3.10+
- 必須ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意 / 推奨:
  - PyYAML（validate_config.py が YAML を検証する場合）
- その他：
  - SQLite（標準ライブラリで対応）
  - ネットワーク接続（kabuステーション API / OpenAI を利用する場合）

インストール例（仮想環境推奨）:
```sh
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際の要件はプロジェクトの packaging / requirements ファイルに合わせてください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成
   - 対話式に作成する場合:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション（例）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード時の DB（data/paper_trading.db）
     - OPENAI_API_KEY — ニュース NLP / レジーム検出に必要
4. 設定検証（オプション）
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合
   python -m kabusys.validate_config --strict
   ```
5. 初期ディレクトリ作成（ログ / data）
   - ログはデフォルトで `logs/` に出力されます（setup_logging が自動で作成を試みます）。
   - データディレクトリ（例: data/）は必要に応じて作成されますが、.env のパス設定に応じて変更してください。

---

## 使い方（起動コマンド例）

起動はモジュール実行形式を推奨します（プロジェクトルートで実行）。

- ExecutionEngine を起動
  - 本番 / 開始例:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード（Mock Broker を使用、別 DB に記録）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行時の挙動:
    - プロセス優先度を "high" に設定し、SQLite / DuckDB に接続
    - Paper Trading の場合は PAPER_TRADING_SQLITE_PATH を使用
    - 停止フラグ: プロジェクトの data/stop_requested.flag が存在する場合は起動を抑止または停止

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数で変更可能:
    ```
    export MONITOR_POLL_INTERVAL=30  # 秒
    ```
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に保存される仕様）
  - 停止フラグ: data/stop_requested.flag を検知するとループを停止

- .env を対話式で作る（再掲）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - 必要: OPENAI_API_KEY 環境変数（または関数引数で明示）
  - ニューススコアリングは kabusys.ai.score_news（プログラムから呼出す API）

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...） デフォルト: INFO
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒） デフォルト: 60
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動で読み込みます。
- テスト等で自動読み込みを抑制したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 運用上のファイル / フラグ

- data/stop_requested.flag — プロセスを停止させたい時にこのファイルを作成すると run_* スクリプトが検知して安全停止します
- data/execution.pid — ExecutionEngine の PID ファイル（デフォルトパスは Settings.pid_file_path）
- kill.flag（Settings.kill_flag_path）
  - KillSwitch がトリガー条件を満たすとこのファイルを作成して ExecutionEngine 停止を促します
  - 設定 KILL_FLAG_CLEAR_ON_START=1 により起動時に自動でクリアすることもできます（本番では 0 推奨）

---

## ログ

- ロギングは共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` で設定されます。
- デフォルト:
  - コンソール出力（stdout）
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保持）
- LOG_DIR を設定することでログディレクトリを変更可能（引数経由でも設定可）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル / モジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                — Settings / 自動 .env ロードロジック
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (実装がある場合)
    - execution/
      - execution_engine.py (実装本体)
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
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
    - data/ (データ関連のパッケージが存在する想定)
    - tools/
      - paper_verification_report.py

---

## 開発 / テストのヒント

- settings = Settings() により環境変数の妥当性チェックが行われます。ValueError が投げられたら .env を確認してください。
- validate_config.py は本番移行前のチェックに有効です（--strict を使うと警告もエラー扱い）。
- DuckDB のテーブル名（prices_daily, raw_financials 等）に依存するコードが多いので、分析データのスキーマ整備が必要です。
- AI 機能は外部 API（OpenAI）に依存します。API キーとネットワークを用意してください。API 呼び出しはリトライ・フォールバックを行う設計です。

---

## よくあるトラブルシューティング

- PyYAML がないと validate_config の YAML 内容チェックをスキップします（警告表示）。インストールするには `pip install PyYAML`。
- ログディレクトリ作成に失敗するとファイル出力が無効になりコンソール出力のみになります（stderr に警告が出ます）。
- MONITOR_POLL_INTERVAL が 0 や負値だと無効値として無視され、デフォルト（60 秒）が使用されます。
- ExecutionEngine 停止は stop flag (data/stop_requested.flag) または kill.flag によります。意図せず停止する場合はこれらのファイルを確認してください。

---

## ライセンス / バージョン

- パッケージバージョンは `kabusys.__version__` で管理（例: 0.1.0）。
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）。

---

README は以上です。必要であれば、以下の追記も可能です：
- サンプル .env のテンプレート
- systemd / supervisor 用のユニットファイル例
- より詳細な DB スキーマ説明（テーブル列の説明）