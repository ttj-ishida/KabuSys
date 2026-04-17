# KabuSys

日本株向け自動売買システム（ミニマル実装）のコードベース用 README。

以下はこのリポジトリの主要機能・セットアップ・起動方法・ディレクトリ構成の概要です。  
ソースコード内の docstring と設計コメントに従ってまとめています。

---

## プロジェクト概要

KabuSys は日本株自動売買のための小規模なフレームワークです。主な目的は次のとおりです。

- 戦略に基づく銘柄選定、配分、発注までのエンジン（ExecutionEngine）
- システム監視・アラート・KillSwitch によるプロテクション（Monitoring）
- リサーチ用のファクター計算・特徴量解析（Research）
- ニュースの NLP によるセンチメント評価（AI モジュール）
- Paper Trading を想定した分離された DB とモックブローカー
- 運用・検証用のツール（検証レポート、Streamlit ダッシュボード 等）

設計方針として、データ永続化は主に SQLite / DuckDB を使用し、LLM 呼び出しは OpenAI（gpt-4o-mini）想定で実装されています。環境依存の設定は環境変数 / .env で管理します。

---

## 機能一覧（主な機能）

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの切替（本番 / paper_trading のモック）
  - 発注管理（OrderManager, OrderRepository）
  - 再起動時のリコンシリエーション（Reconciler）

- 監視系
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor: 滞留注文や約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み & LINE 通知
  - MonitoringEngine: 上記モニタを束ねるポーリングループ
  - Streamlit ダッシュボード（監視データ表示）

- リサーチ/ポートフォリオ
  - ファクター計算 (momentum, volatility, value)
  - 将来リターン計算・IC 計算・統計サマリー
  - 銘柄選定・等比重/スコア加重配分・ポジションサイズ計算
  - セクターキャップ、レジームに応じた乗数

- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM でスコア化し ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロセンチメントの合成で市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading 検証レポート生成
  - streamlit_dashboard.py: 監視用ダッシュボード起動用スクリプト

---

## 動作要件（推奨）

- Python 3.10+（型注釈や match を想定しないが typing の|表記などのため 3.10 推奨）
- 以下の外部ライブラリ（requirements.txt がある場合はそれを利用してください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリに含まれます）
- ネットワーク（OpenAI API / LINE API へアクセスする場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージ展開。
2. 仮想環境を作成して依存をインストール（上記参照）。
3. 環境変数を設定:
   - 手動で export するかプロジェクトルートに `.env` / `.env.local` を配置。
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml）を起点に自動で .env を読み込みます。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. 必須環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用
   - KABU_API_PASSWORD — kabu ステーション API 用（実運用時）
   - OPENAI_API_KEY — news_nlp / regime_detector 利用時
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE）利用時
5. データフォルダの初期化（任意）:
   - デフォルト DB パスは `data/monitoring.db`, `data/kabusys.duckdb` 等。必要に応じてディレクトリを作成してください（多くのコードは自動で parent を作成しますが、PID/FLAG 等の配置を事前に確認すると安全です）。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）。デフォルト 60
- SQLITE_PATH: 監視用 SQLite（monitoring）パス。デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB パス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（紙口座用）。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject）。デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー
- PID_FILE_PATH, KILL_FLAG_PATH: PID / Kill flag のパス（デフォルトは data 以下）

Settings は `src/kabusys/config.py` に実装されており、必要な env が未設定だと例外を raise します（必須項目は _require() でチェック）。

---

## 使い方（起動方法・コマンド）

いくつかの主要な起動手順とコマンド例を示します。

- Monitoring（監視ループ）を起動:
  - 環境変数 MONITOR_POLL_INTERVAL を設定してポーリング間隔を変更できます。
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 挙動:
    - Settings から本番の sqlite_path を参照して監視 DB を初期化（init_monitoring_db）。
    - `data/stop_requested.flag` を検出するとループを抜けて終了します。
    - プロセス優先度を high に設定しようとします（psutil に依存）。

- ExecutionEngine（注文実行）を起動:
  - Paper Trading モードでは `KABUSYS_ENV=paper_trading` とすると MockBrokerClient が使われ、Paper 専用 DB を利用します（PAPER_TRADING_SQLITE_PATH）。
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 挙動:
    - 起動時にリコンシリエーション等を行い、別スレッドで engine.run_session() を実行します。
    - `data/stop_requested.flag` を検出すると安全に停止します。
    - 実行中は `data/execution.pid` を作成・管理します。

