# KabuSys

KabuSys は日本株向けの自動売買 / 監視基盤のサンプル実装です。  
このリポジトリは取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニューススコアリングなどのコンポーネントを含みます。

以下はコードベース（src/kabusys 以下）から自動生成した README です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド例）
- ディレクトリ構成（ファイル一覧と説明）
- 重要な環境変数・フラグファイル

---

プロジェクト概要
- 日本株自動売買システムの小規模なサンプル実装。
- コンポーネント: ExecutionEngine（発注・注文管理）、Monitoring（システム監視・リスク監視・アラート）、Portfolio Construction、Research（ファクター計算）、AI（ニュース NLP / レジーム判定）、ツール（検証レポート、Streamlit ダッシュボード）など。
- DB: SQLite（監視・注文ログ等）と DuckDB（時系列株価・ファイナンスデータ等）を併用。
- Paper Trading（模擬取引）機能を備え、本番 DB と分離して動作可能。

機能一覧
- Execution
  - 注文作成・管理（OrderManager / OrderRepository）
  - 起動時のリコンシリエーション（Reconciler）
  - Paper Trading モード（MockBroker）対応（KABUSYS_ENV=paper_trading）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度
  - TradeMonitor: 滞留注文（stale）・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新、risk_logs 記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止をトリガ
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio
  - 候補選定（score / equal）、ウェイト算出、ポジションサイズ算出、セクターキャップ、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計測・特徴量要約
- AI
  - ニュースのセンチメントスコアリング（OpenAI API を利用）
  - 市場レジーム判定（ETF MA + マクロニュースの LLM 評価を合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）
  - 監視 DB の初期化/マイグレーションユーティリティ

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の union 演算子などの型表現を使用）。
2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージ（例）
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があればそれを利用）
4. プロジェクトルート構成
   - 作業パスはリポジトリのルート（.git や pyproject.toml がある場所）で作業してください。
5. .env
   - .env または .env.local をプロジェクトルートに置くと自動で読み込まれます（OS 環境変数より優先度低）。
   - 自動ロードを無効にするには環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須（代表例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - LINE 通知を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
6. data ディレクトリ
   - 実行時に自動作成されますが、手動で作る場合はプロジェクトルート直下の data/ を作成しておくとよいです。

重要な環境変数（主なもの）
- KABUSYS_ENV: execution の実行環境。値: development | paper_trading | live
  - paper_trading: MockBroker を使用し、paper 専用 SQLite (PAPER_TRADING_SQLITE_PATH) を使用
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: PaperTrading モードの SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

使い方（主要コマンド例）
注意: パッケージがインストールされていない場合は、プロジェクトルートから PYTHONPATH=src を渡して実行してください。

- 実行エンジン起動（本番 / paper_trading 切替）
  - 本番に相当する起動（KABUSYS_ENV=live）
    - PYTHONPATH=src KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（DB 分離・MockBroker）
    - PYTHONPATH=src KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時、data/execution.pid が作成され、data/stop_requested.flag によって停止要求が検出されます。

- 監視プロセス起動
  - デフォルトポーリング 60 秒（環境変数で上書き可）
    - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
  - 監視は KABUSYS_ENV に関わらず本番の sqlite_path（SQLITE_PATH）を参照します（監視ログは共通に記録されます）。
  - 停止は data/stop_requested.flag を作成または KeyboardInterrupt。

- Streamlit ダッシュボード
  - PYTHONPATH=src streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視データを可視化します（デフォルトは読み取り専用で DB を開く）。

- Paper Trading 検証レポート
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - またはデフォルト DB を環境変数で指定:
    - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY 環境変数を設定してから呼び出してください。これらはライブラリ関数として利用できます（例: kabusys.ai.score_news() / kabusys.ai.regime_detector.score_regime()）。
  - CLI ラッパーは用意されていないため、スクリプト等からインポートして呼び出します。

停止用フラグ・PID ファイル
- data/stop_requested.flag: run_monitoring / run_execution のループを検出して安全停止します（管理用）。
- data/execution.pid: ExecutionEngine の PID 管理に使用。
- data/kill.flag: KillSwitch により、致命的な条件で ExecutionEngine を停止させるために書き込まれるフラグ。
  - KillSwitch はリスク監視（ドローダウン等）条件でこのファイルを作成します。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / .env 読み込み・Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - execution/
    - order_manager.py — 注文マネージャ
    - reconciler.py — 起動時のリコンシリエーション
    - order_repository.py, order_record.py, execution_engine.py, broker_factory.py, ...（発注関連実装）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化ラッパー（MonitoringDB）
    - system_monitor.py — CPU/メモリ/disk/process/data 最新性監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — KillSwitch（kill.flag 書き込み）
    - alert_manager.py — LINE push 通知（クールダウン含む）
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・ウェイト計算
    - position_sizing.py — 株数計算・上限・ラウンド
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — raw_news を LLM で評価して ai_scores に書き込む
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定、DB に書き込み
  - data/  (実行時に使用)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用、PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - execution.pid / kill.flag / stop_requested.flag

設計上の注意点
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は KABUSYS_ENV に関係なくデフォルトの sqlite_path（SQLITE_PATH）を使用します。Paper Trading DB は run_execution で切り替えられますが、監視は本番監視 DB を参照します。
- AI 連携（OpenAI）は API 利用料・レート制限に注意してください。レスポンス検証・リトライロジックは組み込まれていますが、実運用ではさらに堅牢な運用が必要です。
- Streamlit ダッシュボードは読み取り専用で監視 DB を開く想定です。DB ファイルを直接ロックするため、複数プロセスから同時に書き込みを行う場合は注意してください。

トラブルシュート（よくある点）
- .env が読み込まれない → KABUSYS_DISABLE_AUTO_ENV_LOAD を確認、プロジェクトルートが正しいか確認
- 実行がすぐ終了する / PID チェックで stale と判定される → data/execution.pid の内容を確認
- OpenAI 関連が失敗する → OPENAI_API_KEY が設定されているか、ネットワークとレート制限を確認
- DuckDB/SQLite ファイルが見つからない → DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 環境変数を確認

ライセンス・貢献
- 本 README はコードベースの説明を目的としたものです。実際の運用や商用利用は各自の責任で行ってください。セキュリティ（API キー管理・秘密情報の取り扱い）に十分留意してください。

---

以上がリポジトリの概要・セットアップ・使い方です。必要ならば「各モジュールの API（関数・クラスの詳細使用例）」「systemd / Docker 化手順」「CI/CD 設定例」などの追加ドキュメントも作成できます。どの情報がさらに必要か教えてください。