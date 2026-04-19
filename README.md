# KabuSys

日本株向け自動売買システムのライブラリ／起動スクリプト群です。本リポジトリは戦略・ポートフォリオ構築、実行エンジン、監視、研究ツール、AI（ニュースNL P / レジーム判定）などを含むモジュール構成になっています。

以下はこのコードベースの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群を提供します。

- 戦略（ファクター）とポートフォリオ構築ロジック（純粋関数群）
- 実際の発注処理を担う ExecutionEngine（本番 / ペーパートレード切替）
- 実行状況やシステム状態を記録・監視する Monitoring
- ニュースの NLP による銘柄別センチメント評価（OpenAI を利用）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、IC 計算、統計サマリ）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の例：
- 本番データへのルックアヘッドを防ぐ（date.today()/datetime.today() を直接参照しない設計）
- フェイルセーフ：外部 API エラー時もシステム全体が停止しないよう設計
- 設定は .env に集約。KABUSYS_ENV により挙動（paper_trading / live / development）を切替

---

## 機能一覧（抜粋）

- 環境設定
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行系
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する監視エンジン
  - run_monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - Kill Switch（data/kill.flag を書き込むことで ExecutionEngine を停止させる仕組み）
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスク調整（セクター上限）、ポジションサイズ決定（単元丸め含む）
- 研究・分析
  - DuckDB を用いたファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント（gpt-4o-mini など）→ ai_scores テーブルへ書込み
  - マクロニュース + ETF MA による市場レジーム判定（bull/neutral/bear）
- 運用ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 事前準備 / セットアップ

1. Python 仮想環境を作成・有効化
   - 例: python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 少なくとも次のライブラリが使われます: duckdb, psutil, openai, PyYAML（config 検証時）

3. 環境変数の設定
   - 推奨: 対話式ウィザードで .env を作成
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な任意 / 上書き可能な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
     - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH：デフォルトは data/execution.pid / data/kill.flag
   - .env 自動読み込み:
     - プロジェクトルートに .env/.env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. ディレクトリ作成（実行時に自動で作成されますが事前に用意しておくと良い）
   - data/ , logs/

---

## 使い方（主要コマンド）

- .env を作成（対話式）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
    - 起動前に data/stop_requested.flag が存在すると起動しません
    - 実行中に停止させるには data/stop_requested.flag を作成するか ExecutionEngine 側の kill.flag を利用

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / 研究系をプログラムから呼ぶ例（Python REPL 内で）:
  - DuckDB 接続を作成して呼び出す例:
    - from openai import OpenAI
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, datetime.date(2026,4,1), api_key="your-key-here")
  - 市場レジーム:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, datetime.date(2026,4,1), api_key="your-key-here")

注意: AI 機能は OPENAI_API_KEY が必要。API エラー時は安全側（スコア 0.0 など）で継続する設計です。

---

## 運用上のポイント / 注意事項

- Kill Switch（data/kill.flag）
  - RiskMonitor 等が条件を満たすと kill.flag を書き込み、ExecutionEngine に停止を促します。kill.flag の既存を上書きしないため冪等。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアしますが、本番では 0 を推奨。

- ログ
  - デフォルトで logs/ ディレクトリに日次ローテーション（30日保持）でログを出力します（kabusys.utils.logging_setup）。
  - ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で指定可能。

- DB マイグレーション / 初期化
  - monitoring 用 SQLite は init_monitoring_db でスキーマを自動作成・マイグレーションします（不足列の追加などを含む）。

- Paper Trading
  - ペーパートレードは本番 DB と分離されるよう設計（PAPER_TRADING_SQLITE_PATH）。発注は MockBrokerClient が担当します。

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出します（psutil を使用）。権限不足の場合は警告を出して続行します。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なファイル・モジュール構成（src/kabusys 配下）です。省略されている実装ファイルもありますが、主要な役割を併記します。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                      — 環境変数／.env の読み込み・Settings クラス
  - config_setup.py                — 対話式 .env ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）による銘柄別スコア生成
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite 永続化レイヤ（監視用）
    - monitoring_engine.py         — 各 Monitor の統合
    - system_monitor.py            — システム状態・データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 書き込みロジック
    - (trade_monitor.py 等の他モジュール)
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定、重み計算
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - position_sizing.py           — 発注株数決定、単元丸め、aggregate cap
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py       — 将来リターン計算、IC、統計サマリ
  - utils/
    - __init__.py
    - logging_setup.py             — ロギング初期化ユーティリティ
    - process_priority.py          — プロセス優先度・CPU affinity 設定ユーティリティ
  - execution/
    - (ExecutionEngine, broker factory, order manager 等の実装ファイル群 — 実行処理本体)

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 研究 / AI 呼び出しは Python スクリプト／REPL から関数をインポートして利用

---

## 補足

- 本 README はコードベースの主要な使い方と構成をまとめたものです。実運用時は必ず
  - .env を適切に設定し（機密情報は秘匿）
  - python -m kabusys.validate_config でチェックし
  - ログや DB の保存先・権限を確認した上で起動してください
- OpenAI API を使用する機能は課金やレート制限の対象です。API キーの管理に注意してください。

---

必要であれば、README に以下を追加で盛り込みます：
- requirements.txt の想定依存（候補パッケージ一覧）
- systemd / Supervisor 用の起動ユニット例
- 具体的な設定例（.env.example のサンプル）
- 個々のモジュール（ExecutionEngine / TradeMonitor 等）の API ドキュメント

どれを追加したいか教えてください。