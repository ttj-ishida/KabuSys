# KabuSys

KabuSys は日本株向けの自動売買システムのコードベースです。  
バックテスト / リサーチ用のファクター計算、ポートフォリオ構築、発注（Execution）、監視（Monitoring）、AI を使ったニュースセンチメント評価などのコンポーネントを収めたモジュール群で構成されています。

主な設計方針：
- 本番・Paper Trading を環境変数で切り替え（KABUSYS_ENV）
- DuckDB / SQLite をデータ層に使用（ローカルファイル）
- 外部 API（kabu API, J-Quants, OpenAI）との連携レイヤを分離
- 監視・アラート機構（LINE Push）・KillSwitch による安全停止機構を備える

---

## 機能一覧

- Execution（発注・リスク管理・リコンシリエーション）
  - Broker クライアント抽象化（実口座 / モック切替）
  - OrderManager / OrderRepository（DB保持）によるクラッシュ耐性
  - RiskManager によるポジション上限・投下資金制御
  - Reconciler による再起動時の状態同期

- Monitoring（システム監視）
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じてフラグファイル（data/kill.flag）を作成して Execution を停止
  - AlertManager：LINE Push によるアラート（クールダウン管理）
  - Streamlit ダッシュボードで監視状態を可視化

- Portfolio（銘柄選定・重み付け・株数決定）
  - 候補選定 (score/equal)
  - セクターキャップ、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）

- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント集約→ai_scores へ書込
  - マクロニュース + ETF MA200 乖離から市場レジーム（bull/neutral/bear）判定

- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・成功率・レイテンシ等の検証レポートを生成

---

## セットアップ手順（ローカル）

1. リポジトリルートへ移動し、仮想環境を作成・有効化
   - 例（venv）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt を用意している想定です:
     - pip install -r requirements.txt

3. 環境変数 / .env の準備
   - ルートに .env または .env.local を作成（.env.example を参照）
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO
     - PAPER_FILL_MODE=instant  (paper_trading 時の成行/部分約定挙動)
   - 自動 .env 読み込みはデフォルトで有効。無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリ作成
   - mkdir -p data

5. （任意）DuckDB / SQLite の初期データ投入は各モジュールのユーティリティまたは ETL スクリプトで行います。
   - 監視用 DB（monitoring.db）は起動時にテーブルが作られます（init_monitoring_db は冪等）。

注意:
- 起動時にプロセス優先度を "high" に変更しようとします。権限がない場合は警告としてスキップされます。
- OpenAI / 実ブローカ利用には各種 API キー・認証情報が必須です。

---

## 使い方（代表的なコマンド）

- ExecutionEngine を起動（本番/テストは KABUSYS_ENV による切替）
  - python -m kabusys.run_execution
  - Paper Trading（環境変数で切替）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper Trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH にデータを記録します。

- Monitoring ポーリングループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30  # 秒（1以上の整数）
  - 監視は本番 sqlite_path（KABUSYS_ENV に依らず）を使用します。

- Streamlit ダッシュボードで監視情報を見る
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 関連（プログラムから呼び出す）
  - ニュースセンチメント集計:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- 設定値の参照
  - from kabusys.config import settings
  - settings.env, settings.sqlite_path, settings.is_paper などを利用可能

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 開発/ペーパートレード/本番
  - 有効値: development, paper_trading, live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数/設定読み込みロジック
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor 起動スクリプト

src/kabusys/execution/
- order_manager.py
- order_repository.py
- execution_engine.py
- reconciler.py
- risk_manager.py
- broker_factory.py
- broker_api.py
- order_record.py
- ...（発注・ブローカー関連）

src/kabusys/monitoring/
- monitoring_db.py                 — SQLite テーブル定義 / ラッパー
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- monitoring_engine.py
- kill_switch.py
- alert_manager.py
- streamlit_dashboard.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py                      — ニュースセンチメントスコアリング
- regime_detector.py               — 市場レジーム判定
- __init__.py

src/kabusys/tools/
- paper_verification_report.py
- __init__.py

src/kabusys/utils/
- process_priority.py              — プロセス優先度・CPU affinity ユーティリティ

その他:
- data/                            — デフォルトの DB / PID / フラグ用ディレクトリ（手動で作成）
- pyproject.toml / .git / .env.example（想定）

---

## 注意事項 / 運用メモ

- Paper Trading と本番 DB は分離されています（settings.is_paper により paper_sqlite_path を使用）。
- Monitoring は KABUSYS_ENV に関係なくデフォルトの sqlite_path（本番想定）を使用します（監視は本番を監視する設計）。
- process priority の設定や CPU affinity の変更は OS に依存し、権限の都合でスキップされることがあります（警告ログが出ます）。
- OpenAI 等の外部 API はレート制限や一時エラーに対してリトライ（指数バックオフ）を実装していますが、APIキーの管理に留意してください。
- .env 自動ロード: プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env / .env.local を読み込みます。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション的な簡易処理（監視 DB にカラム追加など）が起動時に行われるため、既存 DB との互換性に留意してください。

---

必要であれば、README にサンプル .env.example、具体的な CLI オプション一覧、または依存パッケージの厳密なバージョンリスト（requirements.txt）を追加します。どの情報を優先して追記しますか？