# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買／研究／監視ツール群を含むプロジェクト「KabuSys」です。  
本 README はコードベースから読み取れる機能・使い方・セットアップ手順をまとめたものです。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は次のような役割を持つモジュール群で構成された自動売買システムです。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で注文を作成・管理する実行コンポーネント。
- Monitoring（監視）: システム稼働状況、注文状況、リスク（ドローダウン・ポジション上限等）をポーリングしてログ・アラートを発生。
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群。
- Research（リサーチ）: DuckDB 上の価格・財務データからファクター計算や特徴量解析を実行。
- AI モジュール: OpenAI を利用したニュースセンチメント評価（news_nlp）や市場レジーム判定（regime_detector）。
- Tools: ペーパートレード検証レポート生成等のユーティリティスクリプト。
- utils: ロギング設定・プロセス優先度設定などのユーティリティ。

設計上のポイント:
- DuckDB（分析用）と SQLite（監視・発注ログ用）を併用。
- ペーパートレード時は本番 DB と完全分離されるよう paper_trading 用 DB をサポート。
- OpenAI 呼び出しはリトライ・バリデーション・部分書き込みなどフェールセーフを重視。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper/live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の静的検証 CLI
  - Settings クラス: 環境変数ラッパー（デフォルト値、バリデーション、パス展開）
- 監視・リスク管理
  - monitoring_engine.py: 個別 Monitor の集約・定期実行
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 各種チェックと monitoring DB への永続化
  - kill_switch.py: 条件により data/kill.flag を書き込んで ExecutionEngine を停止させる
- ポートフォリオ構築
  - 候補選定、等ウェイト / スコア加重、リスクベースの株数決定、セクター制限、レジーム乗数
- 研究（Research）
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン、IC 計算、統計サマリー
- AI 機能
  - news_nlp.score_news: OpenAI でニュースを集約・センチメントスコア化し ai_scores テーブルへ書込
  - regime_detector.score_regime: MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード結果の検証レポートを生成（期間指定可）

---

## セットアップ手順（ローカル開発環境想定）

1. リポジトリをクローン / 取得

2. Python 環境（推奨: 3.10+）を準備し仮想環境を作成・有効化

   example:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   - 必須: duckdb, psutil, openai
   - あると便利: PyYAML（config YAML 検証用）

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. .env の準備
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成（下記「必須/任意の環境変数」参照）。

   自動読み込み:
   - プロジェクトルート（.git または pyproject.toml がある場所）にある `.env` および `.env.local` は自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. DB 初期化
   - monitoring 用 SQLite と DuckDB は起動スクリプトが自動的にテーブルを作成します（init_monitoring_db が実行されます）。
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

6. ログディレクトリ
   - デフォルト logs/ に日次ローテーションログが出力されます。書き込み権限がない場合はコンソール出力のみになります。

---

## 必須 / 主要な環境変数

必須（実行前に設定してください）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

主要な任意項目（デフォルト値があるものを含む）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）デフォルト: instant
- OPENAI_API_KEY — OpenAI を使う機能で必要（news_nlp, regime_detector）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1: クリア、0: しない。production では 0 推奨）

注意:
- validate_config.py により設定漏れや不整合を事前に検出できます。

---

## 使い方（代表的なコマンド）

- 環境検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
  ```

- .env 対話式ウィザード
  ```
  python -m kabusys.config_setup
  ```

- ExecutionEngine の起動
  - 通常（デフォルト KABUSYS_ENV に従う）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードで起動する場合:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    ※ KABUSYS_ENV=paper_trading のときは MockBrokerClient が使われ、data/paper_trading.db に記録されます（本番 DB と分離）。

- Monitoring の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    export MONITOR_POLL_INTERVAL=30   # 30秒間隔
    python -m kabusys.run_monitoring
    ```
  - 注意: Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視 DB に記録します。

- ペーパートレード検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を明示する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- AI 関連
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。CLI ラッパーは提供されていないため、スクリプトから呼び出すか日次バッチで利用してください。
  - モデル: gpt-4o-mini を想定（ソース内に指定あり）。API 呼び出しはリトライ制御・JSON バリデーションを実装。

---

## 停止 / 制御

- 停止フラグ:
  - data/stop_requested.flag — run_monitoring.py と run_execution.py がチェックしている停止フラグ（存在するとループを抜ける）
  - data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine に停止シグナルを送るために存在する。kill.flag の存在は ExecutionEngine の起動を阻止または停止トリガーになります。
- PID ファイル:
  - data/execution.pid は ExecutionEngine の PID 格納ファイル（Settings.pid_file_path で指定可）

---

## ログ

- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション・30日保持）に出ます。
- ログレベルは .env の LOG_LEVEL または setup_logging に渡す引数で調整できます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要なモジュールとファイル（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       — monitoring 用 SQLite 永続化層
      - monitoring_engine.py   — 各 Monitor を束ねる
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py       （アラート送信の実装がある想定）
    - execution/
      - execution_engine.py    — ExecutionEngine（実行本体）
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
      - news_nlp.py             — ニュースセンチメント (OpenAI)
      - regime_detector.py      — 市場レジーム判定 (OpenAI)
    - tools/
      - paper_verification_report.py

（実際の追加ファイルやサブディレクトリはリポジトリ内を参照してください）

---

## 注意事項 / 運用上のヒント

- 本番運用時は KABUSYS_ENV=live とし、LINE 通知等のアラート設定を必ず確認してください（validate_config に警告が出ます）。
- KILL_FLAG_CLEAR_ON_START=1 は本番で危険です。起動時に kill.flag を自動で消してしまうため、通常は 0 を推奨します。
- OpenAI API を利用する機能は API コストとレイテンシに注意してください。API キーと利用制限の管理を徹底してください。
- データのルックアヘッドバイアス防止に配慮した実装が各所にあります（target_date 未満のデータのみ使用等）。研究処理を再利用する際はその点を尊重してください。
- DuckDB / SQLite ファイルはデフォルトで `data/` に置かれます。バックアップ・アクセス権限を考慮してください。

---

この README はコードベースのコメント・関数ドキュメントを元に作成しています。実際の運用では各モジュールのドキュメント（コード内 docstring）や運用手順書を参照し、環境変数・権限・バックアップ・監視を整備してから稼働させてください。もし README の追加項目（例: 実行例, .env.example を含めたテンプレート等）が必要であれば指示してください。