# KabuSys

日本株自動売買システムのコアライブラリ群（軽量な実装）。  
このリポジトリは、戦略の研究/ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）および関連ユーティリティを含みます。

> 本 README は提供されたコードベースに基づく要約ドキュメントです。実運用時は .env / config/*.yaml を適切に設定し、validate_config で検証してください。

## 概要
- DuckDB / SQLite を用いたデータ処理・永続化
- 研究向けファクター計算（momentum / volatility / value 等）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- Paper Trading と Live の切り替え（Paper Trading は専用 DB へ記録）
- OpenAI を利用したニュース NLP（銘柄別センチメント）および市場レジーム判定
- 監視コンポーネント（システム状態・注文ログ・リスク監視）と Kill Switch
- 起動用スクリプト・設定ウィザード・検証ツールを提供

## 主な機能一覧
- 環境設定管理（kabusys.config）
  - .env 自動読み込み機能 / 必須値チェック
- 設定ウィザード（kabusys.config_setup）
  - 対話形式で .env を生成
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数・YAML ファイル・パス等の事前チェック
- Execution 起動スクリプト（kabusys.run_execution）
  - 本番 / ペーパートレード（MockBroker）切替
  - 停止フラグ (data/stop_requested.flag, data/execution.pid) による制御
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定可）
- 監視サブシステム（kabusys.monitoring）
  - MonitoringDB（SQLite スキーマ初期化 / 永続化 API）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch（条件を満たすと data/kill.flag を作成）
  - AlertManager（通知管理のフック場所）
- 研究モジュール（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計測・統計サマリ
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重 / スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- AI モジュール（kabusys.ai）
  - news_nlp: ニュースを OpenAI に投げて銘柄別スコアを ai_scores テーブルへ書込
  - regime_detector: MA・マクロセンチメントを合成して market_regime 更新
- 工具スクリプト
  - paper_verification_report: Paper Trading DB を解析して Pass/Fail レポートを出力

## 必要要件（主な Python パッケージ）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証を行う場合）
- （標準ライブラリの sqlite3, logging 等）

インストール例:
```bash
pip install duckdb psutil openai pyyaml
```
（プロジェクトに requirements.txt があればそちらを利用してください）

## セットアップ手順（基本）
1. リポジトリをクローン / ソース配置
2. 依存パッケージをインストール
3. 設定ファイル（.env）作成
   - 対話式ウィザードを推奨:
     ```bash
     python -m kabusys.config_setup
     ```
   - 重要な環境変数の例（.env に記載）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL
     - OPENAI_API_KEY（AI 機能を使う場合）
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じて data/ ディレクトリや logs/ を作成（logging_setup が自動作成を試みますが権限によって失敗することがあります）。

## 使い方（起動例）
- 監視プロセス起動（デフォルト 60 秒間隔、環境変数で変更可）:
  ```bash
  # 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を指定
  python -m kabusys.run_monitoring
  ```
  - 監視は data/stop_requested.flag の存在でループを終了します。
  - MONITOR_POLL_INTERVAL（秒）: ポーリング間隔（デフォルト 60）
- Execution エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動前に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中に同ファイルが作られるとエンジンを停止します。
- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
- AI スコアリング / レジーム判定（ライブラリ関数として使用）:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、テーブル（raw_news, news_symbols, ai_scores, prices_daily 等）を参照・更新します。

## 重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で使用）
- MONITOR_POLL_INTERVAL — run_monitoring ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1 有効、デフォルト 0）

## 停止・Kill スイッチについて
- 実行系の停止は複数手段:
  - data/stop_requested.flag: run_monitoring / run_execution の外部停止に使われるフラグ
  - data/kill.flag: KillSwitch（監視がトリガーするとここに理由を記載して作成）。ExecutionEngine 起動時にこのフラグがあると起動を抑止する設計
- KillSwitch の評価は RiskMonitor 等の結果に基づく（ドローダウン超過・ポジション上限超過など）

## ロギング
- kabusys.utils.logging_setup.setup_logging により統一的にログを設定
  - コンソール (stdout) 出力
  - 日次ローテーションファイル出力（デフォルト logs/<app_name>.log、30日分保持）
  - LOG_DIR 環境変数または引数でログディレクトリ指定可

## ディレクトリ構成（主要ファイル）
（root: src/kabusys 以下を示す。実際のリポジトリルートに pyproject.toml/.git を置く想定）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ + 永続化 API
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （注文監視）※実装ファイルはプロジェクトに依存
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — フラグファイルによる停止制御
    - alert_manager.py        — アラート送信管理（実装により通知先へ送信）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
    - __init__.py
  - tools/
    - paper_verification_report.py — Paper Trading レポート出力
  - data/                     — デフォルトで使用される DB / flag の格納先（実行前に作成されることが多い）
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag / stop_requested.flag / execution.pid

（注）実際のファイル一覧はリポジトリの内容に依存します。上は本ドキュメント作成時に与えられたコード群から抽出した主要ファイルです。

## 開発時の注意点 / ベストプラクティス
- .env は絶対にリポジトリにコミットしないでください（config_setup もヘッダで警告している通り）。
- 本番環境（KABUSYS_ENV=live）では特に LINE 通知等の設定漏れ・ Kill Switch クリア設定に注意してください（validate_config が警告を出します）。
- AI（OpenAI）を使う処理は API 失敗時にフォールバックを行う設計ですが、テスト環境ではモック化して実行することを推奨します。
- ペーパートレードは本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。誤って本番 DB を上書きしないように注意してください。
- DuckDB / SQLite への接続はファイルパスを設定し、必要に応じてバックアップや権限設定を行ってください。

## 典型的なワークフロー
1. pip install で依存導入
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config でチェック
4. python -m kabusys.run_monitoring を起動（監視を常時稼働）
5. python -m kabusys.run_execution を起動（発注系）
6. Paper Trading の検証は tools.paper_verification_report で実行

---

追加で README に掲載したい内容（例: サンプル .env、SQL スキーマの詳細、使用する外部サービスの注意事項、API レート制限の扱い等）があれば教えてください。必要に応じてサンプル .env やコマンド例を補完します。