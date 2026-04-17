# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、LLM を用いたニュースNLP などの機能を含みます。本リポジトリはライブラリと複数の実行スクリプトを提供します。

---

## プロジェクト概要

主な目的は、実運用（live）および Paper Trading（paper_trading）環境で安全に自動売買を行うためのコンポーネントを提供することです。設計方針としては以下を重視しています。

- 環境分離（Paper Trading は専用 DB、実取引とは完全分離）
- フェイルセーフ（監視・キルスイッチ・リトライ等）
- DuckDB / SQLite を用いたデータ処理と永続化
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントやレジーム判定（API キー必須）
- テスト可能で純粋関数化されたポートフォリオ構築ロジック

---

## 主な機能一覧

- execution（発注）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler：発注、状態管理、再起動時の復旧
  - BrokerFactory により環境に応じて実ブローカー or MockBroker を選択（paper_trading）
- monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、実行プロセスの監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウン／ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件により ExecutionEngine を停止するフラグを書き込み
  - AlertManager：LINE によるプッシュ通知（任意）
  - Streamlit ダッシュボード（読み取り専用）
- portfolio（ポートフォリオ構築）
  - 候補選定、等配分・スコア加重配分、セクター制限、ポジションサイズ計算（単元株丸め、リスク制限）
- research（リサーチ）
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- ai（LLM を利用する補助機能）
  - news_nlp.score_news：ニュース記事をまとめて OpenAI に送信し ai_scores に書き込み
  - regime_detector.score_regime：ETF とマクロニュースを合成して市場レジーム判定
- tools
  - paper_verification_report：Paper Trading DB を解析して検証レポートを生成

---

## セットアップ手順

前提
- Python 3.10+（typing の表記や動作確認を想定）
- git（プロジェクトルートを自動検出に使用）

1. リポジトリをクローン / 取得
   - 例: git clone <repo_url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトで requirements.txt を用意している場合は `pip install -r requirements.txt`）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先されます）。
   - 主要な環境変数（例）
     - KABUSYS_ENV = development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN = <トークン>
     - KABU_API_PASSWORD = <kabu API パスワード>
     - OPENAI_API_KEY = <OpenAI API Key>  （ai.news_nlp / regime_detector を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID = （アラート送信用）
     - SQLITE_PATH = data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
     - DUCKDB_PATH = data/kabusys.duckdb
     - MONITOR_POLL_INTERVAL = 60  （監視ポーリング間隔秒。0以下は無視されデフォルト60秒）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 初期 DB は各起動スクリプトが必要に応じて初期化します（monitoring テーブル等は init_monitoring_db による冪等処理）。

---

## 使い方（よく使うコマンド）

※ 以下はプロジェクトルートで実行することを前提としています。

- 監視プロセスを起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - または: python src/kabusys/run_monitoring.py
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数で間隔（秒）を変更可能（デフォルト 60）
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に関わらず）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - または: python src/kabusys/run_execution.py
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/execution.pid、または data/stop_requested.flag（停止フラグ）により制御されます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

- Streamlit 監視ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - UI から最新ダッシュボード、ポジション、トレードログ、リスクログ等を参照できます（読み取り専用で安全）

- AI 関連（ニューススコア・レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime はライブラリ API として利用可能です。例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - 実行には OPENAI_API_KEY が必須です。

- 停止 / キル
  - KillSwitch がトリガーした場合、data/kill.flag が書き込まれます。ExecutionEngine は起動中にこのフラグを検出して停止します。
  - 手動で停止したい場合は data/stop_requested.flag を作成すると run_monitoring/run_execution が終了します。

---

## 設定と環境（Settings）

- 設定は環境変数経由で行います。Settings クラス（kabusys.config）でアクセスできます。
- .env と .env.local の自動読み込み:
  - OS 環境変数 > .env.local > .env の優先順位
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効
- 重要な設定例:
  - KABUSYS_ENV: development / paper_trading / live（動作モード）
  - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
  - PID_FILE_PATH, KILL_FLAG_PATH などファイルパス系
  - CPU / MEMORY / DISK 閾値（監視）

---

## ディレクトリ構成

主要なファイルとモジュールを抜粋して示します。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み）
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - data/                          — 実行時に使用する DB/フラグ類（プロジェクトルート直下）
  - ai/
    - news_nlp.py                  — ニュースセンチメント取得（OpenAI）
    - regime_detector.py           — 市場レジーム判定（ETF + マクロニュース）
  - monitoring/
    - monitoring_db.py             — SQLite スキーマ & 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - order_record.py etc.
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

（上記はコードベースの主要モジュールを抜粋したものです。詳細はソースツリーを参照してください。）

---

## 運用上の注意

- Paper Trading と Live の DB は分離してください（PAPER_TRADING_SQLITE_PATH を適切に設定）。
- OpenAI 使用箇所（news_nlp / regime_detector）は API キーと呼び出し制限、コストに注意して運用してください。失敗時のフェイルセーフが組み込まれていますが、運用ポリシーを定めてください。
- process_priority.set_process_priority() を起動時に呼び出しますが、権限不足等で設定に失敗する場合があります（warning が出力され続けることはありません）。
- monitoring は本番 sqlite_path を使う設計です（run_monitoring は KABUSYS_ENV に依存せず本番 DB を参照します）。
- kill.flag / stop_requested.flag / execution.pid などフラグファイルの取り扱いに注意してください。自動化スクリプトや運用手順に沿ってクリーンに扱ってください。

---

## 参考情報・トラブルシューティング

- .env のパースは shell ライクな書式をサポートしますが、複雑な値はクォートして記述してください。
- DuckDB への書き込みや executemany の空リストバインドについては互換性制約があるので、tools や ai モジュールでそれらへの対処が実装されています。
- Streamlit ダッシュボードは DB を読み取り専用モードで開くので、通常は安全に参照できます。DB が存在しない場合はエラーメッセージが表示されます。

---

必要があれば、README に以下を追加します：
- 具体的な .env.example のテンプレート
- 各モジュール（ExecutionEngine, Reconciler, Execution Broker API）に関する詳細な設計ドキュメントリンク
- Docker / systemd ユニット例（プロダクション運用向け）

ご希望があれば追加で用意します。