# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はプロジェクトの概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・検証・監視を目的とした Python 製のモジュール群です。主要コンポーネントは以下です。

- ExecutionEngine: ブローカーとの発注・注文状態管理・リスク管理・リコンシリエーション
- Monitoring: システム稼働状況、注文の滞留・約定異常、ドローダウンなどの監視
- Portfolio construction: 候補選定、重み算出、ポジションサイズ決定、セクター制約・レジーム調整
- Research: ファクター計算・特徴量探索（DuckDB 経由で過去価格データを解析）
- AI: OpenAI を利用したニュースセンチメント集計（ニュース NLP）・市場レジーム判定
- Tools: Paper Trading の検証レポート生成、Streamlit ダッシュボードなど

設計上の特徴：
- DuckDB / SQLite をデータ層として利用
- 本番・ペーパートレードを分離（ペーパーは別 SQLite）
- 環境変数または .env(.local) 経由で設定を注入（自動ロード機能あり）
- OpenAI API を利用する機能は API キーが必須

---

## 主な機能一覧

- 実行系 (run_execution.py)
  - ブローカークライアントの抽象化（本番 / Mock）
  - リスク管理 (RiskManager)
  - OrderManager による発注ライフサイクル管理
  - 起動時リコンシリエーション（Reconciler）

- 監視系 (run_monitoring.py / monitoring package)
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態/データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の検出とログ記録
  - KillSwitch：リスクトリガーにより停止フラグ（kill.flag）を書き込み
  - AlertManager：LINE によるプッシュ通知（トークン・ユーザーID 必要）
  - Streamlit ダッシュボード（監視 DB の可視化）

- ポートフォリオ (portfolio)
  - 候補選定、スコア/等分配の重み計算
  - セクター制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数計算（calc_position_sizes） — リスクベース / 等分配 / スコア 加重

- リサーチ (research)
  - モメンタム / ボラティリティ / バリュー ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI（OpenAI）
  - ニュース記事のセンチメント評価を銘柄毎に集計して ai_scores テーブルへ書き込み
  - マクロニュースを使った市場レジーム判定（regime_detector）

- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ（psutil を使用）
  - monitoring DB の初期化 / マイグレーション（監視用 SQLite）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

---

## セットアップ手順（開発環境向け）

想定：プロジェクトルートに `src/` 配置。Python 3.10+ を想定（PEP604 の union 型を使用）。

1. リポジトリをクローン（省略）
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（代表例）
   - pip install duckdb psutil requests openai streamlit
   - 実際の requirements はプロジェクトの配布に合わせて調整してください。

4. 環境変数 / .env の用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（抜粋）：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - KABUSYS_ENV = development | paper_trading | live  （デフォルト: development）
     - PAPER_FILL_MODE = instant | partial | never | reject  （デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH（例: data/execution.pid）
     - KILL_FLAG_PATH（例: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループ間隔 秒、デフォルト 60）
     - LOG_LEVEL（DEBUG / INFO / ...）

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な実行例）

注意：パッケージをインストールしていない場合、プロジェクトルートから `PYTHONPATH=src` を指定するか `pip install -e .` などでパッケージ化してください。

- 実行エンジンを起動（本番 / ペーパートレード共通起動スクリプト）
  - python -m kabusys.run_execution
  - ペーパートレードで起動する場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - ペーパートレード時は MockBrokerClient を使い、データは `PAPER_TRADING_SQLITE_PATH`（既定: data/paper_trading.db）へ記録され、本番 DB と分離されます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は常に Settings が示す本番 sqlite_path を使って monitoring 用テーブルを初期化します（`init_monitoring_db`）。

- 停止・制御
  - Execution/Monitoring スクリプトはプロジェクトの `data/stop_requested.flag`（run scripts の定義によりパスは変わる）を検知すると安全に終了します。
  - KillSwitch（監視→Execution の自動停止）は `data/kill.flag` を書き込み、Execution 側で停止フラグ等に用いることができます。
  - Execution は起動時に PID を `data/execution.pid` に書く設計（PID ファイルの整合性を SystemMonitor がチェックします）。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit 監視ダッシュボード（ローカル表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取りモードで開くため、MonitoringEngine が書き込んでいる状態で参照してください。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で渡す）。
  - AI モジュールの関数例:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - モデルやリトライロジック、バッチサイズ等はモジュール内定数で調整されています。

---

## 設定と挙動に関する重要な点

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
  - OS 環境変数は保護され、`.env` の値はデフォルトとしてのみ適用されます。`.env.local` は override=True なので OS env にないキーは上書きできます。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- DB の分離:
  - 監視用テーブルは Settings.sqlite_path（デフォルト: data/monitoring.db）に作成されます。
  - ペーパートレードは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離されます。
  - DuckDB は主にリサーチ用途で使用（`DUCKDB_PATH` デフォルト: data/kabusys.duckdb）。

- ログレベル・プロセス優先度:
  - 起動スクリプトは最初にプロセス優先度を `high` に変更しようとします（OS に依存、失敗時は警告）。
  - ログレベルは `LOG_LEVEL` 環境変数で調整可能。

- 安全対策:
  - API 呼び出し（OpenAI など）はリトライ・バックオフが実装されており、フェイルセーフとして失敗時はスコア 0.0 を用いる、またはスキップする設計です。
  - Monitoring の結果から KillSwitch が作動するとフラグファイルを書き、Execution 側に停止を促します。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主要なファイル・モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env の読み込みと Settings クラス
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP（OpenAI）によるセンチメント算出
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite 監視 DB 初期化＋読み書きラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Broker / Engine / OrderRepository 等の実装ファイル)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py

その他: DuckDB / SQLite を使うための SQL スキーマやマイグレーションロジックは `monitoring_db.py` 等に実装されています。

---

## 参考・運用上の注意

- 本リポジトリ内のスクリプトはローカルや検証用の実装が混ざっています。実際にブローカー接続を行う前に設定・権限・リスクパラメータを十分に確認してください。
- OpenAI を用いる機能は API 利用料が発生します。バッチサイズ・リトライは設定済ですが、運用時はコストとレート制限に留意してください。
- PID ファイルやフラグファイル（data/*.pid, data/stop_requested.flag, data/kill.flag）を外部運用ツールと併用する場合、パスや権限に注意してください。
- DuckDB / SQLite のファイルパスはデフォルトで `data/` 配下にあります。バックアップ・ローテーションを検討してください。

---

この README はコードベースの現状（主要ファイル）から自動的にまとめたものです。詳細な API 仕様や Engine の起動オプション、Broker 実装などは該当モジュールのドキュメント／ソースコメントを参照してください。必要であれば特定機能（例: ExecutionEngine の起動フロー、OrderRepository のスキーマ、AI モジュールの入出力仕様）に関する詳細なドキュメントを追加作成します。