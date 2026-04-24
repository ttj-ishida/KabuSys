# KabuSys

日本株自動売買システムのコアライブラリ（リサーチ / ポートフォリオ構築 / 発注実行 / 監視 / AI補助）。  
このリポジトリは、戦略の研究（DuckDBベース）、ポートフォリオ/ポジション計算、発注エンジン、監視エンジン、LLMを用いたニュース解析・レジーム判定などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（重要なもの）
- 使い方（主要スクリプト）
- ディレクトリ構成
- 運用上の注意 / 補足

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたソフトウェアモジュール群です。以下を重視して設計されています。

- 研究（ファクター計算、特徴量解析）と実運用（ExecutionEngine、RiskManager）を分離
- DuckDB を用いた高速な分析／履歴参照
- SQLite を用いた監視ログ・ペーパートレード記録
- OpenAI（LLM）を利用したニュースセンチメント解析・市場レジーム判定（オプション）
- 監視（system/trade/risk）および Kill Switch による安全停止機構

---

## 機能一覧

主な機能 / モジュール

- config / config_setup / validate_config
  - .env ウィザード、設定ファイル自動読み込み、設定検証ツール
- execution
  - ExecutionEngine、OrderManager、RiskManager、Broker クライアントの抽象化（paper_trading で MockBroker を使用）
- monitoring
  - SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、DB永続化（SQLite）
- portfolio
  - 候補抽出、重み計算、ポジションサイズ計算、セクター上限・レジーム補正
- research
  - ファクター計算（Momentum / Volatility / Value）、将来リターン、IC計算、統計サマリー（DuckDB 接続）
- ai
  - news_nlp: ニュースを集約して OpenAI でセンチメントを算出、ai_scores に永続化
  - regime_detector: ETF（1321）MA200 等とマクロニュースで市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

ユーティリティ:
- logging_setup: 統一的ログ設定（コンソールと日次ローテートファイル）
- process_priority: プロセス優先度 / CPU affinity 設定

---

## 必要条件

- Python 3.9+（型アノテーションに Path | None などを使用しているため、3.9 以上を想定）
- 以下の Python パッケージ（機能に応じて必須/任意）
  - 必須（ほとんどの機能で必要）
    - duckdb
    - psutil
  - AI 機能を使う場合
    - openai（OpenAI Python SDK）
  - 設定ファイル検証で YAML を検証する場合（任意）
    - PyYAML

（リポジトリに requirements.txt がない場合は、プロジェクトで使用する環境に合わせて必要パッケージをインストールしてください）

例:
```
pip install duckdb psutil openai PyYAML
```

SQLite は Python 標準ライブラリに含まれています。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境の作成（推奨）
```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 必要パッケージのインストール（プロジェクトに合わせて）
```
pip install duckdb psutil openai PyYAML
```

4. .env の作成（対話ウィザード推奨）
```
python -m kabusys.config_setup
```
対話ウィザードに従って J-Quants のトークンや kabuステーション API パスワード等を設定します。
ウィザードは .env に保存します。`.env` は絶対に Git にコミットしないでください。

5. 設定検証
```
python -m kabusys.validate_config
```
問題があればメッセージに従って修正してください。`--strict` オプションで警告をエラー扱いにできます。

6. データディレクトリ等の確認
- デフォルトの DB / ファイルパス（必要に応じて .env で上書き）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
  - PID / FLAG ファイル: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/デフォルト:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、発注はモック化され paper_trading.db に記録（本番 DB と分離）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG 等に変更可能）
- OPENAI_API_KEY: OpenAI を使用する機能（news_nlp, regime_detector）で必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除（1で有効。productionでは0推奨）

注意:
- Monitoring（run_monitoring.py）は KABUSYS_ENV に関係なく sqlite_path（監視 DB）を使用します（監視は本番 DB を参照して監視する設計）。
- Execution（run_execution.py）は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用し本番 DB と分離します。

---

## 使い方（主要スクリプトとコマンド）

- 環境設定ウィザード（.env を作成 / 更新）
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
# --strict を付けると警告もエラー扱い
python -m kabusys.validate_config --strict
```

- ExecutionEngine（発注エンジン）起動
```
python -m kabusys.run_execution
```
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/stop_requested.flag を監視し、存在すればエンジンを停止します。
  - エンジンは data/execution.pid に PID を書き込みます。

- Monitoring（監視ループ）起動
```
# MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を変更可能。デフォルト 60 秒。
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 挙動:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、必要に応じて kill.flag を書き込むなどのアクションを行います。
  - stop フラグ（data/stop_requested.flag）を検知すると監視ループを終了します。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB 指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI 関連（コードから直接呼び出す）
  - ニュースセンチメント書き込み:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY（または api_key 引数）が必要

---

## Kill / Stop 操作について

- stop_requested.flag:
  - run_execution および run_monitoring は data/stop_requested.flag の存在を監視しており、存在すると停止処理を行います。
  - 管理者がプロセスを優雅に停止させたい場合はこのフラグを作成します（例: echo "stop" > data/stop_requested.flag）。
- kill.flag:
  - Monitoring の KillSwitch が条件（例: ドローダウン閾値超過等）に合致した場合、data/kill.flag を書き込みます。ExecutionEngine 側は kill.flag の存在を元に停止する設計です。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると、起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ファイルを削除してクリア:
```
rm -f data/kill.flag data/stop_requested.flag
```

---

## ディレクトリ構成（主なファイルと説明）

（ルートは src/kabusys 以下）

- __init__.py
  - パッケージ初期化、バージョン定義

- config.py
  - 環境変数読み込み、Settings クラス（アプリ設定の一元化）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト

- run_monitoring.py
  - 監視ループ起動スクリプト

- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注・リスク管理・注文管理のコア実装（詳細は各ファイル参照）

- monitoring/
  - monitoring_db.py: SQLite テーブル定義と簡易 DB ラッパー
  - system_monitor.py: システム・データ鮮度監視
  - trade_monitor.py: 発注／約定ログ監視（該当ファイルはコードベースに存在）
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: Kill Switch 実装
  - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
  - alert_manager.py: アラート送信（LINE 等）管理（コードベース参照）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数計算（リスクベース等）
  - risk_adjustment.py: セクター制限・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン / IC / 統計サマリー

- ai/
  - news_nlp.py: ニュースを集約して OpenAI でセンチメント付与
  - regime_detector.py: ETF MA200 + マクロニュースでレジーム判定

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成

- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定

その他: data/（実行時に生成される DB/flag/pid ファイル等）、logs/（ログファイル）

---

## 運用上の注意 / 補足

- 本番（live）環境では設定値を慎重に確認してください（validate_config は live 時に警告を出します）。特に KILL_FLAG_CLEAR_ON_START の扱いは注意。
- AI（OpenAI）を利用する機能は API コスト・レイテンシの影響を受けます。API キーの管理とレートリミットに注意してください。
- DuckDB は分析用、SQLite は監視・発注ログ用と役割分離されています。paper_trading 環境時は SQLite が分離され、本番 DB に影響しません。
- ロギングは logging_setup.setup_logging を通じて統一されます。ログディレクトリの権限や容量管理（ローテーション: 日次・30日分保持）を運用で整えてください。
- process_priority.set_process_priority で優先度を上げようとしますが、権限不足で失敗する場合があります（警告でスキップ）。

---

以上がこのコードベースの概要とセットアップ／運用手順の要約です。  
各サブモジュールの詳細実装は該当ファイルの docstring / コメントを参照してください。追加で README に含めたい項目（例: よくあるトラブルシューティング、開発フロー、テスト手順など）があれば教えてください。