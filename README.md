# KabuSys

日本株向け自動売買システム（KabuSys）のソースコード README。  
この README はリポジトリ内の主要モジュールから作成した開発者/運用者向けの導入・利用ガイドです。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- よく使う環境変数（主要設定）
- ディレクトリ構成（主要ファイル一覧）
- 運用上の注意事項

---

## プロジェクト概要

KabuSys は日本株の自動売買/研究基盤を目的とした Python ベースのシステムです。  
主に次の役割を持つコンポーネントが含まれます。

- ExecutionEngine：発注処理（本番 / ペーパートレード切替可能）
- Monitoring：システム稼働状況・注文状況・リスク（ドローダウン等）の監視とアラート
- Portfolio：銘柄選定・配分・建玉サイズ決定ロジック（純粋関数群）
- Research：ファクター計算、特徴量解析ユーティリティ（DuckDB を使用）
- AI モジュール：ニュースセンチメント（OpenAI）を用いたスコアリングやレジーム判定
- ユーティリティ群：ログ設定、プロセス優先度設定、.env ウィザード／検証ツールなど

設計方針として、ルックアヘッドバイアス回避、DB分離（本番 / paper_trading）、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- run_execution.py：ExecutionEngine を起動（KABUSYS_ENV に応じて本番 or ペーパートレード）
  - paper_trading モードでは MockBroker を使用し、data/paper_trading.db に記録
  - プロセス優先度設定（高）・PID ファイル管理・停止フラグ監視
- run_monitoring.py：SystemMonitor のポーリングループ起動（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL で間隔調整可
  - 監視ログは sqlite（monitoring.db）へ保存、DuckDB も併用
- monitoring/*：MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、KillSwitch、AlertManager 等
- portfolio/*：候補選定、重み計算、セクター制約、レジーム乗数、ポジションサイズ算出
- research/*：ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算
- ai/*：news_nlp（ニュースを OpenAI でセンチメント評価して ai_scores に保存）、regime_detector（MA と LLM を合成して日次レジーム判定）
- tools/paper_verification_report.py：ペーパートレード結果の検証レポート生成（稼働率、成立率、レイテンシ等）

---

## セットアップ手順

前提：Python 3.9+（実際の要件は pyproject.toml 等を参照）

1. リポジトリをクローン、ワークディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必要な主要パッケージ（例）：duckdb, psutil, openai, PyYAML（YAML 検証用）など
   - ※ requirements.txt がない場合はプロジェクトの import を参考に個別に追加

4. 環境変数設定（.env）
   - 簡易ウィザードで生成:
     - python -m kabusys.config_setup
   - 手動の場合はプロジェクトルートに `.env` を作成（.env.example を参照）
   - 自動ロード: デフォルトで .env / .env.local を読み込みます。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプト（run_execution / run_monitoring）が起動時に必要なテーブルを作成します（init_monitoring_db）。明示的な初期化は不要です。

---

## 使い方（コマンド例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 or paper_trading は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading → MockBroker を使い data/paper_trading.db に記録
    - PID ファイル: data/execution.pid（Settings で上書き可）
    - 停止は data/stop_requested.flag を作成するか Monitoring の KillSwitch が data/kill.flag を書き込む

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  （秒）
  - 監視は常に本番用 sqlite_path を使用（環境にかかわらず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/data/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH で指定可

- AI モジュール使用例（スクリプトやスケジューラから呼ぶ）
  - OpenAI API の利用には OPENAI_API_KEY が必要
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して使用
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## よく使う環境変数（主要設定）

- JQUANTS_REFRESH_TOKEN：J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD：kabuステーション API パスワード（必須）
- KABUSYS_ENV：実行環境（development / paper_trading / live） — default: development
  - paper_trading: 発注はモック化、paper_trading DB に記録
  - live: 本番（注意喚起や検証を確実に）
- OPENAI_API_KEY：OpenAI API キー（AI モジュールで必須）
- PAPER_FILL_MODE：paper trading の fill 動作（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH：paper_trading 用 SQLite（default: data/paper_trading.db）
- SQLITE_PATH：監視 DB（default: data/monitoring.db） — Monitoring は常に本番 sqlite_path を使います
- DUCKDB_PATH：DuckDB ファイルパス（default: data/kabusys.duckdb）
- LOG_LEVEL：ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR：ログ保存先ディレクトリ（default: logs）
- MONITOR_POLL_INTERVAL：run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_PATH：KillSwitch が書き込むパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START：起動時に kill.flag を自動クリアする（0/1、本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 を設定すると .env 自動読み込みを無効化

注意：必須環境変数が未設定だと Settings クラスや validate_config によりエラーになります。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/               — 発注関連（BrokerFactory, ExecutionEngine, OrderManager...）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化 API
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — 注文滞留・約定異常監視（ファイル中に含まれる）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - alert_manager.py       — （アラート送信の抽象化：LINE 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py     — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py — forward return, IC, summary
  - ai/
    - news_nlp.py            — ニュース → OpenAI による銘柄別スコア化・書き込み
    - regime_detector.py     — MA と LLM を合成した市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

  - utils/
    - logging_setup.py       — 統一的なログ設定（コンソール + 日次ローテートファイル）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

データ・ログ・PID などの既定パス（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag
- logs/<app_name>.log

---

## 運用上の注意事項

- KABUSYS_ENV=live に設定する場合は十分に設定を確認してください（validate_config で警告が出ます）。
- .env は機密情報を含むため絶対に VCS にコミットしないこと。
- run_monitoring は監視用に常に「本番」SQLite（Settings.sqlite_path）を参照します。テスト時に別 DB を使いたい場合は適切に設定を変更してください。
- ペーパートレードは本番 DB と分離されており、PAPER_TRADING_SQLITE_PATH を利用します。
- OpenAI API を使うモジュールは API キーが必要です。API 呼び出し失敗時はフェイルセーフ（0.0 等）で続行する設計ですが、結果の品質に注意してください。
- 停止方法：
  - ExecutionEngine は data/stop_requested.flag の存在を検知して終了します（run_execution / run_monitoring で参照）。
  - Monitoring の KillSwitch が条件を満たすと data/kill.flag を書き込み、Execution に停止シグナルを送ります。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通して一元管理されます。ログディレクトリが作成できない場合はコンソール出力のみになります。

---

必要であれば、さらに具体的なコマンドの実行例、.env のサンプル（例: .env.example 形式）、または各モジュールの詳しい API ドキュメント（関数引数・戻り値の詳細）を追加で作成します。どの部分を詳細化しますか？