# KabuSys

日本株自動売買システムのサブセット実装。ポートフォリオ構築、ポジションサイズ計算、監視・キルスイッチ、ペーパートレードの検証ツール、LLM を使ったニュースセンチメント / レジーム判定等のユーティリティ群を含みます。

## プロジェクト概要
KabuSys は以下の目的を想定したモジュール群です。

- 株式売買戦略のポートフォリオ構築とポジションサイズ算出（純粋関数群、DB依存なし）
- ExecutionEngine（発注ロジック）向けの監視・リスク管理（SQLite ベースの監視 DB）
- Paper Trading（ペーパートレード）用の分離された DB と検証レポート生成
- DuckDB を用いたリサーチ／ファクター計算
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（銘柄別センチメント）および市場レジーム判定
- 起動用スクリプト（実行エンジン / 監視ループ）と設定ウィザード・検証 CLI

設計上の特徴：
- 環境変数（.env）による設定管理（config_setup でウィザード生成）
- Paper Trading と Live（本番）DB の分離
- 冪等な DB 初期化 / マイグレーション処理
- LLM 呼び出しはフェイルセーフかつリトライ実装（部分失敗時の局所書き換え）

## 主な機能一覧
- 設定関連
  - config_setup: 対話式に .env を作成/更新
  - validate_config: 起動前の環境・設定検証（--strict オプションあり）
- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて Paper/Live 切替）
  - run_monitoring: SystemMonitor をポーリングで実行
- 監視 / リスク
  - monitoring_engine: 複数モニタの統合ポーリング、アラート送出連携
  - system_monitor, trade_monitor, risk_monitor: CPU/メモリ/ディスク/データ鮮度・滞留注文・ドローダウン等の監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、Execution を停止
- ポートフォリオ構築
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier
  - position_sizing.calc_position_sizes（単元株丸め、資金スケール）
- リサーチ
  - research.calc_momentum / calc_volatility / calc_value（DuckDB 経由で prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン、IC 計算、統計サマリ
- AI / LLM 関連
  - ai.news_nlp.score_news: ニュースを銘柄別に集約して LLM でセンチメント採点し ai_scores に書き込み
  - ai.regime_detector.score_regime: ETF の MA とマクロニュースから日次レジーム判定・保存
- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率・成功率・レイテンシ等）

## セットアップ手順（ローカル開発向け）
以下は推奨フローの例です。プロジェクトに requirements.txt があればそれを使ってください。

1. リポジトリをクローン
   - git clone <リポジトリ URL>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な依存パッケージ（例）:
     - pip install duckdb psutil openai
     - PyYAML は validate_config の YAML 検証に任意で使用: pip install pyyaml
4. .env の作成
   - 対話式ウィザードを起動:
     - python -m kabusys.config_setup
   - あるいは .env ファイルをプロジェクトルートに手動作成（.env.example を参照）
5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って .env / config/*.yaml を修正
6. データディレクトリの作成（必要に応じて）
   - data/ および logs/ ディレクトリは自動作成されることが多いですが、パーミッション等に注意してください。

注意点:
- OpenAI を使う機能（ai.news_nlp, ai.regime_detector）は OPENAI_API_KEY の設定が必要です。
- 実運用（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します。

## 使い方（主要なコマンド）
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
- ExecutionEngine 起動（実装済みの Engine を起動）:
  - python -m kabusys.run_execution
  - Paper Trading を使用する場合は KABUSYS_ENV=paper_trading を .env に設定（または環境変数で一時的に指定）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （秒単位、1以上）
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- リサーチ / AI 用の関数はライブラリ API として import して利用します（例: research.calc_momentum 等）。

停止フラグ（手動制御）:
- 実行中のエンジンを停止するにはプロジェクトルートの data/kill.flag に理由テキストを書き込みます（KillSwitch が検出して Execution を停止）。
- run_monitoring/run_execution は data/stop_requested.flag の存在でループを終了します（シャットダウン用のフラグ）。

ログ:
- デフォルトでは logs/ ディレクトリにアプリケーションごとの日次ローテーションログが出力されます（kabusys.utils.logging_setup.setup_logging）。

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールに必須）
- PAPER_FILL_MODE: paper_trading 時の挙動（instant | partial | never | reject）（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

## ディレクトリ構成（主要ファイル）
プロジェクトルートの src/kabusys 配下:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (参照実装が無い場合は別途)
  - execution/                 — ExecutionEngine 周辺（BrokerFactory, OrderManager 等）
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                      — 実行時生成されるディレクトリ（DB / フラグ / pid 等）
  - logs/                      — ログ出力先（デフォルト）

（実際のファイル数やサブパッケージはコードベースに依存します。上記はコードスニペットから抽出した主要ファイルです。）

## 備考 / 運用上の注意
- 監視（monitoring）は sqlite_path を常に本番用の sqlite_path を使う設計（環境に依らず監視 DB を参照する点に注意）。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用してペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録するよう分離されています。
- LLM 呼び出し（OpenAI）はネットワークエラーやレート制限に対して再試行（指数バックオフ）を行い、失敗時は安全側のデフォルト（スコア 0 等）で継続するよう設計されています。
- データ鮮度や重要なアラートは AlertManager を経由して通知する想定です（LINE 等の外部通知は設定に依存）。

---

問題の特定や README の補足（例: 追加の実行例、requirements.txt の推奨内容、CI 設定）を希望される場合は、その内容を教えてください。必要に応じて README に追記します。