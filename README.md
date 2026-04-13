KabuSys
======

日本株自動売買システムのコードベース（抜粋）向け README。  
本ドキュメントはプロジェクトの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

概要
---
KabuSys は日本株の自動売買・検証・監視を目的としたモジュール群です。主な機能は以下のとおりです。

- 注文の生成・送信・状態管理（ExecutionEngine / OrderManager）
- ブローカーとの照合（Reconciler）
- ポートフォリオ構築（銘柄選定、重み、株数決定）
- リスク管理（ドローダウン、ポジション数上限等）
- 監視（プロセス可否、システム資源、データ鮮度、注文滞留、約定異常）
- アラート（LINE Push）
- Paper Trading 用の分離 DB・検証レポート
- 研究用ファクター計算・特徴量探索（DuckDB を用いたファクター群）
- AI を用いたニュースセンチメント評価・市場レジーム判定（OpenAI API）

設計上のポイント:
- 環境変数ベースの設定（Settings）と .env 自動読み込み（プロジェクトルートが検出される場合）。
- Paper Trading と本番（live）は DB を分離（data/paper_trading.db と data/monitoring.db 等）。
- DuckDB をデータ分析（prices_daily, raw_financials 等）に使用。
- 監視は SQLite（monitoring DB）へ永続化。Streamlit ダッシュボードで確認可能。

---

機能一覧
---
- Execution
  - OrderManager: 注文作成・送信、重複検出、状態遷移管理
  - RiskManager: 発注リスク制御（最大ポジション比率、利用率、サーキットブレーカー等）
  - Reconciler: 再起動時のリコンシリエーション（OrderSent の同期、ポジション差分検出）
  - BrokerClientFactory を介して実口座 / MockBroker の切替（KABUSYS_ENV）
- Portfolio
  - 銘柄選定(select_candidates)、重み付け(calc_equal_weights / calc_score_weights)
  - セクターキャップ適用(apply_sector_cap)、レジーム乗数(calc_regime_multiplier)
  - 株数決定(calc_position_sizes)（単元株丸め、aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - news_nlp.score_news: ニュース記事をまとめて OpenAI に送信し銘柄別センチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF の MA200 とマクロニュースを合成して market_regime に書き込む
- Monitoring
  - SystemMonitor: CPU/Mem/Disk、プロセス生存、データ鮮度をチェックし system_status に記録
  - TradeMonitor: 滞留注文・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション数上限のチェック、dashboard 更新
  - KillSwitch: しきい値到達時に kill.flag を書き ExecutionEngine 停止を指示
  - AlertManager: LINE へ通知（クールダウン管理）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
- Tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを標準出力に出す

---

セットアップ手順
---
前提:
- Python 3.8+（typing | 演算や未来注釈対応のため推奨は 3.10+）
- システムに sqlite3（標準ライブラリ）、DuckDB、psutil がインストール可能であること

例: 仮想環境作成 & 必要パッケージインストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係のインストール（最低限）
   - pip install duckdb psutil requests openai streamlit

   ※ 実行環境に応じて追加ライブラリが必要になる可能性があります（例: broker client 実装に依存）。

3. データディレクトリ準備
   - mkdir -p data

4. 環境変数 / .env の用意
   - プロジェクトルートに .env を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須の場面あり）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須の場面あり）
- OPENAI_API_KEY: OpenAI API キー（ニュース/レジーム機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信用
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）

例 .env（最小）
    KABUSYS_ENV=paper_trading
    OPENAI_API_KEY=sk-...
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    DUCKDB_PATH=data/kabusys.duckdb

---

使い方（起動方法・主要コマンド）
---
1) ExecutionEngine（戦略実行）
- 本番/ペーパートレード切替は KABUSYS_ENV で制御（paper_trading は MockBroker を使用）
- 実行:
    python -m kabusys.run_execution
  内部で Settings を読み、適切な SQLite/duckdb に接続してセッションを開始します。

2) Monitoring（ポーリング監視）
- 監視ループを開始:
    python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
- 監視は常に（KABUSYS_ENV にかかわらず）本番の sqlite_path を使用します（運用設計による）

3) Streamlit ダッシュボード（監視ビュー）
- 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 監視 DB を読み取り専用で開いてダッシュボードを表示します

4) Paper Trading 検証レポート
- コマンド:
    python -m kabusys.tools.paper_verification_report
- オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

5) AI 機能（ニューススコア / レジーム判定）
- プログラムから呼び出し:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
- どちらも OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）

注意点・運用上のヒント:
- Paper Trading 環境は本番 DB と完全分離されています（PAPER_TRADING_SQLITE_PATH を利用）。
- 起動時にプロセス優先度を "high" に上げようとします（set_process_priority）。
  必要に応じて権限や環境での挙動を確認してください（権限不足では警告のみ）。
- kill.flag（Settings.kill_flag_path）は ExecutionEngine 停止のための外部シグナルです。kill.flag のクリアは Settings.kill_flag_clear_on_start に従う運用が可能。
- .env の自動ローディングはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI / Docker 等では環境変数を明示的に渡すことを推奨します。

---

ディレクトリ構成（主要ファイルと役割）
---
src/kabusys/
- __init__.py
  - パッケージ基本情報（__version__ 等）
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロード・バリデーション）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による Mock/実ブローカー切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

subpackages:
- execution/
  - order_manager.py — 注文状態遷移と外向き API
  - reconciler.py — 再起動時のリコンシリエーション
  - その他（broker_factory, execution_engine, order_repository 等が存在想定）
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化および永続化 API
  - system_monitor.py — CPU/Mem/Disk/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 複数モニタを束ねるエンジン
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE への通知
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数算出（リスク基準 / 等配分等）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に保存
  - regime_detector.py — MA200 とマクロニュースで市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading DB から検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

その他:
- data/
  - デフォルト DB・PID・フラグ等を格納する想定ディレクトリ（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag 等）

---

開発・運用に関する補足
---
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブルとインデックスを作成し、既存カラム追加の簡易マイグレーションロジック（ALTER TABLE ADD COLUMN）を含みます。
- テスト運用: KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動ロードを無効化できます。
- ロギング: 各スクリプトは基本的に logging.basicConfig(level=logging.INFO) で起動します。必要に応じて LOG_LEVEL を設定してください。
- 安全設計: LLM 呼び出しや外部 API 呼び出しはリトライ・フェイルセーフ（API失敗時はスコア 0.0 等にフォールバック）を考慮した実装になっています。

---

ライセンス・貢献
---
このリポジトリのライセンスや貢献ルールはここに記載されていません。実運用や公開を行う場合は適切なライセンス表記とセキュリティ対策（APIキーの管理、取引ログ・資金管理の監査等）を行ってください。

---

問題報告・質問
---
コードに関する質問や不具合があれば、該当モジュール名・再現手順・期待する挙動を添えて問い合わせてください。