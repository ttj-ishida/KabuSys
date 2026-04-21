# KabuSys — 日本株自動売買システム

軽量な日本株向け自動売買フレームワークです。戦略（シグナル）→ポートフォリオ構築→発注（Execution）までの実行系に加え、監視・リスク管理、研究用のファクター計算、LLM を用いたニュースセンチメント/レジーム判定などの補助機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を想定したモジュール群で構成されています。

- 発注エンジン（ExecutionEngine）:
  - 本番（live）とペーパートレード（paper_trading）切替対応
  - ブローカークライアントは環境に応じて実装を切替（MockBrokerClient 等）
  - 注文管理・リスク管理・再整合（reconciler）を含む

- 監視（Monitoring）:
  - システム状態（CPU/メモリ/ディスク/プロセス）とデータ鮮度を監視
  - 取引ログ・リスクログ・ダッシュボードを SQLite へ永続化
  - Kill Switch（条件成立時に data/kill.flag を作成して Execution を停止）

- ポートフォリオ構築（Portfolio）:
  - 候補選定、重み計算（等配分・スコア加重・リスクベース）
  - セクター制約やレジームに応じた乗数調整
  - 株数計算（ロット丸め・利用可能現金に基づくスケールダウン）

- リサーチ（Research）:
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC 計算、統計サマリー等

- AI（OpenAI）補助:
  - ニュース記事のセンチメント付与（ニュース → ai_scores 書込）
  - マクロニュース＋ETF MA に基づく市場レジーム判定（market_regime 書込）

- ユーティリティ:
  - .env 対話ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（依存注入可能な BrokerClientFactory）
  - OrderManager / OrderRepository / RiskManager / Reconciler

- Monitoring
  - SystemMonitor（プロセス生存・データ鮮度・リソース監視）
  - TradeMonitor（trade_logs を解析して滞留注文・異常約定検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（各 Monitor の統合ポーリング）
  - KillSwitch（条件で data/kill.flag を書き込み）

- Portfolio
  - 候補選定、等配分・スコア配分、ポジションサイズ計算
  - セクター上限の適用、レジーム乗数

- Research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank

- AI
  - score_news（OpenAI を用いたニュースセンチメント）
  - score_regime（ETF MA + マクロニュースでレジーム判定）

- Tools / CLI
  - python -m kabusys.config_setup（.env ウィザード）
  - python -m kabusys.validate_config（設定検証）
  - python -m kabusys.tools.paper_verification_report（ペーパートレード検証）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化:
     - Unix/macOS:
       - python -m venv .venv
       - source .venv/bin/activate
     - Windows (PowerShell):
       - python -m venv .venv
       - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb, psutil, openai, PyYAML（オプション: config 検証用）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成された .env をプロジェクトルートに配置（.env を Git に入れないこと）
   - 自動ロード: 起動時に .env / .env.local が自動読み込みされます（OS 環境変数が優先）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いして exit(1)

5. データディレクトリ
   - ログ: デフォルト logs/
   - DB・フラグ等: data/
   - 必要に応じてデータディレクトリを作成（多くは起動時に自動作成されます）

---

## 主要な環境変数（抜粋）

必須（実行前に設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な任意/設定
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH を使用
  - live: 本番発注が行われるため注意
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知、任意）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1/0）

（完全な一覧は kabusys.config.Settings / validate_config.py を参照してください）

---

## 使い方（起動例）

- 環境変数読み込み・確認
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV によって paper_trading / live を切替
    - paper_trading の場合は PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag があれば起動を中止
    - PID ファイル: data/execution.pid（設定で変更可）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト: 60）
    - 監視は常に（環境にかかわらず）Settings.sqlite_path を使用
    - 停止は data/stop_requested.flag により検知

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可）

- AI モジュール（プログラムから使用）
  - 例: ニューススコア付与
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_API_KEY")
  - 例: レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_API_KEY")

注意: OpenAI を使う場合は OPENAI_API_KEY を環境変数で設定するか、関数に api_key を渡してください。

---

## 停止・Kill 機構

- stop_requested.flag
  - run_* スクリプトは data/stop_requested.flag の存在を検知してループを終了します（優雅に停止）。

- kill.flag（Kill Switch）
  - KillSwitch が条件を検出すると data/kill.flag を書き込み、ExecutionEngine 停止要求を送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 を推奨）。

---

## ログ設定

- ロガーは共通ユーティリティ kabusys.utils.logging_setup.setup_logging により設定されます。
- デフォルト: console (stdout) と logs/<app_name>.log（日次ローテーション、30日保持）
- ログレベルは LOG_LEVEL 環境変数または引数で調整可能

---

## ディレクトリ構成（主要ファイル）

ルート: (この README と同階層に src/ がある想定)

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
    (※発注関連の主要コンポーネント)

  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義 / 永続化操作
    - system_monitor.py       — システム監視（プロセス/リソース/データ鮮度）
    - trade_monitor.py        — 注文ログ解析
    - risk_monitor.py         — ドローダウン・ポジション監視
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — レジーム判定（ETF MA + マクロニュース）

  - data/                    — データファイル配置（例: data/*.db, data/kill.flag）
  - logs/                    — ログ出力先（デフォルト）

  - tools/
    - paper_verification_report.py

---

## 追加の注意点 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では、必須環境変数や通知設定（LINE）を確実に設定・検証してください。
- .env を誤ってコミットしないでください（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の機密情報を含む）。
- Paper Trading は実運用データと分離されるよう PAPER_TRADING_SQLITE_PATH を使用します。テスト用 DB を使うことで安全に検証できます。
- OpenAI API 呼び出しはレート制限や一時エラーを考慮してリトライ設計が入っていますが、API キーの漏洩・課金には注意してください。
- モジュールは依存注入を想定している箇所が多く、テストや差し替えが容易です（API 呼び出しは内部関数をモック可能）。

---

もし README に「セットアップ用の requirements.txt」、「デプロイ手順（systemd / Docker）」や「よくあるトラブルシューティング（ログの読み方、DB マイグレーションなど）」を追記したければ、使用環境（ローカル / Docker / サーバ）や必要な追加情報を教えてください。必要に応じてサンプル .env.example も作成できます。