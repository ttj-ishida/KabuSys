# KabuSys

日本株向け自動売買システムのパッケージ（ライブラリ／ランタイム用）。  
このリポジトリには、実行エンジン・監視モジュール・ポートフォリオ構築・リサーチ・AI（ニュースNLP / レジーム判定）などの主要コンポーネントが含まれます。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群を提供します。

- ExecutionEngine：発注・注文管理・リスク管理の実行ランタイム（本番・ペーパーの切替対応）
- Monitoring：システム稼働・注文滞留・リスク監視、Kill Switch によるエンジン停止制御
- Portfolio：候補選定、重み付け、ポジションサイズ算出（純粋関数）
- Research：ファクター計算、将来リターン、IC などの解析ユーティリティ（DuckDB を利用）
- AI：ニュースの NLP スコアリング、マクロニュースを使った市場レジーム判定（OpenAI）
- Tools：Paper Trading の検証レポート生成などの補助スクリプト
- Utils：プロセス優先度・CPU affinity 設定など実行環境向けユーティリティ

設計上の特徴：
- 環境変数による設定（.env / .env.local 自動読み込み、オーバーライド可能）
- DuckDB / SQLite を用いたローカル DB（分析用・監視用に分離）
- Paper Trading（モックブローカー）を利用した検証が可能
- OpenAI（gpt-4o-mini）を利用した NLP 処理（オプション）

---

## 主な機能一覧

- execution
  - ExecutionEngine の起動制御（本番 / paper_trading 切替）
  - BrokerClientFactory によるブローカークライアント作成（paper_trading は Mock）
  - OrderManager / RiskManager / Reconciler による注文運用
- monitoring
  - SystemMonitor：CPU/MEM/DISK・プロセス生存確認・データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション数監視とダッシュボード更新
  - KillSwitch：条件で kill.flag を書いて ExecutionEngine を停止
  - MonitoringEngine：上記モニタの統合ポーリング（interval 指定）
- portfolio
  - 銘柄候補選定、等重・スコア重み付け
  - セクター制限、レジーム乗数適用
  - ポジションサイズ算出（単元株丸め、利用可能資金に応じたスケーリング）
- research
  - momentum / volatility / value 等のファクター算出（DuckDB に対する SQL）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- ai
  - news_nlp.score_news: raw_news を集約し LLM へ投げて ai_scores を書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせて日次レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定付きレポートを出力

---

## セットアップ手順

前提
- Python 3.10 以上（typing 演算子 | を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の YAML 検証を使う場合）
  - これらは pip でインストールしてください。

例:
pip install duckdb psutil openai PyYAML

.env の準備
1. 対話式ウィザードで .env を作成・更新できます:
   python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 任意: LINE_TOKEN、LINE_USER_ID（通知用）

2. 自動ロード:
   - デフォルトでパッケージ import 時にプロジェクトルートの `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能利用時）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定振る舞い: instant | partial | never | reject）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KILL_FLAG_CLEAR_ON_START（0/1。本番で 1 は危険）

DB・ディレクトリの初期化
- 実行時に必要なディレクトリ（data/）は各スクリプトが自動作成する場合がありますが、事前に作っておくと安心です。
- DuckDB と SQLite は指定パスにファイルとして作成されます。

---

## 使い方

一般的なコマンド例（プロジェクトルートで実行）:

1. 環境ウィザード（.env 作成）
   python -m kabusys.config_setup

2. 設定検証
   python -m kabusys.validate_config
   # 警告をエラー扱いにする
   python -m kabusys.validate_config --strict

3. ExecutionEngine（発注エンジン）を起動
   python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_trading DB に記録します（本番 DB と分離）。
   - 実行中に data/stop_requested.flag が作成されると安全に停止します。
   - 実行時に data/execution.pid を作成します（PID ファイル）。

4. Monitoring（監視ループ）を起動
   python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
   - 監視は常に本番用 sqlite_path を参照します（環境にかかわらず monitoring は本番 DB を使用する実装上の仕様）。
   - Monitoring は必要に応じて kill.flag を書き、ExecutionEngine に停止を促します（KillSwitch 機能）。

5. Paper Trading 検証レポート生成
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB パスを明示する場合:
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

AI 関連（プログラムから呼び出す例）
- ニュース NLP スコア生成（Python から）
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  from kabusys.ai.news_nlp import score_news
  score_news(conn, date(2026, 4, 11), api_key="...")  # api_key を渡すか OPENAI_API_KEY を設定

- レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 4, 11), api_key="...")

停止・Kill
- 手動停止（外部プロセスを止める）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して停止します。
- Kill Switch:
  - Monitoring の条件に合致すると KillSwitch が設定した path（デフォルト data/kill.flag）にフラグを書き、ExecutionEngine を停止させる仕組みがあります（Settings.kill_flag_path でパスを変更可能）。

ログレベル
- LOG_LEVEL 環境変数で調整。実行時は標準出力に INFO 以上が出ます。詳細なデバッグを見たい場合は LOG_LEVEL=DEBUG。

---

## ディレクトリ構成（抜粋）

以下は主なファイル・ディレクトリのツリー（src/kabusys 配下を中心に抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py              # 環境変数/.env ロードと Settings クラス
    - config_setup.py        # 対話式 .env ウィザード
    - validate_config.py     # 設定検証 CLI
    - run_execution.py       # ExecutionEngine 起動スクリプト
    - run_monitoring.py      # SystemMonitor ポーリング起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py  # プロセス優先度 / CPU affinity ユーティリティ
    - execution/             # （省略）ExecutionEngine / OrderManager 等
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py     # （省略、アラート送信の責務）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py

- data/                    # 実行時に使用する DB / フラグ / PID など（default paths）
  - kabusys.duckdb         (デフォルト: data/kabusys.duckdb)
  - monitoring.db          (デフォルト: data/monitoring.db)
  - paper_trading.db       (paper_trading 用デフォルト: data/paper_trading.db)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- config/                  # system_config.yaml 等（存在を期待するが無ければ警告）
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

---

## 追加メモ / 注意事項

- .env は機密情報を含むため、絶対に Git にコミットしないでください（config_setup でも警告を出します）。
- Paper Trading は本番 DB と分離されるよう設計されています。KABUSYS_ENV=paper_trading を使うと paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）が使用されます。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要です。また料金やレート制限に注意してください。
- validate_config は PyYAML がインストールされていると config/*.yaml の構文チェックを行います。未インストール時は YAML 検証をスキップします。
- モジュールの一部（例: BrokerClientFactory、ExecutionEngine、OrderRepository 等）はこの README の抜粋に含まれていません。実運用する際はそれらの実装や設定も確認してください。

---

必要であれば、以下の点について README に追記します：
- 各コンポーネント（ExecutionEngine / OrderManager / RiskManager）の詳細設計ドキュメントの要約
- docker-compose / systemd での運用例
- 開発時のユニットテスト実行方法

どれを追加しますか？