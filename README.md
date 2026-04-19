# KabuSys

日本株向け自動売買システムのモジュール群。バックテスト／リサーチ、ポートフォリオ構築、注文実行、監視、AI（ニュース/レジーム判定）などの機能を含みます。

## 概要
このリポジトリは以下の主要コンポーネントを提供します。

- ExecutionEngine：発注（実口座／ペーパートレード）を実行するエンジン
- Monitoring：システム稼働状況・注文履歴・リスク監視を行う監視モジュール
- Portfolio：銘柄選定・配分・ポジションサイズ計算ロジック
- Research：ファクター計算・特徴量探索
- AI：ニュースセンチメントや市場レジームを LLM（OpenAI）で判定するモジュール
- Tools：ペーパートレードの検証レポート生成などの補助スクリプト
- Config utilities：.env 生成ウィザードや設定検証 CLI
- Utils：ロギング設定・プロセス優先度などの共通ユーティリティ

Python の型ヒントや最新構文を使用しているため、Python 3.10 以上を想定しています。

## 主な機能
- 環境ごとの挙動（development / paper_trading / live）切替
- Paper Trading 用に本番 DB と分離された専用 SQLite（デフォルト: `data/paper_trading.db`）
- 監視：CPU/メモリ/ディスク・データ鮮度・Execution プロセス検知
- Kill Switch：閾値超過時に `data/kill.flag` を書き込み Execution を安全停止
- RiskMonitor：ドローダウン・ポジション上限検知とログ記録
- AI モジュール：ニュースの銘柄別センチメント（OpenAI）、市場レジーム判定
- Portfolio ライブラリ：候補選定・ウェイト算出・ポジションサイズ決定（単元考慮）
- Research：モメンタム／バリュー／ボラティリティなどのファクター計算
- ログ管理：stdout と日次ローテーションログ（`logs/<app_name>.log`）

## 前提 / 必須パッケージ
推奨 Python バージョン: 3.10+

主な依存ライブラリ（プロジェクト内で使用）
- duckdb
- psutil
- openai
- sqlite3（標準）
- PyYAML（config 検証を行う場合、オプション）

手動インストール例:
```
pip install duckdb psutil openai pyyaml
```

requirements.txt がある場合はそれを利用してください（本リポジトリには同梱されていない想定）。

## 環境変数と .env
自動的に `.env` / `.env.local` がプロジェクトルートから読み込まれます（OS 環境変数が優先）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合必須)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動でクリアする場合は "1"。本番は "0" 推奨)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒。デフォルト 60 秒)

.env の作成はウィザードで対話式に行えます（次参照）。

## セットアップ手順
1. リポジトリを取得
2. Python 3.10+ 環境を用意し、依存パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
3. 環境変数設定
   - .env を手動作成するか、対話式ウィザードを実行:
     ```
     python -m kabusys.config_setup
     ```
   - 作成後、設定を検証:
     ```
     python -m kabusys.validate_config
     ```
     警告を FAIL 扱いにするには `--strict` を付ける:
     ```
     python -m kabusys.validate_config --strict
     ```
4. 必要に応じてデータディレクトリを作成（例: `data/`, `logs/`）。多くは自動作成されますが権限に注意。

## 使い方（起動・ツール）
- ExecutionEngine の起動
  - 本番/開発/ペーパーは `KABUSYS_ENV` で切り替わります。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（`KABUSYS_ENV=paper_trading`）の場合、MockBrokerClient を使い、`data/paper_trading.db` に記録します。

- Monitoring の起動
  - デフォルトのポーリング間隔は 60 秒。環境変数で変更可能。
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path（`SQLITE_PATH`）を使用します（監視データは本番 DB に蓄積）。

- 停止 / Kill Switch
  - 監視や外部操作により `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルが送られます。
  - `data/stop_requested.flag` を作成すると `run_execution` / `run_monitoring` のループが終了します（停止指示用）。
  - Execution は実行中に PID ファイル `data/execution.pid` を作成します。

- Paper Trading 検証レポート
  - 指定期間の paper trading DB を解析して、稼働率や注文成功率、レイテンシ等のレポートを生成できます:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルトの DB パスは `data/paper_trading.db`。`--db PATH` で上書き可能。

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または関数引数で渡す）。
  - ニューススコア: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - これらは DuckDB 接続（prices_daily, raw_news 等を参照）を受け取り、DB の更新を行います。

## ログ
- ログは stdout とファイル（`logs/<app_name>.log`）に出力されます。ログのローテーションは日次で 30 世代保持。
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name="...")` で統一的に行われます。
- ログディレクトリは環境変数 `LOG_DIR` または `logs/`（デフォルト）を使用します。

## 設定検証 / .env ウィザード
- 対話的に `.env` を作成・更新:
  ```
  python -m kabusys.config_setup
  ```
- 作成後、検証:
  ```
  python -m kabusys.validate_config
  ```
  --strict を付けると警告も失敗扱いになります。

## 注意事項 / 運用メモ
- `KABUSYS_ENV=live` の設定は本番運用です。LINE 通知等の設定を必ず確認してください。
- `KILL_FLAG_CLEAR_ON_START=1` は開発用設定です。本番では `0` を推奨します（自動クリアは危険）。
- Paper trading は本番データベースと分離されます（`PAPER_TRADING_SQLITE_PATH` を使用）。
- OpenAI 呼び出しはレート制限・タイムアウト回避のためにリトライとバックオフが実装されていますが、API キーやコストに注意してください。

## ディレクトリ構成（抜粋）
以下は主要なモジュール位置のツリー（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      # 環境変数 / Settings
  - config_setup.py                # .env ウィザード
  - validate_config.py             # 設定検証 CLI
  - run_execution.py               # ExecutionEngine 起動スクリプト
  - run_monitoring.py              # SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py             # ログ設定ユーティリティ
    - process_priority.py          # 優先度 / CPU affinity
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
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

ルートに `data/`（DB・PID・フラグ等）、`logs/`（ログ）ディレクトリを使います。スクリプトは必要に応じてこれらを自動生成します。

## よく使うコマンドまとめ
- .env 作成ウィザード:
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
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- Paper trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---
必要であれば、README に記載するサンプル .env（雛形）や各モジュールの API 使用例（関数シグネチャ・戻り値例）を追加します。どの情報をより詳しく載せたいか教えてください。