# KabuSys

日本株向け自動売買システムのリポジトリ（README）。このドキュメントはこのコードベースをローカルでセットアップし、主要コンポーネントを起動／利用するための手順と構成をまとめたものです。

> 本リポジトリはモジュール化されたトレーディングエンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含みます。多くのスクリプトは環境変数（.env）で挙動を切り替える設計です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したコンポーネント群を提供します。主な目的は以下です。

- 市場データ（DuckDB）を使ったファクター計算・リサーチ
- シグナルに基づくポートフォリオ構築（候補選定・重み付け・株数計算）
- ExecutionEngine による発注管理（paper_trading モードあり）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch による安全停止
- OpenAI を使ったニュースセンチメント（AI モジュール）
- 運用用ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証ツール 等）

設計方針の一部：
- 本番用 DB（monitoring 等）と paper_trading 用 DB は分離（Paper Trading は専用 SQLite を利用）。
- .env（環境変数）により挙動を切り替え。自動ロード機能あり（プロジェクトルートの .env/.env.local）。
- ロギングは統一的に設定（stdout + 日次ローテーションファイル）。
- OpenAI API 経由の処理はフェイルセーフ設計（API失敗時はフォールバック）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注実行
  - BrokerClientFactory により実環境／Mock（paper_trading）を切替
  - RiskManager / OrderManager / Reconciler 等の運用コンポーネント
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス死活、データ鮮度チェック
  - TradeMonitor: 注文状態監視（滞留注文・約定異常等）
  - RiskMonitor: ドローダウン・保有数上限監視（kill switch 連携）
  - MonitoringEngine: 定間隔で各モニタをポーリング・アラート発火
  - monitoring_db: SQLite ベースの永続化層 + マイグレーション処理
- Portfolio
  - 候補選定、等金額／スコア加重重み、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、ファクター統計
- AI
  - news_nlp: ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector: マクロ+MA を組合せて市場レジーム判定・保存
- Tools
  - paper_verification_report: ペーパートレードの検証レポート生成
- Utilities
  - logging_setup: ルートロガーの統一設定
  - process_priority: プロセス優先度・CPU affinity 設定
  - config_setup / validate_config: .env 作成ウィザード、設定検証 CLI

---

## 前提・依存関係

主な Python パッケージ（実際の requirements.txt がない場合は概ね下記が必要になります）:

- Python 3.8+
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- pyyaml （config/*.yaml の検証に必要だが必須ではない）
- sqlite3（標準ライブラリとして同梱）

ログディレクトリや DB 保存先に書き込み権限が必要です。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン / 取得
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があればそれを使用してください）
4. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成
5. 設定検証
   - python -m kabusys.validate_config
   - 必要であれば --strict を付けて警告も FAIL 扱いにする
6. ディレクトリ作成（必要に応じて）
   - data/ （DB・PID・フラグ等）
   - logs/ （ログ）

※ .env は絶対にリポジトリにコミットしないでください（秘密情報を含むため）。

---

## 主要な環境変数（主なもの）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存場所（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / Kill Flag のパス
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

（config_setup.py が主要項目のウィザードを提供します）

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（起動コマンド例）

プロジェクトの主要エントリポイントはモジュール実行（-m）で提供されています。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor 単体運用）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を秒で変更可能（例: export MONITOR_POLL_INTERVAL=30）

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（プログラム内呼び出し）
  - ニューススコアリング: from kabusys.ai import score_news; score_news(conn, target_date, api_key=...)
  - レジーム判定: from kabusys.ai.regime_detector import score_regime; score_regime(conn, target_date, api_key=...)

停止方法：
- run_execution / run_monitoring はプロセスを自己終了させるフラグ（data/stop_requested.flag）をチェックします。停止が必要な場合は該当フラグファイルを作成または Kill Switch を通じて data/kill.flag を作成してください。
- kill_switch は条件満たした場合に data/kill.flag を書き込み、ExecutionEngine 側はそれを検知して停止する仕様です。

ログ：
- デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）。
- 標準出力（stdout）にも出力されます。

---

## 開発・テストのヒント

- モジュール単位の実行が可能（例: MonitoringEngine の run_once は単発実行用 → テスト容易）。
- DuckDB 接続を引数で渡す設計なので、テスト用にメモリ DB やテスト用ファイルを用意して関数を呼び出せます。
- OpenAI を呼ぶ関数は内部で _call_openai_api をラップしており、ユニットテストでは patch で差し替え可能です（例: unittest.mock.patch）。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主なファイル／ディレクトリと用途（抜粋）：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（schema + マイグレーション）
    - system_monitor.py      — システム状態・データ鮮度チェック
    - trade_monitor.py       — （注文関連監視）※コードベースに存在
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込ユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねる実行ロジック
    - alert_manager.py       — アラート送信（LINE など）※コードベースに存在
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション実行）
    - order_manager.py       — Order 管理
    - order_repository.py    — DB への注文履歴保存
    - risk_manager.py        — リスク管理ロジック
    - reconciler.py          — ブローカーとの整合処理
    - broker_factory.py      — BrokerClient の生成（Mock / 実装分岐）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・丸め・資金配分
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — IC / forward returns / 概要統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — paper trading 検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

（上記は主要ファイルの抜粋です。実装の詳細は各ソースを参照してください。）

---

## 注意事項 / 運用上の留意点

- 本番（KABUSYS_ENV=live）では .env の値や Kill Switch の取り扱いに十分注意してください（validate_config は live 時に警告を出します）。
- OpenAI API を使う処理はコストが発生します。API キーの管理、レート制限に留意してください。
- Paper Trading モードは本番 DB と分離しているため、テスト・検証時はこちらを利用することを推奨します。
- ログディレクトリ・DB ディレクトリの権限を確認し、cron / systemd などでデーモン化して運用する場合はパスやユーザー権限に注意してください。
- monitoring_db.init には後方互換のマイグレーションコードが含まれており、既存 DB に対するカラム追加を行います（safe な実装を試みますが、バックアップ推奨）。

---

必要であれば README に追記する内容（例）：
- 開発用のローカル起動手順（systemd unit ファイル例、Docker 化手順）
- テストコマンド（ユニットテスト / CI 設定）
- 詳細な .env.example の内容（機密を除いたサンプル）

追加で README に含めたい項目や、特定ファイルの詳細説明が必要であれば教えてください。