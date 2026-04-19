# KabuSys

日本株自動売買システムのコアライブラリ。ポートフォリオ構築、発注実行、監視・アラート、リサーチ、AI支援（ニュースセンチメント/レジーム判定）などの機能を含む。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な機能は次の通りです。

- 戦略・ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制限、レジームによる資金乗数）
- 注文実行エンジン（実口座 / ペーパートレードを切り替え可能）
- 監視（システム状態・データ鮮度・注文状態・リスクの定期チェック）
- Kill Switch（閾値超過時に安全停止フラグを書き込み）
- AI モジュール（ニュースセンチメントによる銘柄スコアリング、市場レジーム判定、OpenAI 利用）
- リサーチ機能（ファクター計算、特徴量探索、IC 計算）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定等）

---

## 機能一覧（抜粋）

- config_setup: 対話式に `.env` を生成・更新するウィザード（python -m kabusys.config_setup）
- validate_config: 起動前の環境変数 / config/*.yaml の検証（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に書き込む
  - プロセス優先度を高く設定
  - 停止は data/stop_requested.flag や kill.flag により制御
- SystemMonitor / MonitoringEngine（監視ループの起動: python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視結果は SQLite（data/monitoring.db）へ永続化
- KillSwitch: drawdown・ポジション上限等で kill.flag を作成して ExecutionEngine を停止
- AI:
  - news_nlp.score_news: raw_news を集約して OpenAI に送信し ai_scores を更新
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースでレジーム判定
- ツール:
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

---

## 前提条件

- Python 3.9+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の中身検証に利用）
- ファイルシステムに `data/` と `logs/` などを作成できる権限

（requirements.txt は本リポジトリに含まれていません。実行環境に合わせて必要パッケージをインストールしてください。）

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをチェックアウト
   - git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. 初期設定（.env）を対話式で作成
   - python -m kabusys.config_setup
   - このウィザードは `.env`（デフォルト: プロジェクトルート/.env）を生成します。
   - 重要: `.env` は決して Git にコミットしないでください。

5. 設定検証（オプション）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

6. ディレクトリ準備（デフォルトのデータ・ログパスを使用する場合）
   - mkdir -p data logs

---

## 実行方法・使い方

### 1) 実行エンジン（ExecutionEngine）を起動

- 開発（発注なし）:
  - KABUSYS_ENV=development を使います（config_setup のデフォルト）
- ペーパートレード（MockBrokerClient、別 DB に記録）:
  - KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - ペーパートレード DB のデフォルト: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
- 本番:
  - KABUSYS_ENV=live（十分注意して使用）

起動時の挙動:
- 実行中の PID を data/execution.pid に書き、data/stop_requested.flag の存在で停止処理を行います。
- process priority を high に設定する試みを行います（psutil 権限に依存）。

停止:
- data/stop_requested.flag を作成すると起動中のエンジンに停止シグナルが送られます。
- KillSwitch により `data/kill.flag` が生成されると、次回エンジン起動時に kill を検知します（KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動クリアするオプションあり）。

### 2) 監視ループを起動

- python -m kabusys.run_monitoring
- 環境変数で制御:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - LOG_LEVEL / LOG_DIR などは logging_setup で反映されます。
- 監視は SQLite（settings.sqlite_path、デフォルト data/monitoring.db）にログを保存します。

### 3) 設定検証・ウィザード

- 対話式ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1) になります

### 4) ペーパートレード検証レポート

- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

### 5) AI モジュール（プログラムから利用）

- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡し、OpenAI API キーは引数または OPENAI_API_KEY 環境変数で指定
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に DuckDB と API キーを渡して使用

呼び出し例（簡易）:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, date(2026, 4, 10), api_key="sk-...")

注意: OpenAI API 呼び出しを行うため API キーと通信環境が必要です。API 利用は課金に注意してください。

---

## 停止とフラグ管理

- data/stop_requested.flag
  - run_execution/run_monitoring が監視する停止フラグ（存在するとループを抜ける）
- data/kill.flag
  - KillSwitch が書き込むフラグ。ExecutionEngine の安全停止トリガーとして利用
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に自動クリア可能（本番では 0 推奨）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- OPENAI_API_KEY（AI モジュールで利用）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（0/1。起動時に kill.flag を自動クリアするか）

詳細は `kabusys.config.Settings` を参照してください（プロパティの説明があります）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数・.env のロード／Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコアリング
  - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite の監視用テーブル定義・永続化レイヤ
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — 注文ログ監視（stale/anomaly 検出）※別ファイルあり
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — Kill Switch（フラグファイル書き込み）
  - monitoring_engine.py   — 各モニタを束ねるエンジン
  - alert_manager.py       — 通知管理（LINE 等、実装に依存）
- execution/               — 発注に関する実装群（Engine, OrderManager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — IC・統計解析
- monitoring/               — 監視関連（上記）
- monitoring/tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

トップレベル（実行時に作られる / 参照される）
- data/                    — デフォルト DB・フラグ・PID を格納
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite)
  - kabusys.duckdb (DuckDB) ※デフォルト path は data/kabusys.duckdb
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/
  - execution.log
  - monitoring.log
  - ...（アプリ名ごとにローテート）

---

## 開発・運用時の注意点

- .env に機密情報（API トークン / パスワード）を保存する場合、絶対にリポジトリへコミットしないでください。
- run_execution は本番環境（KABUSYS_ENV=live）で実際に発注を行います。十分な確認の上で実行してください。
- AI モジュールは外部 API（OpenAI）を使用します。呼び出しには API キーと課金が必要です。API レート制限やエラーに対するリトライロジックはありますが、費用・影響に注意してください。
- 監視・Kill Switch により強制停止される可能性があります。ログ（logs/）と data/monitoring.db を参照して原因を確認してください。
- DuckDB / SQLite のファイルパスは環境変数で変更できます。開発環境と本番環境で DB を分離することを推奨します（特に PAPER_TRADING_SQLITE_PATH）。

---

## よく使うコマンド例

- .env を作る（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README を英語版に翻訳したり、起動・運用のデプロイ手順（systemd / supervisor / コンテナ化）や推奨の requirements.txt を追加で作成します。どの形式が必要か教えてください。