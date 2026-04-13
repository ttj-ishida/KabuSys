# KabuSys

日本株自動売買システム（軽量プロトタイプ）

このリポジトリは、株価データの分析・ファクター計算、ポートフォリオ構築、発注実行、監視（ログ・アラート・kill switch）、および研究用ユーティリティを含むモジュール群を提供します。実運用（live）とペーパートレード（paper_trading）を切り替えて動かせる設計になっています。

---

## 機能一覧

- Execution（発注エンジン）
  - Broker クライアント抽象化（本番 / Mock）
  - OrderManager による注文作成・送信・状態同期
  - Reconciler による起動時リコンシリエーション（注文・ポジション同期）
  - RiskManager によるリスク制御（最大ポジション比率、利用率、ドローダウン制限等）
- Monitoring（監視）
  - SystemMonitor: プロセス生存確認、CPU/メモリ/ディスク、データ鮮度チェック
  - TradeMonitor: 滞留注文検出、約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager: LINE への通知（クールダウンあり）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio（ポートフォリオ構築）
  - シグナル選定、等重・スコア重み、ポジションサイズ算出、セクターキャップ、レジーム乗数
- Research（研究用）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- AI（LLM連携）
  - ニュースのセンチメント解析（OpenAI API を利用）
  - マクロニュース + ETF MA 乖離を使った市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - その他ユーティリティ

---

## 必要条件 / 前提

- Python 3.9+
- pip でインストール可能な依存ライブラリ（後述）
- ローカルでのテスト実行には DuckDB / SQLite を利用（付属ライブラリで動作）
- OpenAI を利用する機能は OPENAI_API_KEY が必要
- LINE 通知は LINE チャネルアクセストークン / ユーザー ID を設定することで有効化

主要 Python パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

（プロジェクトに requirements.txt が無い場合は上のパッケージをインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主な設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` で指定できます。自動読み込みはデフォルトで有効（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（デフォルト値 / 説明）:

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（AI 機能）
- KABUSYS_ENV — 環境: `development` / `paper_trading` / `live`（デフォルト: development）
- PAPER_FILL_MODE — ペーパートレードの約定挙動: `instant` | `partial` | `never` | `reject`（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag の保存パス（デフォルト: data/kill.flag）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードの無効化（設定値 "1" で無効化）

例（.env）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
JQUANTS_REFRESH_TOKEN=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## セットアップ（初期化）

1. リポジトリをクローン
2. 仮想環境を作成して依存をインストール
3. 必要な環境変数を `.env` に設定
4. データディレクトリを作成（例: data/）
   - 監視 DB や PID ファイルがここに作られます
5. DuckDB / SQLite ファイルはスクリプト実行時に自動で必要テーブル作成やマイグレーション処理が行われます（monitoring 用テーブル等）

注意:
- ペーパートレード実行時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離します。
- 自動で .env を読み込む挙動を無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト用等）。

---

## 実行方法（主要なスクリプト）

- ExecutionEngine（注文実行）
  - 実行ファイル: `src/kabusys/run_execution.py`
  - 例（paper_trading）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番運用（live）では `KABUSYS_ENV=live` を設定します。
  - 注意: 実行時にプロセス優先度を "high" に設定します（psutil による試行）。

- Monitoring（監視ループ）
  - 実行ファイル: `src/kabusys/run_monitoring.py`
  - 例:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を上書きするには `MONITOR_POLL_INTERVAL` を設定（秒、デフォルト 60）。
  - 監視は monitoring/monitoring_db.py のテーブルを自動作成します（init_monitoring_db）。

- Streamlit ダッシュボード
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート
  - スクリプト: `src/kabusys/tools/paper_verification_report.py`
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB は `data/paper_trading.db`。別パスを指定する場合は `--db PATH` を使用するか環境変数 `PAPER_TRADING_SQLITE_PATH` を設定。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必須（OPENAI_API_KEY）
  - API 呼び出しでエラーが発生してもフォールバック処理を行う設計（フェイルセーフ）
  - 関数:
    - kabusys.ai.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)

---

## 注意事項 / 運用上のポイント

- Paper Trading と Live のデータベースは分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- run_execution/run_monitoring は起動時にプロセス優先度を上げようとしますが、権限不足や非対応 OS の場合は警告が出てスキップされます。
- kill.flag による停止シグナル: KillSwitch は path（Settings.kill_flag_path）にフラグファイルを書き込み、ExecutionEngine 側でこれを検知して安全終了します。
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒）を環境変数で上書きできます。不正な値（0 や負数、非整数）は無視され 60 秒にフォールバックします。
- .env の読み込み順序: OS 環境 > .env.local > .env。既に存在する OS 環境変数は保護されます。
- PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"（不正値は例外）
- OpenAI 呼び出しはレート制限や 5xx に対し指数バックオフでリトライしますが、最終的に失敗した場合はスキップして継続します（システム全体の堅牢性を重視）。

---

## ディレクトリ構成（要旨）

src/kabusys 以下の主なファイル・モジュール:

- __init__.py
  - パッケージ定義、バージョン
- config.py
  - 環境変数の自動ロード、Settings クラス（アプリ設定）
- run_execution.py
  - ExecutionEngine 起動スクリプト（本番/ペーパートレード対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - broker_factory.py, broker_api.py, ...（ブローカー抽象化）
  - execution_engine.py（エンジン本体）
  - order_manager.py（注文管理）
  - order_repository.py（注文DBアクセス）
  - reconciler.py（再起動時リコンシリエーション）
  - risk_manager.py（リスク管理）

- monitoring/
  - monitoring_db.py（SQLite 永続化層）
  - system_monitor.py（プロセス・データ鮮度監視）
  - trade_monitor.py（滞留注文・約定異常監視）
  - risk_monitor.py（ドローダウン・ポジション上限）
  - kill_switch.py（kill.flag 制御）
  - alert_manager.py（LINE 通知）
  - monitoring_engine.py（各 Monitor を束ねる）
  - streamlit_dashboard.py（監視ダッシュボード）

- portfolio/
  - portfolio_builder.py（候補選定・重み付け）
  - position_sizing.py（株数算出、単元丸め）
  - risk_adjustment.py（セクター制限・レジーム乗数）

- research/
  - factor_research.py（モメンタム/ボラティリティ/バリュー）
  - feature_exploration.py（将来リターン・IC・統計サマリ）

- ai/
  - news_nlp.py（ニュースの LLM センチメント）
  - regime_detector.py（市場レジーム判定）

- tools/
  - paper_verification_report.py（ペーパートレード検証レポート）

各モジュールは可能な限り純粋関数や明確な責務に分けられており、テストや差し替えがしやすい設計になっています（OpenAI 呼び出し部分などはテストでモックしやすいように分離されています）。

---

## 開発 / テストのヒント

- OpenAI の呼び出し部分は内部で関数を分離しているため、ユニットテストではモック化しやすくなっています（例: patch で _call_openai_api を置き換え）。
- .env の自動読み込みを無効化して、テスト用に明示的に環境を設定するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- ペーパートレードの検証を行う際は、paper_verification_report を使って主要指標（稼働率、注文成功率、P95 レイテンシ 等）を算出できます。

---

この README はコードベースの主要ポイントをまとめたものです。実際の運用前には設定ファイル（.env）を確認し、各 API（kabu API / J-Quants / OpenAI）や Broker の挙動を十分にテストしてください。