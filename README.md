# KabuSys

KabuSys は日本株向けの自動売買 / リサーチ / 監視ユーティリティ群をまとめた小規模フレームワークです。本リポジトリは以下の機能を含み、SQLite / DuckDB をデータ永続化層として利用します。

- 注文送信・状態管理・リコンシリエーション（Execution）
- 監視（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading 用の分離実行・検証レポート生成
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- 研究用ファクター計算 / 特徴量解析（DuckDB ベース）
- AI（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定
- Streamlit ベースの監視ダッシュボード

以下にセットアップ・実行方法、主要コンポーネントの役割、ディレクトリ構成をまとめます。

---

## 主な特徴（機能一覧）

- Execution
  - Broker クライアント経由で注文を送信 / 状態同期
  - 再起動時の Reconciler による自動復旧
  - Paper Trading 環境では MockBroker を使い、本番 DB と分離（data/paper_trading.db）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）や約定価格異常を検出
  - RiskMonitor: ドローダウン / ポジション上限監視、必要に応じて kill.flag を作成して Execution を停止可能
  - AlertManager: LINE Push API への通知（クールダウン管理）
  - Monitoring DB（SQLite）へログ永続化（system_status / trade_logs / risk_logs / positions / dashboard）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- AI
  - news_nlp: OpenAI によるニュースセンチメント（ai_scores テーブルへ書き込み）
  - regime_detector: ETF MA 比・マクロニュースの LLM センチメントを組み合わせて市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視用）

---

## 必要環境 / 依存ライブラリ

- Python 3.9+
- SQLite（Python 標準ライブラリ）
- pip パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- （オプション）LINE Messaging API の使用には channel access token / user id が必要
- 環境によっては追加で OS 権限（プロセス優先度設定等）が必要

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```
※requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

---

## 環境変数と設定（config）

設定は環境変数、またはプロジェクトルートの .env / .env.local により読み込まれます。自動読み込みはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBroker が使われ、本番 DB と分離されます
- PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — Execution の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

.env のパースはシェルライクな形式を許容し、.env.local は .env を上書きします。OS 環境変数は上書きされません（protected）。

---

## ディレクトリ構成（主要ファイルの説明）

（ルートは `src/kabusys` を想定）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env の読み込み、Settings クラス
  - run_monitoring.py — SystemMonitor の単独ポーリングスクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて paper_trading を分離）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力 CLI
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化・CRUD ラッパー（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込み・管理ロジック
    - alert_manager.py — LINE push 通知ラッパー（クールダウン管理）
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード（起動例あり）
  - execution/
    - order_manager.py — 注文作成 / 送信 / 状態遷移管理（OrderManager）
    - reconciler.py — 起動時の注文・ポジション突合（Reconciler）
    - （その他 broker / order_repository 等の実装が想定されます）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け（equal/score）
    - risk_adjustment.py — セクター上限・レジーム乗数
    - position_sizing.py — 株数決定・投下資金スケーリング・単元丸め
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュースを OpenAI に投げて銘柄別センチメントを ai_scores に書き込む
    - regime_detector.py — ETF MA とマクロニュースを組み合わせて市場レジームを判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

※上記は主要モジュールのサマリであり、プロジェクト全体の参照設計です。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 取得
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai requests streamlit
   ```
4. データディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```
5. .env を作成（プロジェクトルート）。最低限必要な変数:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   ```
   - paper_trading を使う場合は KABUSYS_ENV=paper_trading とし、必要であれば PAPER_TRADING_SQLITE_PATH を設定
6. DuckDB / SQLite の初期化は起動スクリプトが自動的に行います（monitoring DB のテーブル作成等）

---

## 実行方法（主要なコマンド）

- 監視プロセスを起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（デフォルト: data/monitoring.db）を使用してログを残します

- 実行エンジン（ExecutionEngine）を起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB（デフォルト: data/paper_trading.db）と MockBroker を使用します
  - 起動時にプロセス優先度を High に変更し、PID ファイルを作成して管理します

- Streamlit 監視ダッシュボード（読み取り専用）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート出力
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI スコア / レジーム判定（ライブラリ関数として呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取りテーブルを更新します。API キーは引数か環境変数 OPENAI_API_KEY を使用します。

---

## 運用上の注意・挙動

- Settings は .env/.env.local をプロジェクトルートから自動ロードします（プロジェクトルートの判定は .git または pyproject.toml に依存）。OS 環境変数は保護されます。
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（data/monitoring.db）を使用して監視ログを残します。
- run_execution は paper_trading の場合、本番 DB と分離して PAPER_TRADING_SQLITE_PATH（data/paper_trading.db など）を使用します。
- Process priority: 起動時に set_process_priority("high") を試行します。権限がない場合は警告が出てスキップされます。
- kill.flag:
  - RiskMonitor / KillSwitch ロジックにより kill.flag（デフォルト data/kill.flag）が作成されると ExecutionEngine の停止シグナルとして機能します。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除できます（Settings.kill_flag_clear_on_start を参照）。
- Paper Trading の挙動は PAPER_FILL_MODE（instant / partial / never / reject）で制御されます。
- DuckDB を用いたファクター計算・研究モジュールは本番口座の注文 API にアクセスしない設計です（データベースの prices_daily / raw_financials 等を使用）。

---

## コードの読み方（ポイント）

- monitoring/monitoring_db.py は監視用 SQLite のスキーマ初期化と簡易 CRUD（MonitoringDB）を提供します。テーブルは冪等に作成され、マイグレーション（列追加）も含みます。
- monitoring/system_monitor.py は psutil によるシステムメトリクスの取得と duckdb を使ったデータ鮮度チェックを行い、結果を MonitoringDB に保存します。
- monitoring/trade_monitor.py は OrderRepository を参照して滞留注文 / 約定異常を検出し、risk_logs に記録します。
- execution/reconciler.py は起動時に OrderSent の同期やブローカーとのポジション差分検査を行う重要ロジックです（障害回復用）。
- ai/news_nlp.py / ai/regime_detector.py は外部 LLM（OpenAI）呼び出しを行います。API エラーはリトライやフェイルセーフ（代替値）を使って堅牢化されています。

---

## よくある質問

Q: 開発環境で Paper Trading を試したい
- A: 環境変数を KABUSYS_ENV=paper_trading に設定して run_execution を起動してください。Paper Trading 用の DB（PAPER_TRADING_SQLITE_PATH）へ取引ログが記録され、本番 DB には影響しません。

Q: 監視ループの間隔を短くしたい
- A: MONITOR_POLL_INTERVAL 環境変数を秒数で設定してください（例: MONITOR_POLL_INTERVAL=30）。

Q: OpenAI を使いたいがキーはどこへ入れる？
- A: OPENAI_API_KEY 環境変数、もしくは AI 関数の api_key 引数で渡します。

---

## 参考コマンドまとめ（例）

- 簡易起動（開発）
  ```bash
  export KABUSYS_ENV=development
  export JQUANTS_REFRESH_TOKEN=...
  export KABU_API_PASSWORD=...
  export OPENAI_API_KEY=...
  python -m kabusys.run_monitoring
  python -m kabusys.run_execution
  ```

- Paper Trading の検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

この README はコードベースの主要機能と実行手順を簡潔にまとめたものです。実装や各モジュールの細部（エラー処理方針、DB スキーマ詳細、アルゴリズムの数理的説明）はソースコメント／ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）を参照してください。追加で README に含めたい内容（例: .env.example の具体的なテンプレート、全面的な運用フロー図、開発用単体テストの実行手順など）があれば教えてください。