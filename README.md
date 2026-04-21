# KabuSys

日本株向け自動売買／リサーチ基盤（軽量なモジュール構成のサンプル実装）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ロジック、監視、ペーパートレード検証、リサーチ（ファクター計算）および簡易 AI ベースのニュースセンチメント評価を含む小規模なトレーディング基盤です。  
設計方針として以下を重視しています。

- モジュール分割（execution, monitoring, research, ai, portfolio, utils）
- 本番 DB とペーパートレード DB の分離
- DuckDB を用いた分析（prices_daily / raw_financials 等の参照）
- OpenAI（gpt-4o-mini）との連携によるニュース/NLP 処理（任意）
- フラグファイルによる外部停止（Kill Switch）など運用を想定した機能

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - live / paper_trading / development 環境対応
  - ペーパートレード時は MockBroker を利用し DB を分離
  - リスク管理（RiskManager）、注文管理（OrderManager）等の統合
- Monitoring（run_monitoring.py）
  - System / Trade / Risk の各モニタによる定期チェック
  - kill.flag によるエンジン停止トリガ
  - 監視ログの永続化（SQLite）
- 監視 DB レイヤ（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard の自動生成・マイグレーション
- Portfolio 構築ユーティリティ（portfolio/*.py）
  - 候補選定、重み計算、ポジションサイズ決定、セクターキャップ適用 等
- Research（research/*.py）
  - Momentum, Volatility, Value などのファクター計算
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- AI モジュール（ai/*.py）
  - news_nlp: ニュース記事を LLM で評価して ai_scores に書き込む
  - regime_detector: MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- ツール
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - 自動 .env ロード / Settings 抽象化（config.py）

---

## セットアップ手順

前提: Python 3.10+ を想定（typing の union 型等を使用）。環境に応じて適宜読み替えてください。

1. リポジトリをチェックアウト（プロジェクトルートに `pyproject.toml` または `.git` があることを期待します）

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - 最低限:
     - duckdb
     - psutil
   - AI 機能を使う場合:
     - openai
   - YAML 検証を行う場合（validate_config の YAML 検証に使用）:
     - pyyaml

   例:
   - pip install duckdb psutil
   - pip install openai         # AI を使う場合
   - pip install pyyaml         # 設定ファイルの検証を行う場合

   （requirements.txt がある場合はそれを使ってください。）

4. 環境変数の準備
   - 対話式ウィザードで `.env` を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - よく使う環境変数（一例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: DEBUG/INFO/...
     - OPENAI_API_KEY: OpenAI を使う場合に設定
     - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、デフォルト 60）
     - PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）

   - 自動ロード:
     - config.py はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化）。

5. データディレクトリ
   - ログは既定で `logs/`、SQLite / DuckDB は `data/` 配下に配置されます。起動時に自動作成されますが、必要に応じて事前にディレクトリを作成してください。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）

- 実行プロセス起動（ExecutionEngine）
  - 本番（live）または開発（development）/ ペーパー（paper_trading）で挙動が変わります
  - Paper Trading の場合は MockBroker を利用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録されます
  - 例（本番）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 例（ペーパートレード）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ 等に基づき PASS/FAIL を判定

- AI（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
  - プログラム的に利用する例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB コネクション（分析 DB）を受け取り、テーブルへ結果を書き込みます

- ロギング
  - 全スクリプトは共通の `setup_logging` を使用します。ログは stdout と `logs/<app_name>.log`（日次ローテーション）に出力されます。

---

## 運用に関するメモ

- 停止フラグ:
  - 監視/実行プロセスの停止はフラグファイルを使用します（`data/stop_requested.flag` / `data/kill.flag` 等）。
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine を停止するトリガになります。
- PID ファイル:
  - run_execution は `data/execution.pid` を利用します（Settings.pid_file_path）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、必要に応じて既存 DB へカラム追加（マイグレーション）も行います。
- 優先度設定:
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil に依存）。権限不足や未対応 OS では警告を出してスキップします。

---

## ディレクトリ構成

概要（主要ファイルのみ抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py             — ログ設定ユーティリティ
      - process_priority.py          — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py             — SQLite 永続化層
      - system_monitor.py            — システム監視
      - trade_monitor.py             — 発注 / 約定監視（存在）
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - kill_switch.py               — kill.flag 書き込みロジック
      - monitoring_engine.py         — 各モニタ束ねる実行ループ
      - alert_manager.py             — 通知管理（存在想定）
    - execution/
      - execution_engine.py          — 実行エンジン本体（存在想定）
      - order_manager.py             — 注文管理
      - order_repository.py          — 注文永続化
      - risk_manager.py              — リスク管理
      - broker_factory.py            — ブローカークライアント生成
      - reconciler.py                — 発注照合
    - portfolio/
      - portfolio_builder.py         — 候補選定・重み計算
      - position_sizing.py           — 株数決定・スケール
      - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py           — Momentum/Volatility/Value 等
      - feature_exploration.py       — IC/統計サマリ等
    - ai/
      - news_nlp.py                  — ニュース NLP（OpenAI 経由）
      - regime_detector.py           — 市場レジーム判定（MA200+マクロ）
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - data/                           — 実行時生成想定（DB / flags / pid 等）

注: 一部モジュール（execution 内の詳細実装など）はここで全てを列挙していません。主要なエントリポイントと責務を中心に記載しています。

---

## 開発者向け情報 / 備考

- Settings はプロジェクトルート（.git または pyproject.toml）を起点に `.env` 自動ロードを行います。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 接続は分析用途向けに設計されています。prices_daily / raw_financials / raw_news / market_regime 等のテーブルを想定しています。
- AI モジュールは外部 API（OpenAI）への依存があり、レスポンスの堅牢な検証やリトライ処理を実装していますが、API コスト・レート制限に注意してください。
- テスト: 各ユーティリティは純粋関数や副作用を最小化する実装方針です。ユニットテストでは DuckDB/SQLite のインメモリ DB や openai 呼び出しのモックを利用すると良いでしょう。

---

必要であれば、README に含める具体的な起動例や環境変数のテンプレート（.env.example 形式）、あるいは systemd / supervisor 用のサンプルユニットファイルも追加できます。どの情報を追加希望か教えてください。