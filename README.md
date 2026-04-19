# KabuSys

日本株向け自動売買システムのコアライブラリ群。システム監視、発注エンジン（ExecutionEngine）、ポートフォリオ構築、ファクター研究、AI を使ったニューススコアリングなどの機能を含みます。

## プロジェクト概要
KabuSys は以下のような責務を持ちます。
- 株価データ（DuckDB）を用いたファクター計算・研究機能
- シグナル → ポートフォリオ構成 → 注文サイズ決定までの純粋関数群
- 発注エンジン（ExecutionEngine）と発注ログの永続化（SQLite / DuckDB）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- OpenAI（LLM）を利用したニュースセンチメント評価と市場レジーム判定
- 開発用 CLI（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

## 主な機能一覧
- 環境設定ウィザード（.env の対話式作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: python -m kabusys.validate_config
- 実際の ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB に分離
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ:
  - 候補選定: select_candidates
  - 重み計算: calc_equal_weights / calc_score_weights
  - ポジションサイズ計算: calc_position_sizes（リスクベース / 等配分 等）
  - セクター上限 / レジーム乗数調整: apply_sector_cap / calc_regime_multiplier
- 研究用ファクター計算（DuckDB 経由）:
  - モメンタム / ボラティリティ / バリュー 等: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC・統計サマリ: calc_forward_returns, calc_ic, factor_summary
- AI 系:
  - ニュースセンチメント評価（OpenAI）: kabusys.ai.score_news
  - 市場レジーム判定（MA200 + マクロニュースの LLM 評価）: kabusys.ai.regime_detector

## セットアップ手順（簡易）
1. Python
   - 推奨: Python 3.10 以上（PEP 604 の `X | Y` 型注釈等を使用）
2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate
3. 依存パッケージをインストール
   - DuckDB, psutil, openai, （オプションで PyYAML）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # config.yaml の検証を行う場合
   - （プロジェクトに requirements.txt があればそれを使用）
4. .env の準備
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 生成された .env を必ず Git にコミットしないこと
5. 設定検証
   - python -m kabusys.validate_config
   - 本番チェックを厳密に行う場合: python -m kabusys.validate_config --strict

## 環境変数（主要なもの）
主に .env に設定するキー（抜粋）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading: 実発注は行わずペーパートレード DB を使用
  - live: 本番。注意して使用すること
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング秒数（run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START — 起動時に data/kill.flag を自動クリアするか（1=有効、デフォルト 0）

.env の自動読み込みはプロジェクトルートの .env/.env.local から行われます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

## 使い方（例）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
  - 停止するにはプロセスに stop フラグを投げるか、kill.flag を使う運用設計に従う
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード DB（data/paper_trading.db）に記録
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト: 60）
  - 監視プロセスは data/stop_requested.flag の存在でループを停止します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- AI 機能（スクリプト / プログラムから利用）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...") など

### Kill Switch / 停止制御
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを与えます（冪等）。
- run_monitoring/run_execution は data/stop_requested.flag を見て終了する挙動を持ちます。
- PID ファイル: data/execution.pid（ExecutionEngine が使用）

### ロギング
- ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging を使用。
- ログレベルは LOG_LEVEL または setup_logging の引数で調節。

## ディレクトリ構成（主要ファイル）
（抜粋・例）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / Settings 管理（.env 自動読み込み）
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 起動前の設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP（OpenAI で銘柄別スコア）
      - regime_detector.py            — 市場レジーム判定（MA200 + マクロニュース）
    - research/
      - __init__.py
      - factor_research.py            — モメンタム・ボラティリティ・バリュー計算
      - feature_exploration.py        — 将来リターン・IC・統計サマリ
    - portfolio/
      - __init__.py
      - portfolio_builder.py          — 候補選定・重み計算
      - position_sizing.py            — 発注株数計算（丸め・集計上限等）
      - risk_adjustment.py            — セクター上限・レジーム乗数
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層（schema 初期化と CRUD）
      - system_monitor.py             — CPU/メモリ/データ鮮度 等の監視
      - trade_monitor.py              — （発注関係の監視）※詳細実装参照
      - risk_monitor.py               — ドローダウン・ポジション上限監視
      - kill_switch.py                — kill.flag 書込みロジック
      - monitoring_engine.py          — 各 Monitor を束ねるエンジン
      - alert_manager.py              — （LINE など通知の抽象）※実装参照
    - execution/                       — ExecutionEngine / ブローカ関連（発注ロジック）
      - ...                           — （実装ファイル群）
    - utils/
      - logging_setup.py              — 統一的ログ設定
      - process_priority.py           — プロセス優先度 / CPU affinity
      - __init__.py
    - data/                            — デフォルトの DB / flag / pid が置かれる（実行時に作成）
- config/
  - system_config.yaml                — 各種設定（テンプレート / 生成スクリプト参照）
  - ...（その他の yaml）

（注意）
- この README はコードベースに含まれる主要モジュールから要点をまとめたものです。実運用時には config/*.yaml や .env の項目を十分に確認してください。
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start 等の設定に注意し、LINE 通知設定を必ず確認してください（validate_config の live ガードが警告を出します）。

## よく使うコマンドまとめ
- .env ウィザード: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config [--strict]
- 実行エンジン開始: python -m kabusys.run_execution
- 監視開始: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

必要であれば、README に含めるサンプル .env のテンプレートや運用フロー（起動手順・停止手順・DB バックアップ方針・ログローテーション要件）などを追記できます。どの項目を詳しく書きたいか教えてください。