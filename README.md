# KabuSys

日本株自動売買システムの軽量モジュール群（ライブラリ + 起動スクリプト群）

本リポジトリは、シグナル生成 / ポートフォリオ構築 / 発注エンジン / 監視 / 研究用ユーティリティなど、実運用を意識したコンポーネントを集めたコードベースです。  
（本 README は src/kabusys 配下の実装に基づいています。）

---

## 概要

- システムはモジュール化されており、発注・監視・AI（ニュースNLP・レジーム判定）・ポートフォリオ構築・研究用ファクター計算などを含みます。
- 設定は環境変数（.env）で管理。対話式ウィザードと検証ツールが付属しています。
- Paper Trading（ペーパートレード）用に本番データと分離された SQLite DB を使う設計になっています。
- ロギングは統一的な setup_logging ユーティリティを通して stdout と日次ローテートファイルに出力します。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: 発注エンジン（ExecutionEngine）起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading.db に記録。
  - run_monitoring.py: SystemMonitor をポーリングで回す監視プロセス起動スクリプト。MONITOR_POLL_INTERVAL で間隔を上書き可（デフォルト 60秒）。

- 設定管理
  - config_setup.py: .env の対話式ウィザード（キー入力で .env を生成/更新）。
  - validate_config.py: .env と config/*.yaml の基本チェックツール（--strict で警告もエラー扱い）。

- 監視（monitoring）
  - monitoring_db.py: 監視用 SQLite テーブルの初期化・読み書きユーティリティ。
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager（実装の一部）: システム稼働状況・注文状態・ドローダウン監視・Kill Switch 機能。

- 発注・実行（execution）
  - ExecutionEngine, OrderManager, OrderRepository, BrokerClientFactory, RiskManager, Reconciler（参照のみ。実装ファイルは別途）を組み合わせて実行。

- ポートフォリオ構築（portfolio）
  - portfolio_builder: 候補選定・重み計算（等金額 / スコア加重）
  - position_sizing: 株数算出、単元株丸め、投下資金スケーリング
  - risk_adjustment: セクター上限やレジーム乗数

- 研究（research）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等

- AI（ai）
  - news_nlp.py: raw_news を OpenAI に送って銘柄ごとにセンチメントを算出し ai_scores に書き込む
  - regime_detector.py: ETF（1321）MA とマクロ記事の LLM センチメントを合成して market_regime を判定

- ツール
  - tools/paper_verification_report.py: Paper Trading DB を解析して検証レポートを作成（稼働率・約定率・レイテンシなど）

- ユーティリティ
  - utils/logging_setup.py: ログ設定
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定
  - config.py: 環境変数ラッパー（Settings クラス）

---

## セットアップ手順（開発環境向け）

前提:
- Python 3.9+（コードは型ヒントに Union 型等を利用）
- 仮想環境推奨（venv または pyenv + venv）

1. リポジトリをクローンしてワーキングディレクトリを移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化
   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   代表的な依存:
   - duckdb
   - psutil
   - openai
   - (オプション) PyYAML — validate_config の YAML 検証で使用

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

   ※requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定内容を検証:
     ```
     python -m kabusys.validate_config
     # strict モード: 警告も失敗扱い
     python -m kabusys.validate_config --strict
     ```

5. データディレクトリ / ログディレクトリ確認
   - デフォルトの DB パス等:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
   - ログや DB は自動的に作成されますが、権限などを確認してください。

---

## 重要な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading のとき発注はモッククライアントへ記録され、専用 DB (PAPER_TRADING_SQLITE_PATH) を使用します。

- DB / ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

- OpenAI:
  - OPENAI_API_KEY（AI モジュール使用時に必要）

- 監視:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒。デフォルト 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

その他は config_setup.py の質問項目を参照してください。

---

## 使い方（主要コマンド）

- .env の作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 発注エンジン起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録されます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止できます（スクリプトはこの存在を監視します）。
  - PID は data/execution.pid に書き込まれます。

- 監視プロセス起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path を使用して監視 DB に書き込みます（環境にかかわらず本番 sqlite_path を使用する設計）。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db` でパスを指定可能。

- AI / 研究関数はライブラリとしてインポートして利用:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, target_date) 等

---

## 運用上のポイント

- Kill Switch:
  - monitoring.kill_switch は RiskMonitor 等からの警告を受けて data/kill.flag を書き込み、ExecutionEngine に停止を指示できます。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定等により処理します。

- ログ:
  - setup_logging により stdout と logs/<app_name>.log（日次ローテーション、30 日保持）に出力されます。LOG_DIR 環境変数で変更可能。

- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出して優先度を上げます（プラットフォーム制約により失敗しても警告で継続）。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、必要に応じて列追加の簡単なマイグレーションも行います。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py

- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py (参照)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照)

- execution/
  - execution_engine.py (参照)
  - order_manager.py (参照)
  - order_repository.py (参照)
  - broker_factory.py (参照)
  - reconciler.py (参照)
  - risk_manager.py (参照)

- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

- tools/
  - __init__.py
  - paper_verification_report.py

- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py

（上記の「参照」はコードベース内で参照されているモジュール群を示します。実際のファイルはリポジトリに含まれている想定です。）

---

## 追加メモ / 開発ヒント

- DuckDB は分析系クエリ（prices_daily / raw_financials / raw_news 等）を素早く実行するのに便利です。research モジュールは DuckDB 接続を受け取り SQL+Python で計算します。
- OpenAI を使う機能 (news_nlp, regime_detector) は API キーを必須とします。テスト時は API 呼び出し関数をモックできます（コード中に patch の想定あり）。
- validate_config は .env の必須項目チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パースチェック（PyYAML を使用）を行います。
- run_execution/run_monitoring は両方とも起動時にプロセス優先度を上げ、終了はフラグファイルまたは KeyboardInterrupt で行う設計です。

---

問題や補足したい点があれば、README の改善箇所（例: 依存関係を requirements.txt にまとめる、起動例のユニットや systemd サービス定義、より詳細な API 使用例）を教えてください。README をその内容に合わせて更新します。