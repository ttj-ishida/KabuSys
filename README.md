# KabuSys

日本株自動売買システムの一部を含むコードベース。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行（本番 / ペーパートレード）、監視・アラート、AI を使ったニュースセンチメント評価などの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な設計方針は以下の通りです。

- モジュール化されたコンポーネント（research / portfolio / execution / monitoring / ai / utils）で責務を分離
- DuckDB / SQLite を用いたローカルデータ蓄積・分析
- 本番（live）とペーパートレード（paper_trading）を設定で切替可能
- OpenAI を用いたニュースの NLP スコアリング・レジーム判定をサポート
- 監視コンポーネントにより稼働状況・ポジション・ドローダウンを監視し、条件に応じて停止フラグ（Kill Switch）を発行

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートを基準）
  - 対話式ウィザードで .env を作成・更新（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行関連
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、ペーパートレード用 DB に記録
    - PID ファイルを出力 / 停止フラグにより安全に停止
  - 監視（Monitoring）起動スクリプト（python -m kabusys.run_monitoring）
    - システム・注文・リスク監視（定期ポーリング）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス死活検知
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常等）
  - RiskMonitor: ドローダウンやポジション上限の監視。必要に応じて risk_logs / dashboard を更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine に停止シグナルを送出
  - MonitoringDB: SQLite に監視データを永続化

- ポートフォリオ構築
  - 候補選定（スコア順、上位 N 抽出）
  - 重み計算（等金額・スコア加重）
  - セクター集中制限（apply_sector_cap）
  - ポジションサイズ計算（risk_based / equal / score、単元株丸め、aggregate cap）

- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリー

- AI（OpenAI を使用）
  - news_nlp: raw_news から銘柄ごとのセンチメントを算出し ai_scores に保存
  - regime_detector: ETF 1321 の MA とマクロニュースを組み合わせて市場レジーム判定し market_regime に書き込み

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

- ユーティリティ
  - ログ設定ユーティリティ（console + 日次ローテーションファイル出力）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発環境向け）

前提: Python 3.10+ を推奨します（型ヒント等により）。  
以下は基本的な手順例です。

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   - 明示的な requirements.txt が無い場合は主要依存のみインストールします:
     ```
     pip install duckdb psutil openai
     ```
   - validate_config の YAML 検証を有効にするなら:
     ```
     pip install PyYAML
     ```

4. .env の準備
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（プロジェクトルートに配置）。重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（デフォルト INFO）
     - KILL_FLAG_CLEAR_ON_START（0/1、本番は 0 を推奨）

   - 自動 .env ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 設定検証（任意、起動前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告もエラー扱い
   ```

---

## 使い方（実行例）

- ExecutionEngine（注文実行）を起動:
  - 標準起動（KABUSYS_ENV に応じて本番またはペーパー）:
    ```
    python -m kabusys.run_execution
    ```
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い `PAPER_TRADING_SQLITE_PATH` に記録します（本番 DB と分離）。
    - 起動時に data/execution.pid が作成されます。プロセスを停止するには data/stop_requested.flag の作成、あるいは kill.flag による停止トリガーで安全停止します。
    - プロセス優先度を "high" に設定しようとします（権限によっては失敗して警告になります）。

- Monitoring（監視ループ）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は monitoring 用の sqlite（Settings.sqlite_path、デフォルト data/monitoring.db）を使用してログを残します。
  - data/stop_requested.flag を作成すると監視ループは終了します。

- Paper Trading 検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は --db オプション、もしくは環境変数 PAPER_TRADING_SQLITE_PATH で指定。

- AI モジュールの利用
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、OPENAI_API_KEY が必要です（ライブラリ内 API を直接呼び出す用途向け）。
  - 例（スクリプト内で使用）:
    ```
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, target_date, api_key='sk-...')
    ```

- Kill Switch（手動）:
  - 高リスク時に ExecutionEngine に停止を通知するには data/kill.flag を作成します（KillSwitch が存在すれば再起動抑止等の運用が可能）。
  - KillSwitch は冪等にファイルを書き、既存なら上書きしません。クリアは KillSwitch.clear() を使うかファイルを手動で削除します。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- OPENAI_API_KEY — OpenAI を利用する場合
- LOG_LEVEL — デフォルト: INFO
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

（.env の雛形は `python -m kabusys.config_setup` で生成できます）

---

## ディレクトリ構成

（プロジェクトルート直下に `src/kabusys` がある想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - execution/ — 発注エンジン周り（Engine, BrokerFactory, OrderManager, RiskManager, Reconciler, repository 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
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
  - data/ (運用時に作成されるディレクトリ)
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db / paper_trading.db / kabusys.duckdb など

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定・シークレット・Kill Switch の扱いに十分注意してください（validate_config は本番環境での警告出力を行います）。
- OpenAI API を利用する機能は API キーの管理とコストに注意してください。API エラー時はフォールバックロジックがあるものの、運用ルールを明確にしてください。
- ログは console + 日次ローテーションファイルに出力されます（デフォルト logs/ ディレクトリ）。ログディレクトリ作成権限に注意してください。
- プロセス優先度変更や CPU affinity 設定は OS 権限に依存します。権限不足で失敗する場合は警告が出ますが処理自体は継続します。
- データベースファイル（DuckDB/SQLite）は実行ユーザーに書き込み権限が必要です。バックアップ・運用方法を検討してください。

---

もし README に含めたい追加の使い方（デプロイ手順、サンプル .env、CLI 引数の詳細など）があれば教えてください。必要に応じて例やコマンドを追記します。