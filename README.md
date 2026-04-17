# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。  
本ドキュメントはコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な機能としては：

- 戦略からのシグナルに基づく注文生成・発注管理（ExecutionEngine）
- 注文状態のリコンシリエーション（再起動後の復旧処理）
- リスク管理（ドローダウン監視、ポジション上限など）と自動停止フラグ生成（Kill Switch）
- システム監視（CPU・メモリ・ディスク、データ鮮度、滞留注文や約定異常の検出）
- Paper Trading（モックブローカー）環境の分離（専用 DB）
- 研究用モジュール（ファクター計算・特徴量解析）
- ニュースを使った AI ベースのセンチメントスコアリング（OpenAI）
- Streamlit ベースの監視ダッシュボード

設計方針として「本番系と Paper Trading の分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しに対するフェイルセーフ」「DB の冪等初期化／マイグレーション」を重視しています。

---

## 主な機能一覧

- Execution（発注系）
  - OrderManager / ExecutionEngine / BrokerClientFactory
  - Reconciler：OrderSent 状態の再照合・ポジション差分検出
  - Paper Trading：KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し `data/paper_trading.db` に完全分離して記録

- Monitoring（監視系）
  - SystemMonitor：プロセス生存確認、CPU/Memory/Disk、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常チェック
  - RiskMonitor：ドローダウン・ポジション数監視
  - KillSwitch：条件到達時にファイルベースで停止シグナルを送出
  - AlertManager：LINE Messaging API での通知（クールダウン管理）
  - MonitoringEngine：各モニタを束ねて定期実行
  - monitoring_db：監視ログの永続化（SQLite）

- Research / Portfolio
  - factor_research：モメンタム／バリュー／ボラティリティ等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC 計算、統計サマリ
  - portfolio：候補選定、配分計算、リスク調整、ポジションサイズ計算

- AI
  - news_nlp：ニュース記事を OpenAI でセンチメント化し `ai_scores` に保存
  - regime_detector：ETF（1321）MA200 とマクロセンチメントを合成して市場レジーム判定（`market_regime` テーブルへ書込）

- ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成
  - monitoring/streamlit_dashboard.py：Streamlit ダッシュボード（監視表示）

---

## 必要な依存パッケージ（代表例）

開発・実行に必要な主要パッケージ（バージョンは適宜調整してください）：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (監視ダッシュボードを使う場合）
- sqlite3（標準ライブラリ）
- その他：logging 等標準ライブラリ

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

※ 実運用では requirements.txt を作成し固定バージョン管理を推奨します。

---

## 環境変数（代表的なもの）

Settings クラスで参照される主な環境変数（デフォルト値はコード内に記載）：

- KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabusapi ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら通知はスキップ）
- DUCKDB_PATH: duckdb ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject、デフォルト instant）
- PID_FILE_PATH: execution.pid ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で参照。デフォルト 60秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env ファイルの自動読み込み:
- プロジェクトルート（.git または pyproject.toml がある場所）を基準に `.env` と `.env.local` を自動読み込みします。
- OS 環境変数優先で `.env.local` が上書き、`.env` は上書きしません。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```
4. data ディレクトリを作成（実行時に自動作成されることもありますが手動で用意しておくと安全）
   ```
   mkdir -p data
   ```
5. 必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定するか `.env` を準備
   - 例: `.env` に以下を追加
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     JQUANTS_REFRESH_TOKEN=...
     ```
6. DuckDB / SQLite の初期化は起動スクリプトが行います（init_monitoring_db が冪等に作成）。

---

## 実行方法（代表的なコマンド）

- 監視プロセスを起動（monitoring）
  - デフォルトで production の sqlite_path（Settings.sqlite_path）を使用します（コードに注意: monitoring は環境にかかわらず本番 sqlite_path を使用）。
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で変更:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 実行エンジンを起動（ExecutionEngine）
  - Paper Trading モードで起動する例:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - Paper Trading 時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離されます。
  - 実行エンジンは `data/execution.pid` を作成し、停止フラグ（`data/stop_requested.flag`）や kill.flag（`data/kill.flag`）を監視します。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パス指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- Streamlit 監視ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI スコアリング / レジーム判定（ライブラリ API）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

---

## 停止 / フラグの扱い

- 停止リクエスト（すぐに安全停止）:
  - run_monitoring / run_execution はプロジェクトルートの `data/stop_requested.flag` の存在を検知して終了・停止します。
  - KillSwitch は `Settings.kill_flag_path`（デフォルト `data/kill.flag`）に理由テキストを書き込んで ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側はこれを検知して停止します）。
- PID 管理:
  - ExecutionEngine は `data/execution.pid` に PID を書きます。SystemMonitor は PID の存在と生存を検査し、stale PID を検出したら削除してリスクログを残します。

---

## 注意事項 / トラブルシューティング

- Process priority / CPU affinity:
  - set_process_priority() は psutil を使用し、OS と権限によりアクセス拒否されることがあります。失敗時は警告ログを出してスキップします。
- OpenAI API:
  - API キー（OPENAI_API_KEY）が必要です。news_nlp や regime_detector はリトライとフェイルセーフ（失敗時はデフォルト値にフォールバック）を組み込んでいますが、API 呼び出し失敗時はスコアリングが行われない場合があります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブル作成と簡単なマイグレーション（列追加）を実行します。既存データの破壊を避けるため冪等に作成しますが、本格的なマイグレーションには注意が必要です。
- .env パーサ:
  - .env のパースはシェル風のクォートやコメントを考慮した実装です。特殊ケースは注意。

---

## ディレクトリ構成（主要ファイルの一覧と説明）

- src/kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（Paper Trading に対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュース文章の OpenAI によるセンチメント集約（ai_scores 書込）
    - regime_detector.py — レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル定義とアクセスラッパー（MonitoringDB）
    - system_monitor.py — システム・データ鮮度監視（SystemMonitor）
    - trade_monitor.py — 注文滞留・約定異常検出（TradeMonitor）
    - risk_monitor.py — ドローダウン・ポジション上限監視（RiskMonitor）
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE への通知機能
    - streamlit_dashboard.py — Streamlit によるダッシュボード表示
  - execution/
    - reconciler.py — 再起動時のリコンシリエーション処理
    - order_manager.py — 注文作成・同期の上位 API（OrderManager）
    - （その他: broker_factory, execution_engine, order_repository, order_record 等 — 実行系コンポーネント）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数・丸め・キャップ処理
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/（ランタイム生成想定）
    - monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag など

（上記は代表的ファイルのみ抜粋しています。実際は execution 内にブローカー関連、order repository 等が含まれます。）

---

## 開発上のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化できます。
- DuckDB はデータ分析処理（ファクター計算、AI 用データ抽出など）に使われます。prices_daily / raw_financials / raw_news / news_symbols 等のテーブルが期待されます。
- Paper Trading は実運用 DB と完全に分離する設計になっています（`paper_sqlite_path` を使用）。実運用とは別の DB で検証してください。
- `monitoring_db.init_monitoring_db()` は冪等なので、最初の起動時に必ず通すことで必要テーブルを保証できます。

---

この README はコード状態（src/kabusys 配下）から自動的にまとめたものであり、実際の運用では追加ドキュメント（運用手順、監視ルールの具体値、broker クライアント設定、CI/CD、バックアップ運用など）を整備してください。必要なら既存モジュールごとの詳細ドキュメント（API 仕様、例）を追記します。