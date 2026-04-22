# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ / 起動スクリプト群）

この README はコードベースから抽出した概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するコンポーネント群を提供します。主な機能は次のとおりです。

- 実運用 / ペーパートレードを切り替え可能な ExecutionEngine（発注管理・リスク制御）
- システム・注文・リスクを監視する Monitoring コンポーネント（Kill Switch 等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ用モジュール（ファクター計算、特徴量解析、IC 計算）
- ニュースの NLP によるセンチメントスコアリング（OpenAI を利用）
- 市場レジーム判定（MA とマクロニュースを合成）
- ユーティリティ類（設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- 運用支援ツール（Paper Trading 検証レポート生成）

設計方針の要点:
- 多くの処理は純粋関数 / DB 結合で実装され、本番 API への不要なアクセスを防止
- Paper Trading は本番 DB と分離（デフォルト別ファイル）
- OpenAI 利用機能は API キー依存で、失敗時はフェイルセーフ処理を行う

---

## 機能一覧（主なモジュール）

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV=paper_trading のときは MockBroker）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定）

- 設定 / 初期化
  - config.py: 環境変数 / 設定管理（.env 自動読み込み）
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前チェック CLI（--strict オプションあり）

- 監視関連
  - monitoring/monitoring_db.py: SQLite を使った監視ログ層（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring/system_monitor.py: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py, monitoring/monitoring_engine.py 等（統合アラート・Kill Switch）

- 実行（Execution）
  - execution/*: Broker クライアントファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository など（発注・約定管理、リスク制御）

- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算
  - portfolio/position_sizing.py: 発注株数計算（単元丸め・リスク制約）
  - portfolio/risk_adjustment.py: セクター上限・レジーム乗数

- リサーチ / 分析
  - research/factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 利用）
  - research/feature_exploration.py: 将来リターン計算・IC・統計サマリ

- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を LLM に渡して銘柄別センチメントを ai_scores テーブルへ書き込み
  - ai/regime_detector.py: ETF MA とマクロニュースセンチメントの合成で市場レジーム判定

- ユーティリティ
  - utils/logging_setup.py: 共通ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

---

## セットアップ手順

以下は一般的なローカルセットアップ手順の例です。Python のバージョンは 3.10 以上を想定しています（型ヒントで | が使われているため）。

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境を作成して有効化（例）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 最低限の依存（プロジェクトに requirements.txt がない場合は主に以下が必要）
     ```
     pip install duckdb psutil openai
     ```
   - YAML の検証を行いたい場合:
     ```
     pip install pyyaml
     ```
   - 必要に応じて他パッケージを追加してください（実運用向け Broker クライアント等）。

4. 環境変数 / .env を作成
   - 対話式に作る:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはプロジェクトルートに .env を作成し、必要なキーを設定します（下の「重要な環境変数」を参照）。

5. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ（data/）やログディレクトリ（logs/）は自動作成されますが、権限等で失敗する場合は手動で作成してください。

---

## 重要な環境変数（代表例）

config_setup で設定される主なキー（.env）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
  - paper_trading の場合、MockBrokerClient を使い記録は data/paper_trading.db に保存される
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ...）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）に必須（または関数引数で指定）

運用でよく使うもの:

- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を自動クリアするか（0/1）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）

---

## 使い方（起動・主要コマンド）

起動スクリプトはパッケージモジュールとして実行できます。

- Monitoring の単独起動（ポーリングループ）:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - run_monitoring は停止フラグファイル data/stop_requested.flag の存在を監視し、検知時にループを終了します。

- ExecutionEngine 起動（実発注またはペーパー）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 実行中、data/stop_requested.flag が存在すればエンジンに停止命令を送り終了します。
  - ExecutionEngine の PID はデフォルト data/execution.pid に書き込まれます。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading の検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は引数 --db で指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも代替可）。

- AI 機能（プログラム内呼び出し）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - これらは OpenAI API キー（OPENAI_API_KEY）を必須とします。

---

## 停止 / Kill Switch

- 管理用ファイル:
  - data/stop_requested.flag: run_monitoring / run_execution が存在を検知すると安全に停止するためのフラグ
  - data/kill.flag: KillSwitch が発動した場合に書き込まれる（ExecutionEngine に対する停止指示として機能）
  - data/execution.pid: ExecutionEngine の PID 保存先

- KillSwitch のトリガー:
  - RiskMonitor がドローダウンやポジション上限などの閾値に合致すると kill.flag を書き込み、Monitoring が通知を行い Execution を停止させます。

---

## データベース（スキーマ概要）

監視用 SQLite（デフォルト data/monitoring.db）に以下のテーブルを作成・利用します（init_monitoring_db により冪等で作成）:

- system_status: CPU/メモリ/ディスク・プロセスOK フラグ・記録時刻
- trade_logs: 発注・約定イベントログ（latency_ms 列含む）
- positions: 保有ポジション
- risk_logs: リスク関連イベント（デデュープ機能あり）
- dashboard: 集計値（id=1 の 1 行運用）

Paper Trading 用 SQLite（デフォルト data/paper_trading.db）は実運用 DB と分離して記録します。

DuckDB（デフォルト data/kabusys.duckdb）はリサーチ / ファクター計算用の分析 DB として使用します。

---

## ディレクトリ構成

主要なファイル群は次のようになっています（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照元あり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

プロジェクトルートには想定される補助ファイル:
- .env（ローカル環境変数）
- config/*.yaml（各種設定テンプレート）
- data/（SQLite, PID, flag ファイル）
- logs/（ログ出力）

---

## 開発・運用時の注意点

- .env は秘密情報を含むため絶対にバージョン管理にコミットしないでください。
- 本番運用時は KABUSYS_ENV=live を使用します。validate_config の注意メッセージに従い設定を入念に確認してください。
- OpenAI を使用する機能は API コスト・レート制限・プライバシーに注意して運用してください（API キーの管理を厳重に）。
- run_execution/run_monitoring はフラグファイル（data/stop_requested.flag）により外部から安全に停止可能です。運用監視のためにログと monitoring DB を定期的に確認してください。
- DuckDB / SQLite のパスは環境変数で変更できます。Paper Trading は本番 DB と分離することを強く推奨します。

---

## 参考コマンド一覧

- .env を対話式に作成:
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
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書かれている内容はコードベースに基づく要約です。実際の運用や環境に応じて設定や依存関係を適宜調整してください。必要であれば README の追補（依存パッケージ一覧、systemd サービス例、Dockerfile 例 など）を追加しますので依頼ください。