# KabuSys

日本株自動売買システム（KabuSys）の簡易ドキュメント。  
このリポジトリはシグナル→発注→監視→検証までの主要コンポーネント群を含みます。以下はコードベースから抜粋した使い方・セットアップ情報です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を行うためのシステムです。主な責務は以下のとおりです。

- シグナルに基づく発注（Execution Engine）
- 発注状態・約定の自動リコンシリエーション
- 実行中システムの稼働監視（Monitoring）
- リスク監視（ドローダウン・ポジション上限等）
- Paper Trading 用の分離環境（モックブローカー）
- 研究・ファクター計算、特徴量探索モジュール
- ニュースの NLP による銘柄別センチメント評価（OpenAI API）
- 検証レポート生成ツール（Paper Trading 向け）
- Streamlit による監視ダッシュボード

設計方針の一部：
- 本番 DB と Paper Trading DB は明確に分離
- ルックアヘッドバイアスを避ける実装（日時参照の扱い）
- フェイルセーフ（API失敗時は安全にフォールバック）

---

## 主な機能一覧

- Execution
  - 発注 API 抽象化（BrokerFactory）
  - OrderManager / OrderRepository による状態管理
  - Reconciler による再起動時の自動復旧
  - RiskManager によるポジション・利用率制限
- Monitoring
  - SystemMonitor：CPU/Memory/Disk、プロセス生存チェック、データ鮮度
  - TradeMonitor：滞留注文、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：閾値超過時に停止フラグを生成して Execution を停止
  - AlertManager：LINE Push を使った通知（クールダウンあり）
  - Streamlit ダッシュボード（監視表示）
- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索、IC 計算、forward returns
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- AI ツール
  - news_nlp: OpenAI を用いたニュースセンチメント集計・ai_scores への書き込み
  - regime_detector: ma200 とマクロニュースを合成して市場レジーム判定
- Utilities
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - 環境変数ローダー（.env / .env.local の自動読み込み）

---

## 必要条件 / 依存パッケージ

最低限の依存（抜粋）：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）
- sqlite3（標準ライブラリ）

例（venv を作った後）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際の requirements.txt は本リポジトリに含まれていないため、運用環境では pip freeze 等で依存を固定してください）

---

## セットアップ手順

1. リポジトリをクローン／配置する。
2. Python 仮想環境を作成して依存パッケージをインストール。
3. 環境変数を設定する（下記参照）。プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
4. データディレクトリを作成（必要に応じて）:
   mkdir -p data
5. SQLite / DuckDB のデータファイルは初回起動時にテーブル作成処理が走ります（monitoring 用テーブル等）。

---

## 環境変数（主要設定）

（.env に記載する想定のキーと既定値／説明）

- KABUSYS_ENV
  - 値: development / paper_trading / live
  - 動作モード。paper_trading の場合は MockBroker を使い、Paper 用 DB に書き込む。
- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用トークン（必須）
- KABU_API_PASSWORD
  - kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY
  - OpenAI を使う機能（news_nlp / regime_detector）で使用
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager 用。未設定時は送信をスキップ
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db（monitoring 用）
- PAPER_TRADING_SQLITE_PATH
  - デフォルト: data/paper_trading.db（paper_trading モード専用）
- PAPER_FILL_MODE
  - Paper Trading の注文約定挙動: instant / partial / never / reject（デフォルト: instant）
- PID_FILE_PATH
  - 実行エンジン PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH
  - KillSwitch が書き込むフラグパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒、デフォルト: 60）。1未満や不正値はデフォルトにフォールバック。
- LOG_LEVEL
  - DEBUG/INFO/…（デフォルト INFO）
- CPU/MEM/DISK の閾値:
  - CPU_THRESHOLD_PCT（デフォルト 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト 85.0）
  - DISK_THRESHOLD_PCT（デフォルト 90.0）

注意: Settings モジュールで未設定の必須キー（例: JQUANTS_REFRESH_TOKEN）を参照すると例外が出ます。

---

## 使い方（起動・実行）

基本的な実行コマンドの例を示します。いずれも仮想環境をアクティベートした状態で実行してください。

