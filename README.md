# KabuSys

日本株自動売買システムの参照実装です。モジュールは売買実行、監視、ポートフォリオ構築、リサーチ、AI（ニュース NLP／レジーム判定）等で構成されています。本リポジトリには実行スクリプトや対話式設定ウィザード、検証ツール、ペーパートレード用レポート生成器などが含まれます。

## プロジェクト概要
- 目的: 日本株の自動売買ワークフロー（シグナル生成 → ポートフォリオ構築 → 注文発行 → 監視・リスク管理）をモジュール化して実装する。
- アーキテクチャ:
  - Execution Engine: 発注・注文管理・リスク管理を担当。KABUSYS_ENV に応じて本番/ペーパーを切替。
  - Monitoring: システム稼働状態・データ鮮度・注文異常・リスク閾値をポーリングで監視し、Kill Switch を発動可能。
  - Research: DuckDB 上の時系列データを用いたファクター計算・特徴量探索。
  - AI: OpenAI を使ったニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）。
  - ユーティリティ: ロギング設定、プロセス優先度設定、環境設定ウィザード／検証 CLI 等。

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient と専用 DB を利用。
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録。
- 環境管理
  - config_setup.py: 対話式ウィザードで .env を作成 / 更新。
  - validate_config.py: .env と config/*.yaml（存在する場合）の検証。`--strict` で警告も失敗扱い。
- 監視
  - monitoring_engine.py: System / Trade / Risk Monitor を束ねてアラートや Kill Switch を評価。
  - monitoring_db.py: SQLite に監視ログ・注文ログ・ポジション・リスクログ・ダッシュボードを永続化（冪等な初期化・マイグレーション対応）。
  - Kill Switch: drawdown やポジション上限で `data/kill.flag` を書き、ExecutionEngine に停止指示。
- ポートフォリオ構築（純関数）
  - 候補選定、重み計算（等重・スコア重み）、ポジションサイズ計算、セクターキャップ、レジーム乗数計算。
- リサーチ（DuckDB）
  - モメンタム、ボラティリティ、バリュー等のファクター計算。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー等。
- AI
  - news_nlp.score_news: OpenAI API を用いて銘柄単位のニュースセンチメントを計算し ai_scores に書き込む。
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート（稼働率、注文成功率、レイテンシ等）を生成。

## 前提 / 必要環境
- Python 3.10 以上（`|` 型等の構文を使用しているため）
- 主要 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証を行う場合）
- OS: Windows / Linux / macOS に対応するユーティリティ実装あり（ただし一部機能は OS 権限に依存）

インストール例:
```bash
python -m pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt がある場合はそれを利用してください）

## セットアップ手順
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して依存ライブラリをインストール
3. .env を作成
   - 対話式で作る:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env.example` を参照して手動作成
4. 設定の検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. DB 初期化等は起動スクリプトで自動実行されます（monitoring 用テーブルの初期化は run_execution / run_monitoring 内で行います）。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（例: INFO、デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading 時の mock ブローカー約定挙動: instant|partial|never|reject、デフォルト: instant）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読込を無効化

デフォルトのファイルパス
- ログ: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日分保持）
- kill flag: data/kill.flag（Kill Switch 用）
- stop flag: data/stop_requested.flag（run_execution/run_monitoring の外部停止トリガー）
- PID: data/execution.pid（ExecutionEngine 用）

## 使い方（主要コマンド）
- ExecutionEngine の起動
  - 本番 / 開発 / ペーパーは KABUSYS_ENV で切り替え:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - ペーパートレードでは paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。外部停止は `data/stop_requested.flag` を作成してください。
  - ExecutionEngine 停止シグナルは `data/kill.flag`（Kill Switch）で行われます。`KILL_FLAG_CLEAR_ON_START=1` に注意（本番では 0 推奨）。

- Monitoring の起動
  ```bash
  # ポーリング間隔を変更する例（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番（settings.sqlite_path）を参照します（環境にかかわらず）。
  - stop フラグ（data/stop_requested.flag）を作成するとループを終了します。

- .env の対話式生成/更新
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
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report
  # 期間指定と DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出す例）
  ```python
  from kabusys.ai import score_news
  # DuckDB 接続（duckdb.connect(...) を用意）
  n = score_news(duckdb_conn, target_date, api_key="sk-...")
  ```

## 監視・停止周りの挙動（要点）
- run_monitoring は MONITOR_POLL_INTERVAL（秒）で SystemMonitor.check_once を呼ぶ（デフォルト 60 秒）。
- run_execution はデーモンスレッドで Engine を走らせ、`data/stop_requested.flag` を検出したら停止処理を行う。
- Kill Switch（監視側）は drawdown やポジション上限を検出すると `data/kill.flag` を書き込み、ExecutionEngine は起動時や稼働中にこれを検出して安全停止します。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では危険なので 0 を推奨）。

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py — 統一ロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・CRUD ヘルパ
    - system_monitor.py — システム稼働・データ鮮度監視
    - trade_monitor.py — 注文 / 取引ログ監視（該当ファイル参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 監視ループの束ね役
    - alert_manager.py — 通知（LINE など）管理（該当ファイル参照）
  - execution/ — 発注関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/ — 銘柄選定、重み、サイズ計算、リスク調整
  - research/ — factor_research.py, feature_exploration.py 等
  - ai/
    - news_nlp.py — ニュースセンチメントスコア
    - regime_detector.py — 市場レジーム判定
  - data/ — 実行時に使用する DB / フラグ / PID 等（デフォルトパス）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - logs/ — デフォルトのログ出力先（実行時に生成される）

（上記はソースの主要ファイル・サブパッケージの抜粋です。詳細はソースを参照してください。）

## 開発上の注意 / ベストプラクティス
- .env は絶対にリポジトリにコミットしないこと（config_setup.py のヘッダにも記載）。
- 本番環境（KABUSYS_ENV=live）での設定は慎重に：LINE 通知や kill flag の設定を確認してください。
- OpenAI API を利用する AI 機能は API キーとコストに注意。API 呼び出しはリトライやフォールバック（失敗時はスコア 0 等）を実装してフェイルセーフ化していますが、運用ポリシーを策定してください。
- psutil によるプロセス優先度 / CPU affinity の設定は権限に依存します。権限不足だと警告ログが出ますが動作は継続します。

## よくあるコマンドまとめ
- .env を作る: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれていない内部 API（関数名やクラス）についてはソースの docstring を参照してください。必要なら、特定モジュールの使い方や API の詳細なドキュメントを追加で作成します。どの箇所を詳しく書けばよいか教えてください。