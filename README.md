# KabuSys

KabuSys は日本株の自動売買システム（リサーチ、ポートフォリオ構築、発注、監視、AI 補助機能を含む）です。本リポジトリには、コアロジック、監視・アラート機能、ペーパートレード向けの分離 DB、ニュース NLP / レジーム判定などのユーティリティが含まれます。

---

## 概要

- 自動売買エンジン（ExecutionEngine）による注文発行・状態管理
- 監視コンポーネント（System / Trade / Risk Monitor）とキルスイッチ（kill.flag）
- DuckDB を使ったリサーチ（ファクター計算、フォワードリターン、特徴量探索）
- OpenAI を用いたニュースのセンチメント付与（news_nlp）と市場レジーム判定（regime_detector）
- ペーパートレード用の分離 DB とレポート生成ツール
- Streamlit による監視ダッシュボード

---

## 主な機能一覧

- 実行（run_execution.py）
  - KABUSYS_ENV により paper_trading / live 動作を切替
  - BrokerClientFactory で実際のブローカーまたはモックを選択
  - RiskManager, OrderManager, Reconciler を組み合わせてセッションを実行
- 監視（run_monitoring.py / MonitoringEngine）
  - CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - 注文滞留・約定異常価格の検出
  - ドローダウン／ポジション上限の検出と kill.flag 書き込み
  - LINE による通知（AlertManager）
  - SQLite に監視ログを永続化（monitoring_db）
- ペーパートレード検証ツール（tools.paper_verification_report）
  - 稼働率・注文成功率・送信率・レイテンシなどのレポート出力
- リサーチ（research）
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials からファクターを算出
  - feature_exploration：将来リターン、IC、統計サマリーなど
- ポートフォリオ構築（portfolio）
  - 候補選定、等重／スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ算出
- AI（ai）
  - news_nlp.score_news：OpenAI でニュースをスコアリングして ai_scores に書込
  - regime_detector.score_regime：ETF MA とマクロニュースから市場レジーム判定

---

## 必要条件（想定）

- Python 3.9+
- 主要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（LINE / OpenAI / ブローカー API を利用する場合）

※ requirements.txt はリポジトリに含まれていない場合があるため、上のライブラリを pip でインストールしてください。

例:
```
pip install duckdb psutil requests streamlit openai
```

---

## 環境変数（主なもの）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須／重要な環境変数（主なもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に必要）
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` の場合、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE — paper trading の約定挙動: `instant`|`partial`|`never`|`reject`（デフォルト: instant）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）  
  ※ run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。デフォルト: 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知に利用

監視しきい値（任意環境変数で上書き可）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil requests streamlit openai
   ```

2. .env ファイルを作成
   - リポジトリの `.env.example`（存在する場合）を参照して `.env` を作成してください。
   - 例:
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     ```

3. データディレクトリ作成
   ```
   mkdir -p data
   ```

4. DuckDB / SQLite の初期化
   - 監視(DB スキーマ) は run_monitoring または run_execution 起動時に自動作成されます（init_monitoring_db が冪等でテーブル・インデックスを作成します）。
   - DuckDB に prices_daily / raw_financials 等のテーブルを用意する場合は外部スクリプトで投入してください（本 README ではデータロード手順は省略）。

---

## 使い方（代表的な起動方法）

- 監視ループを起動（PID 優先度を high に設定し、SQLite にログを保存）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - 環境をペーパートレードに切り替える:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    - paper_trading の場合は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に発注ログを記録し、本番 DB と分離されます。
    - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます。

- Streamlit ダッシュボード（監視データの可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パスを指定できます。指定がない場合は環境変数 `PAPER_TRADING_SQLITE_PATH` → `data/paper_trading.db` を参照します。

- AI 関連（ニューススコア／レジーム判定）をプログラムから呼び出す
  - OpenAI API キーが必要です（OPENAI_API_KEY または関数引数）。
  - 例: news_nlp.score_news / regime_detector.score_regime を呼び出して DuckDB 接続を渡します（詳細はモジュール内 docstring を参照）。

---

## 重要な挙動ノート

- Settings（kabusys.config）は自動で .env をロードしますが、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト用途など）。
- run_monitoring は監視用 DB 接続に常に本番の `sqlite_path` を使います（KABUSYS_ENV に関係なく）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、paper 用 SQLite を使用して本番 DB と分離します。
- kill.flag による停止シグナル:
  - RiskMonitor / KillSwitch が条件を満たすと `KILL_FLAG_PATH` に原因テキストを書き込みます。ExecutionEngine はこのフラグを検出して安全停止できます。
- プロセス優先度設定:
  - 起動スクリプトは最初に set_process_priority("high") を呼び、psutil を通じて OS に依存した優先度設定を試みます。権限不足などで失敗した場合は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイルの概要）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定の読み込み・検証
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコア化して ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定と書き込み
  - monitoring/
    - monitoring_db.py — SQLite スキーマ定義と永続化 API（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン、ポジション上限の監視
    - kill_switch.py — kill.flag 管理ロジック
    - alert_manager.py — LINE による通知送信
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, ... — 発注・同期ロジック（部分実装あり）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC・統計サマリ関数
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 開発・拡張のヒント

- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, など）を充実させることで、リサーチ・AI 機能が有効になります。
- OpenAI の呼び出し周りはリトライやバリデーションを慎重に実装しているため、テスト時は該当関数をモックすることを推奨します（コード内に patch 指示あり）。
- monitoring_db.init_monitoring_db は冪等にテーブルとインデックスを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）も実装しています。

---

## ライセンス / 責務

- この README はコードベースの説明を目的としています。実運用に当たっては各 API（ブローカー、OpenAI、LINE 等）の利用規約に従い、適切な権限・制約の下で実行してください。
- 本システムを実運用する際は十分なテスト、障害対策、監査ログ、資金管理ルールを整備してください。

---

追加で README に含めたい内容（例: 詳細なデータロード手順、requirements.txt、CI 設定、テスト実行法）があれば教えてください。必要に応じて追記・テンプレート化します。