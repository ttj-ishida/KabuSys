# KabuSys

KabuSys は日本株の自動売買システム向けユーティリティ群（ポートフォリオ構築、リサーチ、監視、Execution 起動 / リコンシリエーション、AI ニューススコアリング等）をまとめたコードベースです。本 README はこのリポジトリの主要コンポーネント、セットアップおよび使い方をまとめたものです。

---

## プロジェクト概要

- 日本株戦略のバックエンド処理（ファクター計算、特徴量解析、ポートフォリオ構築、ポジションサイズ算出）
- Execution 関連：注文管理、ブローカーインターフェース、起動時のリコンシリエーション
- 監視（Monitoring）：システム状態、注文滞留・約定異常、ドローダウン監視、LINE 通知、ダッシュボード（Streamlit）
- AI モジュール：ニュース記事のセンチメント評価 / 市場レジーム判定（OpenAI を利用）
- ユーティリティ：環境設定ローダー、プロセス優先度設定、簡易レポート生成ツール 等

設計上の特徴：
- DuckDB / SQLite をデータストアに利用（DuckDB は時系列ファクター計算・生データ、SQLite は監視ログ・orders 等）
- Paper Trading と Live は分離（paper_trading モードは専用 SQLite を使用）
- 外部 API 呼び出し（OpenAI 等）失敗時はフェイルセーフの挙動を優先

---

## 主な機能一覧

- 研究・リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- ポートフォリオ構築
  - シグナル選定（スコア順）、等配分・スコア加重配分
  - セクター集中制限、レジーム乗数適用
  - ポジションサイズ計算（risk-based / equal / score）、単元株丸め、利用可能現金に基づくスケール

- Execution（発注関連）
  - OrderManager: 注文作成・送信フロー、重複検知、2相永続化などのクラッシュ耐性
  - Reconciler: 起動時の注文・ポジション照合（ブローカーとの同期）

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数上限監視とリスクログ記録
  - KillSwitch: 条件に応じてデータ/ファイル経由で Execution の停止要求（data/kill.flag）
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）

- AI
  - news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF(1321) の MA とマクロニュースで日次の市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading 結果の検証レポート生成（稼働率、成功率、P95 レイテンシ等）

---

## 必要条件（例）

- Python 3.10+
- ローカル（または仮想環境）に以下のパッケージをインストール
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- OS: Linux / macOS / Windows（プロセス優先度や CPU affinity の一部は OS に依存）

requirements.txt がある場合はそれを使用してください。無ければ例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリに移動
   - 仮想環境の作成を推奨（venv / poetry など）

2. 依存関係をインストール
   - 例: pip install -r requirements.txt
   - （requirements.txt が無い場合は上記パッケージを個別インストール）

