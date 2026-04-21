# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群の抜粋）。  
この README はリポジトリ内の主要コンポーネントの概要、セットアップ、実行方法、およびディレクトリ構成を日本語でまとめたものです。

注意: 実行時の環境依存設定は .env（または環境変数）で行います。機密情報（API トークン等）は .env に保存し、決して Git にコミットしないでください。

---

## 概要

KabuSys は次のような機能を持つ自動売買基盤のコンポーネント群を含みます：

- マーケットデータ集計／ファクター計算（DuckDB を使用）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- ExecutionEngine（発注処理、リスク管理、オーダー管理）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
- ニュースの NLP スコアリング（OpenAI API を利用）
- ペーパートレード検証レポート生成ツール
- 設定ウィザード / 設定検証ツール

主要実行スクリプト（モジュール）:
- run_execution.py — 実行エンジン起動（本番 / ペーパートレード対応）
- run_monitoring.py — 監視ループ起動
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- tools/paper_verification_report.py — ペーパートレード検証レポート生成

---

## 機能一覧（抜粋）

- 環境設定読込（.env 自動ロード、config_setup による作成支援）
- 環境検証（必須環境変数・YAML ファイル・パスの存在チェック）
- ExecutionEngine（ブローカークライアント差し替え可能、paper_trading モードで MockBroker 使用）
- 監視（CPU/Mem/Disk、データ鮮度、プロセス生存、注文の滞留・異常）
- Kill Switch（閾値超過時に data/kill.flag を書き込み Execution を停止）
- ポートフォリオ構築（候補選定、等分／スコア重み、リスクベース配分）
- ポジションサイズ計算（lot 単位丸め、aggregate cap、scale-down）
- リサーチ（モメンタム／ボラティリティ／バリュー等のファクター計算）
- AI 用ニュース NLP（OpenAI を使ったセンチメント集計、バッチ化・リトライ実装）
- Paper Trading 検証レポート生成（稼働率、成功率、レイテンシ等を評価）

---

## 要件（推奨）

- Python 3.9+
- 推奨パッケージ（プロジェクトに requirements.txt がある場合はそちらを使用）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（標準ライブラリで対応）
- ネットワーク接続（本番・OpenAI 利用時）

実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を確認してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もし requirements.txt がなければ少なくとも次をインストール:
     - pip install duckdb psutil openai

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuAPI / LOG_LEVEL などを設定します。

5. 設定を検証
   - python -m kabusys.validate_config
   - 本番運用前は --strict オプションを使い警告も FAIL として扱う:
     - python -m kabusys.validate_config --strict

6. データ/ログ ディレクトリ確認
   - デフォルトで DB は data/ 以下、ログは logs/ 以下に出力されます。
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を設定。

---

## 主要環境変数（主なもの）

- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient を使用し DB は data/paper_trading.db に分離されます。
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で必要）
- LOG_LEVEL: ログレベル ("INFO" 等)
- LOG_DIR: ログ出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 本番で Kill Flag 自動クリアするか (`1` はクリア、推奨は `0`)
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）

その他の設定は config/*.yaml やソース内の Settings クラス参照。

---

## クイックスタート（実行例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（デフォルト環境に従う）
  - python -m kabusys.run_execution
  - ペーパートレードに切り替えるには KABUSYS_ENV=paper_trading を設定。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定: --db PATH（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

注意:
- run_monitoring は stop フラグファイル data/stop_requested.flag の存在を監視して終了します。
- run_execution は同様に data/stop_requested.flag を参照し、data/execution.pid に PID を書きます。
- Kill Switch は条件を満たした場合に data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。

---

## 使い方（主要機能の説明）

- 設定
  - config_setup.py で対話的に .env を作成できます。
  - validate_config.py で .env と config/*.yaml を検証します。

- 実行エンジン（run_execution）
  - Settings に従いブローカークライアント（実口座または Mock）を生成して発注セッションを開始します。
  - paper_trading 環境では paper_trading 用 SQLite に記録し、本番 DB と分離されます。
  - 起動前に data/stop_requested.flag が存在すると起動をキャンセルします。

- 監視（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を用いて定期的にチェックを行い、監視ログを SQLite に記録します。
  - KillSwitch の評価により data/kill.flag を書き込むことがあります（Execution 停止トリガー）。
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能（デフォルト 60 秒）。

- AI（ニュース NLP / レジーム検出）
  - OpenAI API を利用してニュースを銘柄別にスコアリングします（ai.news_nlp.score_news）。
  - レジーム検出モジュール（ai.regime_detector.score_regime）は ETF とマクロニュースを組み合わせて 'bull'/'neutral'/'bear' を判定します。
  - API 呼出しはバッチ化とエクスポネンシャルバックオフで堅牢化されています。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）、重み計算（等分・スコア重み）、ポジションサイズ計算（calc_position_sizes）など、純粋関数として実装されています（DB 参照なし）。

- 監視 DB 操作（kabusys.monitoring.monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard のテーブル管理・読み書きを行います。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys をルートとした主要モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、自動 .env ロード機構
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト

- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM でスコアリング
  - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - __init__.py

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル作成 / 永続化操作
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - trade_monitor.py — 発注ログ監視（ファイル上では省略）
  - kill_switch.py — kill.flag の書き込み / 管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py（アラート送信：ファイル上では省略）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター制限・レジーム乗数
  - __init__.py

- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート
  - __init__.py

- src/kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFile）
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - __init__.py

---

## 運用上の注意

- 機密情報（API キー・パスワード等）は .env に設定し、決して VCS にコミットしないでください。
- 本番運用時は KABUSYS_ENV=live を使用。validate_config の結果を慎重に確認してください。
- Kill Switch / stop フラグ（data/kill.flag, data/stop_requested.flag）や PID ファイルは運用上重要です。自動クリア設定（KILL_FLAG_CLEAR_ON_START）に注意してください。
- run_monitoring は監視用 DB（SQLITE_PATH）を環境に関係なく「本番用パス」で使用します（設計上の注意）。一方、run_execution は paper_trading なら別 DB を使います（PAPER_TRADING_SQLITE_PATH）。

---

## トラブルシューティング

- PyYAML がない場合: validate_config は YAML 内容検証をスキップし、警告を出します。必要に応じて `pip install PyYAML`。
- DuckDB / OpenAI API エラー: ネットワーク・API キーを確認してください。AI 呼び出しは自動リトライを行いますが、API キー未設定はエラーとなります。
- ログファイル作成失敗: LOG_DIR の権限やパスを確認してください。ファイル出力に失敗しても標準出力にはログが出ます。

---

必要に応じて README を拡張できます（CI 設定、デプロイ方法、詳細な API ドキュメント、設計資料へのリンク等）。追加したい項目があれば教えてください。