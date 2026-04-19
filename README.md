# KabuSys

日本株自動売買システムの参照実装ライブラリ / 実行スクリプト群です。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主要コンポーネントは次のとおりです。

- ExecutionEngine：発注・リスク管理・注文管理を行う実行エンジン（本番／ペーパートレード対応）
- Monitoring：システム稼働状態、注文・リスク監視、Kill Switch を扱う監視機構
- Portfolio：銘柄選定・重み付け・ポジションサイズ計算
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：OpenAI を用いたニュースセンチメント / 市場レジーム判定
- Tools：ペーパートレード検証レポートなどユーティリティ

設計方針として、ルックアヘッドバイアス回避・フェイルセーフ（API失敗時は継続）・DB分離（paper_trading と本番の DB を分ける）などが組み込まれています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine 起動（KABUSYS_ENV により paper_trading と live を切替）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 環境設定 / 検証
  - config_setup: .env の対話式ウィザード生成
  - validate_config: .env と config/*.yaml の整合性チェック
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - SQLite を用いた監視ログ（data/monitoring.db）
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスク調整、ポジションサイズ算出（単元株丸め等）
- リサーチ
  - モメンタム、ボラティリティ、バリューファクター計算（DuckDB 使用）
  - 将来リターン、IC 計算、統計サマリ等
- AI（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores に格納
  - マクロニュース + ETF MA200 を組み合わせたレジーム判定
- ツール
  - paper_verification_report: ペーパートレードの稼働性・成功率・レイテンシ等のレポート生成

---

## 前提条件（最低限）

- Python 3.9+
- パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検査用、無くても動作するが警告が出る）
- OS 権限（プロセス優先度設定や CPU affinity の一部操作は管理者権限が必要な場合があります）

requirements.txt がない場合は例として次をインストールしてください:

pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を手動で配置
   - 自動ロード:
     - .env と .env.local は Settings モジュールで自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
     - ロード順: OS 環境 > .env.local > .env

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 必須環境変数が揃っているか、DB パスの親ディレクトリなどをチェックします
   - --strict を付けると警告も失敗（exit 1）扱いになります

5. データディレクトリ作成（必要なら）
   - デフォルト DB/ログ/データはプロジェクト相対パスの `data/` と `logs/` を使用します
   - 必要に応じて `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`, `LOG_DIR` を .env で上書き

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY — AI モジュール使用時に必要
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB デフォルト: data/paper_trading.db
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading 時のモック約定方式（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

---

## 実行方法（利用例）

- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - 起動時に data/execution.pid が作成されます（Settings.pid_file_path 参照）
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、ペーパートレード DB（PAPER_TRADING_SQLITE_PATH）へ記録され本番 DB とは分離されます

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring で間隔を変更可能
  - 監視は Settings.sqlite_path（監視用 DB）を使用します（環境にかかわらず本番 monitoring DB を使う設計）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（プログラムから呼び出す例）
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - これらは OpenAI API キー（OPENAI_API_KEY または引数）を必要とします

---

## 運用上の注意 / 特記事項

- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります
  - run_execution/run_monitoring は data/stop_requested.flag の存在でループを停止します
  - 本番運用では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（自動クリアは危険）

- DB 分離
  - paper_trading モードでは paper_trading 用の SQLite DB（デフォルト data/paper_trading.db）を使用します。監視 DB は別途 monitoring.db を使用します。

- ログ
  - デフォルトで stdout と日次ローテートファイル logs/<app_name>.log に出力します
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみになります

- プロセス優先度
  - 起動時に set_process_priority("high") を呼びますが、権限不足で警告が出ることがあります（スキップされます）

- DuckDB / SQLite
  - リサーチ・AI モジュールは DuckDB 接続を受け取り SQL 中心で計算します
  - monitoringDB は SQLite を用いて監視ログ／ダッシュボード等を永続化します

---

## ディレクトリ構成（概要）

下記は src/kabusys 以下の主要ファイル・モジュールの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — Settings クラス（.env 自動読み込み・環境変数取得・バリデーション）
  - config_setup.py — .env 対話式ウィザード生成
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/utils/
  - logging_setup.py — 統一的なロギング設定（Stream + TimedRotatingFileHandler）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ラッパー
  - __init__.py

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（テーブル作成 / CRUD ラッパー）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - risk_monitor.py — ドローダウン・ポジション数監視（RiskMonitor）
  - trade_monitor.py — （注文系監視、ファイルに含まれる想定）※実装ファイルあり
  - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
  - kill_switch.py — Kill Switch 実装
  - alert_manager.py — （アラート送信の管理、ファイルに含まれる想定）

- src/kabusys/execution/
  - execution_engine.py — 実行エンジン本体（EngineConfig, run_session 等）
  - broker_factory.py — ブローカークライアント生成（Mock / 本番）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・調整・リスク管理の部品

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け関数
  - position_sizing.py — 株数決定・上限・aggregate cap 等
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py — エクスポート

- src/kabusys/research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores テーブルへ保存
  - regime_detector.py — マクロニュース + ETF MA200 を使ったレジーム判定
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証用レポート生成スクリプト
  - __init__.py

- data/ (デフォルト)
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid, kill.flag, stop_requested.flag などのフラグ / PID ファイル

- logs/ (デフォルト)
  - execution.log, monitoring.log, ... 日次ローテートで保存

---

## よくある操作例

- .env を新規作成して検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ペーパートレードで Execution を起動
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視プロセスを起動（ポーリング間隔を 30 秒に）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Kill Switch を発動（手動）
  - echo "reason ..." > data/kill.flag
  - Execution 側が kill.flag を検知して停止・ログ等を出します

---

## 開発メモ / 拡張ポイント

- Strategy / Execution の詳細は各ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に従って設計されています。将来的に lot_size を銘柄別にする、スリッページ推定を改善する等の拡張が想定されています。
- AI 関連は OpenAI SDK のバージョン変化に伴うエラーハンドリング差異に注意してください。
- DuckDB のバインドや executemany の挙動はバージョン依存で微妙な差があるため、DB 周りのユニットテストを整備することを推奨します。

---

必要であれば README にサンプル .env のテンプレートや各 CLI の詳細な引数一覧、ユースケース別の運用手順（本番切替手順、障害時のリカバリ手順）を追加します。どの情報を拡充しますか？