- Paper Trading 検証レポート（コマンドライン）:
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - `--db PATH` で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先して使用）。

- Streamlit ダッシュボード:
  - 実行:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ダッシュボードは監視用 SQLite を読み取り専用で参照します（`?mode=ro`）。

- AI モジュール（プログラムから呼ぶ）:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 両関数とも `api_key` 引数または環境変数 OPENAI_API_KEY を参照します。失敗時はフェイルセーフ（例: macro_sentiment=0.0）する実装が含まれますが、APIキーは必須チェックを行う箇所もあります。

---

## ファイル／フラグ類（運用時の注意）

- 停止フラグ: data/stop_requested.flag — run_monitoring / run_execution が存在を見て停止処理を行います。
- Kill フラグ: data/kill.flag — KillSwitch により ExecutionEngine 停止を要求するために使用。存在すれば Execution 起動時に起動しないような挙動もあります。
- PID ファイル: data/execution.pid — Engine の PID 管理に使用
- 監視 DB 初期化: init_monitoring_db() により必要なテーブルとマイグレーションが適用されます（冪等）。

---

## ディレクトリ構成（主要モジュールの概要）

以下は `src/kabusys` 以下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数と Settings 管理（.env 自動読み込みロジック含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）

- kabusys/monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ永続化 / MonitoringDB クラス
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor.py — 滞留注文・約定価格異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込み・判定
  - alert_manager.py — LINE Push API を使った通知（クールダウン付き）
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit で表示するダッシュボード

- kabusys/execution/
  - execution_engine.py — （実装箇所が存在）ExecutionEngine 本体
  - order_manager.py — 発注フロー（state machine の外向き API）
  - order_repository.py — Orders DB アクセス
  - reconciler.py — 起動時の注文/ポジションの突合せ
  - broker_* — ブローカー関連ファクトリ / API インターフェース（コード内参照）

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定、重み計算（等重・スコア加重）
  - position_sizing.py — 発注株数計算、単元調整、aggregate cap
  - risk_adjustment.py — セクター上限、レジーム乗数

- kabusys/research/
  - factor_research.py — Momentum / Volatility / Value のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- kabusys/ai/
  - news_nlp.py — raw_news を LLM によって銘柄別センチメント化し ai_scores に書き込む
  - regime_detector.py — ETF MA200 とマクロセンチメントを合成して market_regime に書き込む

- kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成（CLI）

- kabusys/utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ラッパ（psutil 利用）

---

## 運用上の注意 / ベストプラクティス

- Paper Trading は本番 DB と完全に分離されています。`KABUSYS_ENV=paper_trading` を指定すると `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に書き込みます。
- .env の取り扱い:
  - OS 環境変数が優先される
  - `.env.local` は `.env` の上書きとして扱われる（自動ロード）
  - テストや CI で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- OpenAI 呼び出しはネットワーク／レート制限の考慮がされています（エクスポネンシャルバックオフ）。ただし API キーと利用制限には注意してください。
- Monitoring / Execution ではプロセス優先度を "high" にしようと試みます（権限によっては警告が出てスキップされます）。
- KillSwitch により `data/kill.flag` が書かれると Execution の停止を誘発します。運用時にこのファイルの存在を慎重に扱ってください。
- DB マイグレーションは簡易的に init_monitoring_db() 内で実行されます。プロダクションで大規模なスキーマ変更がある場合は別途管理することを推奨します。

---

## 開発 / テスト

- 多くの関数は純粋関数（副作用が小さい）か、DB 接続を注入する形で設計されています。単体テストが行いやすい構造です。
- OpenAI など外部 API を呼ぶ箇所は `_call_openai_api` のような関数を patch してモック可能です（テスト用に想定されています）。

---

以上が本リポジトリの README 内容です。必要であれば以下を追加で作成できます。

- requirements.txt / poetry/pyproject.toml 例
- .env.example（必須環境変数テンプレート）
- デプロイ / systemd ユニット / supervisor 用のサンプル設定
- よくあるトラブルシュート（PID フォーマット不正や DB ロック等）

追加で欲しいドキュメントや、README の別言語版（英語）などがあれば教えてください。