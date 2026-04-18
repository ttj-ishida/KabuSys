# KabuSys

日本株向け自動売買システムの軽量フレームワークです。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、
およびニュースNLP / レジーム判定などの補助モジュールが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の機能群を持つモジュール群で構成された自動売買基盤です。

- ExecutionEngine（発注処理）
  - ライブ / ペーパートレード（環境に合わせてブローカークライアントを切替え）
  - 注文管理、リスク管理、照合処理を備える
- Monitoring（監視）
  - システムリソース、データ鮮度、注文ログ、リスク指標の定期チェック
  - kill.flag を用いた外部からの安全停止（Kill Switch）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制約など
- Research（調査 / ファクター計算）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC 計測、要約統計
- AI（ニュース NLP / レジーム判定）
  - OpenAI を使ったニュースセンチメント評価（ai_scores に書き込み）
  - ETF の MA200 とマクロニュースを合わせた市場レジーム判定
- Tools
  - Paper Trading 用の検証レポート生成スクリプト 等
- 設定管理 / ウィザード / 検証 CLI
  - .env の対話式生成（config_setup）、起動前の設定検証（validate_config）

設計方針の一部:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV を参照）
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）
- フェイルセーフ: API 失敗時はフォールバック（スコア 0 など）して継続

---

## 主な機能一覧

- 環境設定:
  - .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行 / 発注:
  - run_execution: ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - ペーパートレード時は MockBroker を使用し data/paper_trading.db に記録
- 監視:
  - run_monitoring: SystemMonitor のポーリング起動（python -m kabusys.run_monitoring）
  - MonitoringEngine: System/Trade/Risk Monitor を束ねてアラート・Kill Switch を評価
- ポートフォリオ構築:
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ算出
- リサーチ:
  - DuckDB を用いたファクター計算（prices_daily/raw_financials ベース）
  - IC / forward returns / factor summary
- AI:
  - ニュースセンチメント（OpenAI）を ai_scores に書き込み（kabusys.ai.score_news）
  - 市場レジーム（score_regime）判定・書き込み
- ツール:
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提 / 必要パッケージ

推奨 Python バージョン: 3.10 以上（| 型や match ではないが、コードで 3.10 の構文を使用）

主要依存（最低限）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- SQLite（標準ライブラリに含まれます）

実際の環境では requirements.txt を置き、仮想環境で管理してください。例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai PyYAML
   ```

3. 初期設定（.env の作成）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 生成された .env を編集して必要な値を入力（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須）

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も含めて厳密にチェックする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの確認 / 作成
   - デフォルトの DB パス等は .env で指定できます。デフォルト値:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/（LOG_DIR で変更可）

注意:
- 実際にプロセス優先度を "high" に設定する処理があり、権限が必要な場合があります（set_process_priority）。
- OpenAI 関連機能を使う場合は OPENAI_API_KEY を .env に設定してください。

---

## 環境変数（抜粋）

主要な環境変数（必須 / 重要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）、デフォルト: development
  - paper_trading: 発注は MockBrokerClient、DB は data/paper_trading.db に分離
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

その他、PAPER_FILL_MODE（paper_trading の注文埋め方）などの設定があります（詳細はコード内 Settings を参照）。

---

## 使い方（実行例）

- .env を作成・編集後、設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（バックグラウンドで起動する場合はプロセスマネージャを使用）:
  ```
  python -m kabusys.run_execution
  ```
  注意: KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録されます。

- Monitoring を起動（デフォルト 60 秒間隔。環境変数 MONITOR_POLL_INTERVAL で変更可）:
  ```
  python -m kabusys.run_monitoring
  ```
  例: 30秒間隔で起動する場合:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- .env を対話的に作成:
  ```
  python -m kabusys.config_setup
  ```

- AI 関連（プログラムから呼ぶ例）:
  - news NLP（銘柄ごとのスコアを書き込む）:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")
    ```

- 停止制御:
  - 外部から ExecutionEngine を安全に停止させたい場合、`data/kill.flag` を作成します（KillSwitch 実装により検知）。
  - run_monitoring と run_execution では `.data/stop_requested.flag` や `data/execution.pid` を利用する処理が含まれています。

---

## 重要な設計ノート / 運用注意

- Paper trading と本番データは明確に分離されています。KABUSYS_ENV=paper_trading では paper_trading.db を使用します。
- OpenAI API 利用箇所はリトライとサニタイズ処理が入っていますが、APIキーやコスト管理は運用者側の責任です。
- Kill Switch はリスク指標（ドローダウンやポジション数超過）で自動的に `data/kill.flag` を書き、Execution の停止を促します。`KILL_FLAG_CLEAR_ON_START` は本番で 1 を設定しないでください。
- プロセス優先度の設定（set_process_priority）は権限不足で失敗することがあり、その場合は警告でスキップされます。
- DuckDB / SQLite のパスやログ先は .env で設定可能。データやログを確実に永続化するため適切なボリュームマウント・バックアップを行ってください。
- DB スキーマのマイグレーションは簡単な ALTER を含みますが、本番環境でのスキーマ変更は慎重に。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定取得ロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント評価（OpenAI）
  - regime_detector.py — レジーム判定（MA200 + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・読み書きラッパー
  - system_monitor.py — システム / データ鮮度監視
  - trade_monitor.py — 発注ログ監視（ファイルに含まれます）
  - risk_monitor.py — ドローダウン・ポジション数チェック
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — 通知管理（LINE など）※実装ファイル参照
- execution/ (発注関連ロジック)
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py — 統一ログ初期化
  - process_priority.py — 優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading レポート

（上記は主要ファイルの抜粋です。詳細は src/kabusys フォルダ内の各ファイルを参照してください。）

---

## 監視 DB（SQLite）スキーマ（概要）

init_monitoring_db により作成される主なテーブル:
- system_status: cpu/memory/disk/process_ok, recorded_at
- trade_logs: 発注イベントログ（event_type, client_order_id, code, qty, price, latency_ms 等）
- positions: 現在の保有
- risk_logs: リスク関連イベント
- dashboard: ダッシュボード集計（最新の portfolio_value, cash, drawdown_pct 等）

マイグレーション処理（既存 DB にカラム追加）も実装済みです。

---

## 開発 / 貢献

- まずは .env を作成し validate_config を通してください。
- DuckDB にサンプルデータ（prices_daily / raw_financials / raw_news）を入れると research / AI 機能をローカルで試せます。
- テストはユニットテストを追加していくことを推奨します（現在のコードベースは関数単位で純粋関数が多く、テストしやすい設計です）。

---

README に記載のない内部 API や細かい実装はソースコード（src/kabusys 以下）を参照してください。必要であれば、各モジュールの利用例や運用手順を別途ドキュメント化できます。