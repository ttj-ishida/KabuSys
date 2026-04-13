# KabuSys

KabuSys は日本株向けの自動売買システムのリファレンス実装です。取引エンジン、リスク管理、監視・アラート、ポートフォリオ構築、ファクター計算、そしてニュースを用いた AI スコアリングなど、実運用を意識したコンポーネント群を含みます。

以下は、このリポジトリの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 実行方法（使い方）
- 環境変数（主要）
- ディレクトリ構成（主要ファイルの説明）
- 補足・運用上の注意

---

プロジェクト概要
- 日本株自動売買システムの構成要素をモジュール化した実装例。
- 注文作成→ブローカー送信→状態同期→リコンシリエーションを含む注文管理。
- リスク監視（ドローダウン、ポジション上限）、システム監視（CPU/MEM/DISK、データ鮮度）、アラート（LINE）を備える。
- DuckDB を使った研究用ファクター計算や、OpenAI を用いたニュースセンチメント（AI スコアリング）、市場レジーム判定モジュールを提供。
- Paper Trading モードを用意し、本番 DB と分離して検証可能。

主な機能（抜粋）
- ExecutionEngine（発注・約定管理、リスク管理、リコンシリエーション）
- OrderManager / OrderRepository（注文明細管理と DB 永続化）
- RiskManager（最大ポジション比率、利用率、ドローダウン等の制約）
- MonitoringEngine（SystemMonitor / TradeMonitor / RiskMonitor の統合ポーリング）
- AlertManager（LINE Messaging API への一方向プッシュ通知、クールダウン管理）
- KillSwitch（閾値超過時にフラグファイルを書き ExecutionEngine を停止させる仕組み）
- Portfolio モジュール（候補選定、重み算出、ポジションサイズ算出、セクター制限、レジーム乗数）
- Research モジュール（モメンタム / ボラティリティ / バリュー等のファクター計算、IC 計算）
- AI モジュール（news_nlp：ニュースを LLM でセンチメント化 → ai_scores、regime_detector：MA200 とマクロニュースの LLM 評価を合成）
- Tools（paper_verification_report、streamlit ダッシュボード）

前提・依存関係
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (監視ダッシュボードを利用する場合)
- 標準ライブラリ: sqlite3, datetime, argparse 等

セットアップ手順（例）
1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone ...
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がない場合は上記を参考にインストール）
4. data ディレクトリを作成（デフォルトの DB/フラグファイル等）
   - mkdir -p data
5. 環境変数を設定
   - .env に主要なキーを記載する（下記「環境変数」を参照）
   - 本リポジトリの config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます
     - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

実行方法（使い方）

- ExecutionEngine（発注エンジン）を起動
  - 本番相当:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（モックブローカー / data/paper_trading.db に保存）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 備考:
    - run_execution は起動時にプロセス優先度を high に設定します（set_process_priority）。
    - Paper Trading 時は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。

- Monitoring（ポーリング監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings に関係なく本番 sqlite_path（data/monitoring.db 等）を使用してログを永続化します。
  - run_monitoring も起動時にプロセス優先度を high に設定します。

- Streamlit ダッシュボード（監視データ可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数で代替可能）
  - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ 等

環境変数（主要）
- 設定一般
  - KABUSYS_ENV： development | paper_trading | live （default: development）
  - LOG_LEVEL： ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- API / 認証
  - JQUANTS_REFRESH_TOKEN：J-Quants API 用（必須の場合）
  - KABU_API_PASSWORD：kabuステーション API 用（必須）
  - KABU_API_BASE_URL：kabu API base URL（default http://localhost:18080/kabusapi）
  - OPENAI_API_KEY：OpenAI API キー（AI モジュールで必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID：AlertManager 用（未設定時は通知スキップ）
- DB / ファイルパス
  - DUCKDB_PATH（default: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、default: data/monitoring.db） ← Monitoring は常にここを使用
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、default: data/paper_trading.db）
  - PID_FILE_PATH（default: data/execution.pid）
  - KILL_FLAG_PATH（default: data/kill.flag）
- その他
  - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject、default: instant）
  - MONITOR_POLL_INTERVAL（run_monitoring 用、秒。0以下無効 → デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env 自動読み込みを無効化）

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ宣言（バージョン等）
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じた挙動）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - execution/ (注文・ブローカー関連)
    - order_manager.py — 注文の状態遷移 / 送信ロジック
    - reconciler.py — 起動時リコンシリエーション（OrderSent の突合、ポジション差分検出）
    - （その他: broker_factory, execution_engine, order_repository などの実装が想定）
  - monitoring/ (監視関連)
    - monitoring_db.py — SQLite による監視ログ永続化（テーブル作成 / CRUD）
    - system_monitor.py — CPU/MEM/DISK, データ鮮度, PID チェック
    - trade_monitor.py — 滞留注文 / 約定異常価格検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイルにより ExecutionEngine 停止シグナルを送る
    - alert_manager.py — LINE へのプッシュ通知（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を束ねるポーリング実行
    - streamlit_dashboard.py — Streamlit ベースの監視 UI
  - portfolio/ (ポートフォリオ構成)
    - portfolio_builder.py — 候補選定・重み計算（等金額 / スコア加重）
    - position_sizing.py — 発注株数計算（risk_based / equal / score）
    - risk_adjustment.py — セクター上限適用、レジーム乗数
  - research/ (調査・ファクター計算)
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算、IC 計算、統計サマリ
  - ai/ (AI 関連)
    - news_nlp.py — ニュースを LLM（OpenAI）でセンチメント化して ai_scores に書き込み
    - regime_detector.py — MA200 + マクロニュースセンチメントを合成して市場レジームを判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポートを生成（CLI）
    - __init__.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足・運用上の注意
- .env の自動読み込み
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視 DB と発注 DB の分離
  - Monitoring 用 DB（sqlite_path）は監視ログ用に使用され、本番/ペーパーの設定にかかわらず監視は指定された sqlite_path を使います。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、本番 DB と分離します。
- Kill Switch / フラグファイル
  - kill.flag（Settings.kill_flag_path）を生成すると ExecutionEngine 停止のトリガーになります。存在確認 / 削除の API を備えています。
- OpenAI API
  - AI モジュール（news_nlp, regime_detector）は OPENAI_API_KEY を必要とします。API 呼び出しは失敗時でもフェイルセーフ（多くの箇所でゼロフォールバック）を実装していますが、API 使用にはコストとレイテンシが発生するため運用時は注意してください。
- 権限・優先度設定
  - set_process_priority によりプロセス優先度を変更します。OS によっては権限不足で設定できない場合があり、警告を出してスキップします。

ライセンスや貢献方法
- （このリポジトリに対するライセンスや貢献ガイドはここに追記してください）

---

以上がこのコードベースの概要と利用方法のまとめです。README の内容や補足説明をプロジェクト方針に合わせて調整したい場合は、特に運用フロー（起動手順、監視 → 実行の責務分離）や必須環境変数の扱いについて具体的な要望を教えてください。