- Execution Engine（取引実行）
  - モード: 本番 / paper_trading は環境変数 KABUSYS_ENV で切替
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - ポイント:
    - paper_trading: settings.is_paper が True のときは MockBroker を用い、PAPER_TRADING_SQLITE_PATH に書き込む
    - 起動時に data/stop_requested.flag が存在すると起動せず終了する
    - 実行中は PID を data/execution.pid に書き込み（設定により変更可）

- Monitoring（監視ループ）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - オプション:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 備考:
    - 監視は常に（KABUSYS_ENV に関係なく）本番用 sqlite_path を使用するよう実装されています
    - 停止は data/stop_requested.flag を作成することで安全にループを抜けられます

- Streamlit ダッシュボード
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - GUI でポジション・オーダー・最近の監視ログを確認できます

- Paper Trading 検証レポート生成
  - 起動:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスは `--db` もしくは環境変数 `PAPER_TRADING_SQLITE_PATH` を使用

- AI スコアリング / レジーム判定（ライブラリ関数呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(duckdb_conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、テーブルを書き換えます。OpenAI API キーが必要です。

---

## 停止方法 / フラグ

- 安全に停止したいときはプロジェクトルートの data/stop_requested.flag ファイルを作成してください。run_execution.py と run_monitoring.py はこのファイルを検知して順次シャットダウンします。
- Execution 停止のための KillSwitch（自動停止）は monitoring 側で `data/kill.flag` を書きます。kill.flag があると起動時にエンジンは起動しない等の保護が働きます。
- pid ファイルは `data/execution.pid`（デフォルト）に出力されます。stale PID ファイルは SystemMonitor により検出・削除され、risk event として記録されます。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（各種設定プロパティ）
  - run_execution.py
    - ExecutionEngine の起動スクリプト（paper_trading 分離）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py: ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py: 市場レジーム判定
  - monitoring/
    - monitoring_db.py: SQLite を用いた監視ログ永続化
    - system_monitor.py: CPU/メモリ/ディスク・プロセス・データ鮮度監視
    - trade_monitor.py: 注文滞留・約定異常検出
    - risk_monitor.py: ドローダウン / ポジション上限監視
    - kill_switch.py: kill.flag 操作ユーティリティ
    - alert_manager.py: LINE 通知
    - monitoring_engine.py: 各モニタの統合実行ループ
    - streamlit_dashboard.py: Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ...（発注・同期・リコンシリエーション関連）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
  - research/
    - factor_research.py, feature_exploration.py（ファクター計算・解析）
  - tools/
    - paper_verification_report.py（Paper Trading の検証レポート生成ツール）
  - utils/
    - process_priority.py（プロセス優先度 / CPU affinity 設定ユーティリティ）
  - data/ （実行時に使用するファイル群）
    - monitoring.db（デフォルトの監視 SQLite DB）
    - paper_trading.db（paper_trading 用 DB）
    - kabusys.duckdb（DuckDB ファイル）
    - execution.pid / kill.flag / stop_requested.flag など

---

## 運用上の注意

- Paper Trading と本番 DB は完全に分離されるよう実装されていますが、設定ミスにより上書きする可能性があるため .env の設定は慎重に管理してください。
- OpenAI API を使う機能は API キーと外部通信に依存します。失敗時のフォールバックロジックはあるものの、利用時はレート制限やコストに注意してください。
- SystemMonitor は監視対象プロセスの PID ファイルを参照し、プロセスの生存確認や stale PID の自動削除を行います。PID ファイル周りの権限・配置には注意してください。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存（psutil による実装）です。権限不足で例外が出る場合はログに警告が出ます。

---

## 追加情報 / 開発者向け

- Settings はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テーブルのスキーマ変更（マイグレーション）は monitoring_db.init_monitoring_db() 内で簡易的に扱っています（列追加等）。
- テストやモックの差し替え用に API 呼び出し部分（OpenAI の呼び出しなど）は内部関数を patch しやすい設計になっています（ユニットテスト時にモック可能）。

---

README の内容はコードベースからの抜粋に基づく概説です。実際のデプロイ・本番運用時はセキュリティ（API キー管理）、依存パッケージのバージョン固定、ログ集約・監査など追加の運用設計を行ってください。必要ならこの README を踏まえて運用手順書（Runbook）や .env.example を作成するサポートも行います。