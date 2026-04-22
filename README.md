# KabuSys

日本株自動売買システムの参照実装ライブラリ / 実行スクリプト群です。  
このリポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、および運用監視（Monitoring）を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つコンポーネント群を提供します。

- 研究（research）: ファクター計算・特徴量探索（DuckDB 上の時系列データを利用）
- ポートフォリオ構築（portfolio）: 候補選定・重み算出・ポジションサイズ計算・リスク調整
- 発注（execution）: ブローカー抽象化、発注管理、リスク管理、再整合（reconciler）
- 監視（monitoring）: システムヘルス、注文ログ、リスク指標の継続監視とアラート連携
- AI 補助（ai）: ニュース NLP によるセンチメント評価、レジーム判定（OpenAI API）
- ツール（tools）: ペーパートレード検証レポートなどユーティリティ

設計方針の要点:
- DuckDB/SQLite を用いて履歴・分析・監視データを保持（ローカルファイルベース）
- 環境変数／`.env` で設定を管理（Settings クラス）
- Paper trading と Live を明確に分離（paper_trading 用 DB を別ファイルに保持）
- ルックアヘッドバイアス回避のため日付参照は基本的に引数ベース

---

## 主な機能一覧

- Settings 管理（環境変数の自動ロード・検証）
- .env 対話式生成ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV により paper_trading モードでの MockBroker 利用
  - 発注・リスク管理・再整合機能
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング
  - kill.flag による安全停止、停止フラグ検知（data/stop_requested.flag 等）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整
- MonitoringDB（SQLite）: system_status、trade_logs、positions、risk_logs、dashboard テーブル
- ポートフォリオ構築ユーティリティ:
  - 候補選定（select_candidates）
  - 等配分・スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- 研究（research）:
  - モメンタム / ボラティリティ / バリューファクターの計算
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- AI モジュール:
  - ニュースを OpenAI (gpt-4o-mini 等) でスコア化し ai_scores に登録
  - 市場レジーム判定（マクロニュース + ETF MA200 を組合せ）
- ツール:
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要要件（概略）

- Python 3.9+
- 依存ライブラリ（例）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config 検証で YAML 検証を有効にしたい場合）
- SQLite（Python 標準ライブラリで利用可能）
- 実行環境に応じたブローカー接続設定（kabuステーション等）

インストール例（venv 利用）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt を用意している場合。個別に duckdb psutil openai などをインストールしてください。
```

---

## セットアップ手順

1. リポジトリをクローンしてソースツリーへ移動
2. 仮想環境を作成・有効化して依存をインストール
3. 初期設定ファイル（.env）を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要なオプション:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い
5. 必要に応じてデータディレクトリを作成:
   - data/（DB・flag・pid を格納）
   - logs/（ログ出力先。logging_setup が自動作成を試みます）

注意:
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください。
- KABUSYS_ENV が `paper_trading` の場合、発注は MockBroker を利用して data/paper_trading.db に記録され、本番 DB（monitoring.db）とは分離されます。

---

## 使い方（主要なコマンド例）

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - 起動時にプロセス優先度を "high" に設定し、SQLite/ DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用
    - data/stop_requested.flag の有無で起動可否・停止を制御
    - 実行中の PID は data/execution.pid に書き出される

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor を一定間隔でポーリングし system_status 等を記録
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60）
    - 監視は常に「本番 sqlite_path」を使用（環境に関わらず監視 DB は production path を参照）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（プログラム上から呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY が使われます

ログ設定:
- 全スクリプトは共通の logging_setup を使ってログを設定します（コンソール + 日次ローテートファイル）
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数で制御

停止・Kill Switch:
- monitoring の KillSwitch は risk monitor 等の条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine は data/stop_requested.flag や stop フラグを監視し安全停止します。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル／モジュール構成（src/kabusys 以下）です。必要に応じてプロジェクトルートに配置されます。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        (実装ファイルは本例に一部のみ含まれます)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        (実装想定)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に利用する DB / flag / pid（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）
  - logs/                    — ログファイル出力先（デフォルト）

（注: 上記は本リポジトリにあるソースのサブセット説明です。実際の追加スクリプトやユーティリティが存在する可能性があります。）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨/任意:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（例: INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（監視間隔、秒。run_monitoring が参照）

詳細は kabusys.config.Settings のドキュメントを参照してください。

---

## 運用上の注意 / トラブルシューティング

- .env の管理:
  - .env は機密情報を含むため Git にコミットしないこと。
  - config_setup で作成した後、 validate_config で検証してください。
- Paper trading と Live の DB は分離されます。Paper モードでのデータは data/paper_trading.db に記録され、本番監視 DB には影響しません。
- AI 機能:
  - OpenAI の API 呼び出しに失敗した場合はフェイルセーフ（スコア 0.0 など）にフォールバックして実行を継続しますが、適切な API キーとレート管理を行ってください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（警告ログあり）。
- psutil によるプロセス優先度 / CPU affinity の設定は権限に依存します。権限がないと警告を出してスキップします。
- SQLite / DuckDB ファイルのパスが含まれる親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、config 検証で WARN が出ます。事前に作成することを推奨します。

---

## 参考 / 追加情報

- 各モジュールの docstring に詳細な設計注記・振る舞いが記載されています。実装や拡張を行う際は該当ファイルを参照してください。
- config/*.yaml（system_config.yaml 等）は別途管理される想定です。存在しない場合は警告が発生します（validate_config が検出）。

---

問題や改善要望があれば、具体的な用途（開発 / テスト / 本番）と実行コマンド、発生しているエラーやログを添えてご相談ください。