3. データディレクトリの作成（必要に応じて）
   - data/（デフォルトの SQLite・DuckDB の保存先）
   - 例: mkdir -p data

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードされます（既存 OS 環境変数を保護）
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. 重要な環境変数（主要なもののみ）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - paper_trading の場合、Execution はモックブローカーを使い DB を data/paper_trading.db に保存
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の成行執行モード（instant | partial | never | reject、デフォルト: instant）
   - PID_FILE_PATH: Execution の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API トークン（必須な場合あり）
   - OPENAI_API_KEY: OpenAI を使う AI 機能で必要
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を有効にする場合
   - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

   例（.env）:
   ```
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

---

## 使い方（主なコンポーネントの起動）

プロジェクトはパッケージとして配置されている想定です（src/ 配下に kabusys パッケージ）。

- Python パスを通す（パッケージ直下で）
  - 開発時: pip install -e .（setup があれば）または PYTHONPATH=src を使う

1. Monitoring（SystemMonitor のポーリングループ）
   - 起動:
     python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（例: 30）
   - 特徴:
     - Settings.env に関係なく監視用の本番 sqlite_path を使用
     - 起動時にプロセス優先度を "high" に設定しようとする（失敗しても継続）

2. Execution（ExecutionEngine）
   - 起動:
     python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に完全分離して記録されます
   - 起動時に PID ファイル（data/execution.pid）を作成し、プロセス優先度を high に設定

3. Streamlit ダッシュボード（監視 UI）
   - 起動:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で DB を開きます。MonitoringEngine を先に起動してデータを用意してください

4. Paper Trading 検証レポート
   - 実行:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（`--db` オプションで上書き可能）
   - 出力: 標準出力に検証サマリ（稼働率、注文成功率、P95 レイテンシなど）

5. AI モジュール（ニュース評価 / レジーム判定）
   - news_nlp.score_news / regime_detector.score_regime は OpenAI API キーが必要
   - 実行例（スクリプト化されている場合）:
     - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); score_news(conn, datetime.date(2026,4,10))"
   - OpenAI API 呼び出しは失敗時にフェイルセーフ（0.0 やスキップ）する設計

---

## 重要な挙動・注意点

- Paper Trading 分離
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと分離します。必ず paper_trading を使う際は設定を確認してください。

- MONITOR_POLL_INTERVAL
  - run_monitoring / MonitoringEngine のポーリング間隔を秒で指定できます（環境変数、デフォルト 60 秒）
  - 0 以下の値は無効としてデフォルトにフォールバックします

- PID / kill.flag
  - Execution は pid_file を書き込みます（デフォルト data/execution.pid）。SystemMonitor はこの PID ファイルを見てプロセス生存を検査します
  - KillSwitch は条件に応じて kill.flag（デフォルト data/kill.flag）を書き込み、Execution に停止要求を通知する方式です
  - 起動時に kill.flag を自動クリアしたい場合は Settings.kill_flag_clear_on_start を利用する（環境変数 KILL_FLAG_CLEAR_ON_START=1）

- OpenAI / API レート制限
  - AI モジュールはリトライとバックオフを実装していますが、API キーの使用量やレート制限に注意してください

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に対してカラム追加の簡単なマイグレーションを行います（例: trade_logs.latency_ms, dashboard.peak_value）

- ロギング
  - 各スクリプトは basicConfig(level=INFO) で起動します。必要に応じて環境変数 LOG_LEVEL を設定できます（Settings.log_level）

---

## 開発者向け: ディレクトリ構成（主要ファイル）

以下は src/kabusys 下の主要なファイル・パッケージ構成（抜粋）です。

- src/kabusys/
  - __init__.py (バージョンなど)
  - config.py (Settings, .env 自動ロード機能)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - data/ (データ処理関連モジュールは別ファイルに配置される想定)
  - portfolio/
    - portfolio_builder.py (候補選定、重み計算)
    - risk_adjustment.py (セクター上限、レジーム乗数)
    - position_sizing.py (株数決定・スケーリング)
    - __init__.py
  - research/
    - factor_research.py (momentum/value/volatility 計算)
    - feature_exploration.py (forward returns, IC, サマリ)
    - __init__.py
  - ai/
    - news_nlp.py (ニュースセンチメント -> ai_scores)
    - regime_detector.py (市場レジーム判定)
    - __init__.py
  - monitoring/
    - monitoring_db.py (SQLite 永続化層)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (orders DB 操作、別ファイル)
    - broker_factory.py (ブローカークライアント生成)
    - execution_engine.py (Engine 実装、別ファイル)
    - その他 execution 関連モジュール
  - utils/
    - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)
    - __init__.py

（上記はリポジトリ内の代表的なファイルを抜粋した一覧です。詳細な実装は各ファイルを参照してください。）

---

## よくある運用例（例: systemd / サービス化）

- run_execution と run_monitoring をそれぞれ systemd サービスとして登録して常時稼働させる運用が想定されます。
- 実運用では KABUSYS_ENV を `live` に、ログレベルや PID、kill flag のパス設定を確認してください。
- Paper Trading テストは別環境（KABUSYS_ENV=paper_trading）で実施し、本番 DB と一切共有しないようにしてください。

---

## 補足 / 開発上の注意

- DuckDB を用いたファクター計算はデータ量に応じてメモリ・IO を消費します。性能チューニングは必要に応じて行ってください。
- OpenAI を使う箇所は API レスポンスのバリデーションを強化しており、部分失敗時の安全性を重視していますが、出力の妥当性確認は運用側でも行ってください。
- unit test を追加する際は、外部 API 呼び出し部分（OpenAI、requests、psutil）を mock する設計になっています。

---

必要であれば次の内容も追加できます：
- systemd のユニットファイル例
- より詳細な .env.example（全環境変数一覧）
- データスキーマ（DuckDB のテーブル、raw_news / prices_daily 等の詳細）
- 開発用テストコマンド / CI 設定例

どの追加情報が欲しいか教えてください。