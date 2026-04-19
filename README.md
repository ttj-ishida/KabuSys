# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群）。  
この README は src/kabusys 配下のコードベースに基づく概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

> 対象 Python バージョン: 3.10+（型注釈や `X | None` 記法を使用しているため）  
> 推奨パッケージ（最低限）: duckdb, psutil, openai, PyYAML（config 検証時に任意）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワーク／ユーティリティ群です。主な目的は以下：

- 戦略（ファクター計算、特徴量解析）やポートフォリオ構築のための研究用モジュール
- 発注実行（ExecutionEngine）とそのリスク管理・注文管理
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）による安全停止機構
- Paper Trading 用の分離された DB と検証レポート
- OpenAI を利用したニュース NLP によるセンチメント評価・市場レジーム判定
- 共通ユーティリティ（ロギング設定、プロセス優先度設定 等）

設計上、研究用（DuckDB を使ったファクター計算）と運用用（発注・監視）は分離されており、paper_trading 環境では本番 DB と分離して動作します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - Broker クライアントファクトリ（Mock により paper_trading をサポート）
  - リスク管理（RiskManager / Reconciler / OrderManager 等）
- Monitoring
  - System / Trade / Risk のポーリング監視（python -m kabusys.run_monitoring）
  - ログ永続化（SQLite、monitoring_db モジュール）
  - KillSwitch による安全停止（data/kill.flag）
  - Alert 管理（AlertManager 経由で通知）
- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、統計サマリ
  - 候補選定、重み算定、ポジションサイジング、セクター制約等
- AI（OpenAI）
  - news_nlp: ニュース記事を使った銘柄センチメントの算出（ai_scores テーブルへ）
  - regime_detector: ma200 とマクロニュースを合成した市場レジーム判定
- ツール
  - .env 初期作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）
- ユーティリティ
  - 統一ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度・CPU affinity 設定（kabusys.utils.process_priority）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai PyYAML
   - 実行環境によっては追加パッケージが必要となる場合があります（broker client 実装等）。

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用してください）

4. 環境変数 / .env
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨 / 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - LOG_LEVEL (デフォルト: INFO)
     - OPENAI_API_KEY（news_nlp / regime_detector を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番通知用）
   - .env 作成を対話式で行う:
     - python -m kabusys.config_setup
     - 生成後、python -m kabusys.validate_config で検証（--strict をつけると警告もエラー扱い）

5. ディレクトリの作成
   - data/ と logs/ は自動作成されることが多いですが、権限等で失敗する場合は手動作成してください。

---

## 使い方（実行例）

- ExecutionEngine を起動する
  - 本番/開発の切替は KABUSYS_ENV で制御
  - Paper trading（Mock broker）を使う例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番（注意して実行）:
    - KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring を起動する
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

  備考: run_monitoring は KABUSYS_ENV にかかわらず monitoring 用の本番 sqlite_path を使用します（monitoring DB は本番データに接続する設計）。

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニューススコア / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キーが必要です（OPENAI_API_KEY または関数引数）。
  - 実行には DuckDB 接続オブジェクトを渡す設計です（詳細はモジュール docstring を参照）。

- グレースフル停止 / Kill Switch
  - KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止シグナルを送ります。
  - run_execution/run_monitoring は data/stop_requested.flag の存在で外部的に終了を検知する仕組みがあります（stop フラグの検出でループを抜けます）。

---

## 主要な環境変数（要点）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連（デフォルト値）
  - KABUSYS_ENV: development | paper_trading | live （default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - LOG_DIR: logs/
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0 (1 にすると起動時に kill.flag を自動クリア)
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）

- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector で使用

---

## 注意事項 / 運用上のヒント

- Paper Trading は production DB と分離されます（settings.is_paper が有効なとき paper_sqlite_path を使用）。実際の発注は行われません（MockBrokerClient）。
- run_monitoring は「監視用 DB を常に本番パスで参照する」設計のため、環境による DB 切り替えを行いません。意図的な設計です。
- Stop / Kill 機構:
  - data/stop_requested.flag: run_* のループを外から止めるためのフラグ（存在検知でループ終了）。
  - data/kill.flag: KillSwitch によるエンジン停止指示（ExecutionEngine 側で検知し停止）。
- ログは logs/<app_name>.log に日次ローテーションで保存（ログディレクトリ作成に失敗した場合はコンソール出力のみ）。
- OpenAI 関連は API 呼び出し失敗（429/タイムアウト/5xx）に対してリトライ実装があり、フェイルセーフで部分失敗に耐える設計になっていますが、API キー管理・コストには注意してください。
- validate_config で本番環境（KABUSYS_ENV=live）を誤設定していないか、LINE 通知設定等が正しいかを確認してください（本番では慎重に）。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ定義・バージョン
- config.py
  - 環境変数と .env の自動読み込み、Settings クラス
- config_setup.py
  - .env 作成ウィザード（対話式）
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（スレッドでエンジン実行、stop flag 監視）
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- ai/
  - news_nlp.py — ニュースを OpenAI で評価して ai_scores に書き込むロジック
  - regime_detector.py — ma200 とマクロニュースからレジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・簡易 CRUD（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度チェック
  - risk_monitor.py — ドローダウン / ポジション数監視
  - trade_monitor.py — （注文系監視、ソース参照）
  - kill_switch.py — data/kill.flag の管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信ロジック、ソース参照）
- execution/
  - execution_engine.py — ExecutionEngine（起動、セッション制御）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注管理・リスク管理関係
- portfolio/
  - portfolio_builder.py — 候補選定・重み算定
  - position_sizing.py — 株数決定・丸め・制約処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
- utils/
  - logging_setup.py — 統一的なログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定

（上記に加えて、config/ 以下に YAML 形式の設定ファイルを想定する設計あり）

---

## 開発・デバッグのヒント

- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）がないと research / AI 関連は動かないため、開発用にテストデータを準備してください。
- validate_config は PyYAML 未インストール時に YAML 検査をスキップします。YAML 検証を行う場合は PyYAML を入れてください。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御可能です。
- process_priority.set_process_priority("high") を起動直後に呼ぶ設計になっています。権限がない場合は警告ログになります。

---

必要であれば、README にサンプル .env（機微な値は伏せた例）や、よく使う CLI コマンド集、よくあるトラブルシューティング（DB 権限、OpenAI エラー、ファイルパス権限）を追加できます。どの内容を詳細化したいか教えてください。