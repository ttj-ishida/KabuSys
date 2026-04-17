# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要モジュールに基づき、プロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

重要: 実運用にあたっては API キーやブローカー設定、手数料・スリッページ等のパラメータの調整を必ず行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を含むシステム設計の実装例です。

- シグナル → 注文発行 → 注文状態管理 → リコンシリエーション（復旧）
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制限、レジーム乗数）
- リサーチ（ファクター計算、特徴量探索、IC算出）
- AI（ニュースの NLP によるセンチメント、レジーム判定）
- 監視（プロセス/データ鮮度/約定異常/ドローダウン監視）とアラート（LINE）
- Paper Trading モード（本番 DB と分離して動作）
- Streamlit ダッシュボード（監視データ可視化）
- 検証用レポート生成スクリプト（paper_trading の検証）

設計方針の一部:
- DuckDB を用いた時系列/ファクタ計算（分析用）と、SQLite を用いた監視/注文ログの永続化を併用
- 本番/ペーパートレードを環境変数で切り替え
- LLM（OpenAI）呼び出しはフェイルセーフ（失敗時はデフォルト値で継続）

---

## 主な機能一覧

- execution
  - 注文作成・管理（OrderManager）
  - ブローカーインタフェース抽象化（BrokerClientFactory 等）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- portfolio
  - 候補選定（select_candidates）
  - 重み計算（等重み／スコア重み）
  - リスク調整（セクター上限、レジーム乗数）
  - 株数算出（単元丸め、aggregate cap 等）
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ai
  - ニュース NLP による銘柄別センチメント（OpenAI を利用）
  - マクロニュース＋ETF MA による市場レジーム判定
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - KillSwitch：条件により ExecutionEngine を停止させるフラグ生成
  - AlertManager：LINE Push による通知（クールダウン管理あり）
  - MonitoringEngine：各種モニターをまとめてポーリング
  - Streamlit ダッシュボード（監視 DB の可視化）
- tools
  - paper_verification_report：Paper Trading の検証レポート生成

---

## セットアップ

以下は開発 / 実行環境の最低限の手順です。環境に応じて Python バージョンやパッケージを調整してください（ソースは Python 型注釈を多用しているため Python 3.10+ を推奨）。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 代表的な依存（実際の requirements.txt がない場合は下記をインストールしてください）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

4. 環境変数 / .env
   - プロジェクトルートに `.env` や `.env.local` を配置すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY
   - その他（代表例）:
     - KABUSYS_ENV (development | paper_trading | live)  デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH デフォルト: data/kabusys.duckdb
     - SQLITE_PATH デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db
     - PAPER_FILL_MODE (instant|partial|never|reject) デフォルト: instant
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
     - PID_FILE_PATH, KILL_FLAG_PATH 等

   - サンプル `.env`（一例）
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     ```

5. データディレクトリ
   - `data/` ディレクトリを作成しておくと便利です（PID/flag/DB のデフォルトパスがここにあるため）。

---

## 使い方（主要スクリプト）

以下は主要な起動手順の例です。実行はプロジェクトルート（pyproject.toml または .git のある位置）で行ってください。

- 監視プロセスの起動（Monitoring）
  - 環境変数でポーリング間隔を指定可能: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 特記事項:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を参照する想定）。
    - 停止フラグ: `data/stop_requested.flag` が存在するとループを抜けます。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution
  - 停止フラグ: `data/stop_requested.flag` が存在すると停止を試みます。
  - PID ファイル: `data/execution.pid` に PID を出力します（設定で変更可能）。

- Paper Trading 検証レポート
  - データベース（paper_trading.db）に記録された取引ログを解析してレポートを標準出力に出力します。
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB を明示する場合:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード（監視データ閲覧）
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で DB を開くため、MonitoringEngine を先に起動してデータを蓄積しておくことを推奨。

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または明示的引数）
  - プログラム的呼び出し例:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続と target_date を受け取り、テーブル（raw_news / news_symbols / ai_scores / prices_daily / market_regime 等）を読み書きします。

---

## 主要設定・環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要に応じて）
- KABU_API_PASSWORD: kabuステーション API パスワード（実運用で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードでの約定動作）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知用

.env の自動読み込み:
- リポジトリルート（.git または pyproject.toml が存在するディレクトリ）を探索して `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## ディレクトリ構成（抜粋・説明）

src/kabusys/
- __init__.py
  - パッケージ初期化、バージョン等
- config.py
  - 環境変数読み込み・Settings クラス（各種設定の取得ロジック）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（ペーパートレード分離ロジック含む）

modules / サブパッケージ:
- execution/
  - order_manager.py         — 発注・注文状態管理の外向き API
  - order_repository.py      — SQLite による注文永続化（ファイル内には他実装がある）
  - reconciler.py            — 起動時の自動復旧・照合ロジック
  - risk_manager.py          — リスク制御ロジック
  - execution_engine.py, broker_* （実装の想定）
- monitoring/
  - monitoring_db.py         — SQLite スキーマ定義・永続化ヘルパ
  - system_monitor.py        — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常検出
  - risk_monitor.py          — ドローダウン・ポジション数監視
  - kill_switch.py           — フラグファイルによる停止
  - alert_manager.py         — LINE 通知
  - monitoring_engine.py     — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py   — Streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py     — 候補選定・重み計算
  - position_sizing.py       — 株数計算・制約処理
  - risk_adjustment.py       — セクターキャップ・レジーム乗数
- research/
  - factor_research.py       — モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
  - feature_exploration.py   — 将来リターン、IC、統計サマリー
- ai/
  - news_nlp.py              — ニュース集約・OpenAI 呼び出し・ai_scores 書き込み
  - regime_detector.py       — ETF MA + マクロニュースでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート
- utils/
  - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
- data/
  - （実行時生成される DB / PID / flag ファイル等を置くディレクトリを想定）

---

## 運用上の注意 / ヒント

- Paper Trading モードは本番 DB と分離して動作します。KABUSYS_ENV=paper_trading を使って必ず分離してください。
- AI（OpenAI）を使用する機能は API コストとレイテンシが発生します。リトライ・バックオフの実装はされていますが、呼出頻度とコスト管理に注意してください。
- Monitoring は監視用 DB に状態を吐きます。初回は自動でテーブル作成（マイグレーション）されますが、DB ファイルの配置権限やファイルパスに注意してください。
- PID/flag ファイルによる停止制御を採用しています。外部から停止させたい場合は `data/stop_requested.flag` を作成するか、`KillSwitch` を利用して `data/kill.flag` を作成してください。
- LINE 通知はチャネルアクセストークンとユーザー ID が必要です。設定がない場合はログ出力のみになります。

---

## 参考コマンドまとめ

- 監視開始:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン開始:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードベースの主要点をまとめたものです。実際に運用する際は各モジュールのドキュメント（ソース内 docstring）・設定・テストをよく確認してください。必要であれば、各コンポーネント（ブローカー接続、ExecutionEngine の設定、RiskManager の閾値等）についての詳細ガイドを別途作成します。