# KabuSys

KabuSys は日本株向けの自動売買基盤の一部を実装した Python パッケージです。本リポジトリには監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）、および各種ユーティリティと CLI/ツール類が含まれます。

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動コマンド / ツール）
- 環境変数一覧（主要）
- ディレクトリ構成（主要ファイルと説明）

---

プロジェクト概要
- KabuSys は自動売買システムのコアコンポーネント群を含むライブラリ兼ランタイム群です。
- 監視（System / Trade / Risk）、Execution エンジン、注文リコンシリエーション、ポートフォリオ構築、ファクター計算（リサーチ）、ニュースに対する LLM ベースのセンチメント解析などを備えています。
- SQLite（監視ログ等）と DuckDB（時系列・ファクターデータ集計）をデータ基盤として利用します。
- 実運用（live）とペーパートレーディング（paper_trading）を環境切替で分離できます。

主な機能一覧
- 監視（monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度を監視して SQLite に記録
  - TradeMonitor: 滞留注文（stale orders）や約定異常価格を検出してリスクログへ記録
  - RiskMonitor: ドローダウンやポジション上限を監視し、必要なら kill.flag を書き込み ExecutionEngine 停止をトリガ
  - AlertManager: LINE Push API 経由でアラート通知（オプション）
  - MonitoringEngine: 上記を束ねるポーリングエンジン
  - Streamlit ダッシュボード: 監視 DB を可視化する UI
- 実行（execution）
  - ExecutionEngine（起動スクリプトから起動）
  - OrderManager / OrderRepository / Reconciler: 注文生成・送信・永続化・起動時リコンシリエーション
  - BrokerClientFactory: 環境に応じて実ブローカー or MockBroker を生成（KABUSYS_ENV に依存）
- ポートフォリオ（portfolio）
  - 候補選定、等重配分・スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算（単元丸め・cash cap）
- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索（将来リターン、IC 計算、統計サマリ）
- AI（ai）
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計 → ai_scores 書き込み
  - regime_detector: ETF MA とマクロニュースの LLM 評価を合成して market_regime を算出
- ツール
  - paper_verification_report: ペーパートレード結果を集計して検証レポートを標準出力に出す
  - streamlit_dashboard: 監視 DB の可視化（Streamlit）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（推奨: 3.10+）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb, psutil, requests, streamlit, openai
   - 例:
     - pip install duckdb psutil requests streamlit openai
   - （必要に応じて追加パッケージをインストールしてください）
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数の用意
   - プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須となる可能性のある環境変数（詳細は次節参照）を設定してください。
6. DB 初期化
   - Monitoring は起動時に init_monitoring_db を実行して必要テーブルを作成します。monitoring を起動すれば SQLite の初期化が行われます。

使い方（実行コマンド例）
- 監視ループ（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60 秒）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が変わります:
    - paper_trading: MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db) に記録。本番 DB と完全分離。
    - live / development: 本番用設定
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD （開始日）
    - --to YYYY-MM-DD   （終了日）
    - --db PATH         （DB パス、環境変数 PAPER_TRADING_SQLITE_PATH より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で読み取り専用モードの DB パスを指定可能
- AI / レジーム系（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None) などを呼び出してニュース NLP を実行
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用（未設定の場合エラー）

主要な環境変数（概要）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 利用時に必須
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 利用時必須）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の fill 動作（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill switch のフラグファイルパス（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

注意点 / 実行時の挙動
- run_monitoring は Settings を読み込み、環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- Execution 側の PID ファイルや kill.flag を使ってプロセス間安全停止や監視連携を行います（KillSwitch が条件を満たすと kill.flag を作成）。
- .env の自動読み込み機能はプロジェクトルート（.git か pyproject.toml の存在）を基準に行われ、OS 環境変数は保護されます。
- Process priority や CPU affinity の設定をするユーティリティがあり、起動スクリプトは起動直後にプロセス優先度を "high" に設定しようとします（失敗した場合は警告で続行）。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env ロード / Settings クラス
  - run_monitoring.py — SystemMonitor のポーリングループ実行用エントリ
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite の初期化 / MonitoringDB（永続化 API）
    - system_monitor.py — システム状態 / データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常の検出
    - risk_monitor.py — ドローダウン / ポジション上限の監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE Push による通知
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit による監視ダッシュボード
  - execution/
    - order_manager.py — 注文状態遷移 / send ロジックの外向き API
    - reconciler.py — 起動時の注文・ポジション照合（自動復旧）
    - （その他：broker_factory, execution_engine, order_repository などはコードベースに依存）
  - portfolio/
    - portfolio_builder.py — 候補選抜、等重/スコア重み付け
    - position_sizing.py — 発注株数計算（丸め・リスク制限・aggregate cap）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB 経由）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント集計（ai_scores 書込）
    - regime_detector.py — ETF MA と LLM マクロセンチメントを合成して市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード結果の検証レポート出力ツール

テストやローカル検証のヒント
- ペーパートレードモード（KABUSYS_ENV=paper_trading）で動かすと、本番 DB を汚さずに動作確認できます。
- Streamlit ダッシュボードは読み取り専用で DB の存在を検出し、監視プロセスが書き込んでいるデータを可視化します。
- news_nlp / regime_detector を試す場合は OPENAI_API_KEY の設定が必要です。API を直接叩くため、API 利用料に注意してください。
- MonitoringDB の init_monitoring_db を実行すれば必要テーブルが作成され、マイグレーション（カラム追加）も冪等に処理されます。

ライセンス・貢献
- 本 README には明示的なライセンスは含まれていません。実プロジェクトへの導入時はリポジトリルートの LICENSE を確認してください。
- コントリビューションは、Issue / Pull Request を通じて行ってください。大きな変更は設計意図（ドキュメント）を合わせて提出してください。

---

上記はリポジトリ内のモジュールとスクリプトに基づく概要と利用方法です。追加で README に含めたい具体的な実行例や設定テンプレート（.env.example など）を用意する場合は、その内容（必須環境変数一覧や推奨値）を知らせてください。必要に応じてサンプル .env.example の草案も作成します。