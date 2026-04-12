# KabuSys

日本株向けの自動売買・リサーチ基盤のコアライブラリ群と起動スクリプト群です。本リポジトリは発注（Execution）、監視（Monitoring）、リサーチ（Research）、AI 補助（News NLP / Regime Detector）、ポートフォリオ構築ロジック等を含みます。

---

## 概要

- 自動発注エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）を中心とした構成。
- DuckDB / SQLite を用いた時系列・メタデータの集計・永続化。
- Paper Trading モードをサポート（本番 DB と分離された専用 SQLite を利用）。
- ニュース記事を LLM（OpenAI）でセンチメント化する AI モジュールと、それを用いた市場レジーム判定。
- Streamlit ベースの監視ダッシュボード、監視ログの永続化、アラート（LINE）送信機能。
- ポートフォリオ構築、ポジションサイジング、リスク制御の純粋関数群（ユニットテストが容易）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution）
  - ブローカ抽象化（BrokerClientFactory）に応じた実行（paper_trading は MockBrokerClient）
  - OrderManager / Reconciler による注文ライフサイクル管理・再同期
  - リスクマネジメント（RiskManager）設定

- Monitoring
  - SystemMonitor：プロセス稼働、CPU/メモリ/ディスク、データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視
  - KillSwitch：フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager：LINE によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only）

- Research / Feature
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - news_nlp: raw_news -> OpenAI による銘柄別センチメントのスコア化（ai_scores への書込み）
  - regime_detector: ETF MA とマクロニュースの LLM センチメントを合成して日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading ログから稼働率・注文成功率・レイテンシ等を集計してレポート生成

---

## 動作要件

- Python 3.9+
- 推奨ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite は標準ライブラリで利用
- ネットワーク接続（OpenAI / LINE を使う場合）

※ requirements.txt は本コードには同梱していませんが、上記パッケージを仮想環境にインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン／配置。
2. 仮想環境を作成して依存パッケージをインストール（上記参照）。
3. データディレクトリを作成：
   ```
   mkdir -p data
   ```
4. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH 等
   - .env の自動読み込みはデフォルトで有効。無効化する場合は環境変数:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DB 初期化
   - 多くの起動スクリプトが初回起動時に監視テーブルを自動作成します（init_monitoring_db を呼ぶ）。
   - 明示的に初期化したい場合は Python REPL から:
     ```
     from kabusys.config import Settings
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     s = Settings()
     conn = sqlite3.connect(str(s.sqlite_path))
     init_monitoring_db(conn)
     conn.close()
     ```

---

## 使い方（主要な起動方法）

- 監視ループ（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）。
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 監視は Settings.sqlite_path に対して常に本番 sqlite を使用（環境に依らず）。

- 実行エンジン（Execution）
  - Paper Trading の場合は KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```

- Streamlit ダッシュボード（監視 UI）
  - 実行例（read-only モードで監視 DB を開く）:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ストリームリット起動引数 --db で DB パスを指定可能。

- Paper Trading 検証レポート
  - 使用例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション `--db PATH` で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI / レジーム判定（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI キーは引数または環境変数 OPENAI_API_KEY。
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも DuckDB 接続（kabusys.config.Settings.duckdb_path）を渡して使用します。
  - 例（対話的に）:
    ```
    import duckdb, os
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, date(2026, 4, 10), api_key=os.environ.get('OPENAI_API_KEY'))
    ```

---

## 重要な挙動・注意点

- 設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある .env / .env.local を自動で読み込みます（OS 環境変数を上書きしない既定の挙動。`.env.local` は上書き可）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- Paper Trading と本番 DB は分離されます（run_execution が KABUSYS_ENV を見て sqlite_path を切り替え）。

- OpenAI 呼び出し:
  - rate limit (429)・ネットワーク断・タイムアウト・5xx は再試行ロジックあり。
  - レスポンスのバリデーションを行い、不正な結果はスキップしてフェイルセーフに振る舞います。

- モニタリング DB のスキーマ変更（マイグレーション）は起動時に簡単な ALTER TABLE を行います（例: latency_ms, peak_value カラム追加）。

- プロセス優先度設定:
  - 起動時に set_process_priority("high") を呼んでプロセス優先度を上げようとします。プラットフォームによる差分吸収とアクセス権のハンドリングあり。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- execution/
  - order_manager.py, reconciler.py, ... — 発注・再同期・OrderRecord 等（Execution 系）
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化層（init / CRUD）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限チェック
  - kill_switch.py — kill.flag による停止シグナル
  - alert_manager.py — LINE Push API 経由の通知（クールダウン管理）
  - monitoring_engine.py — 上記 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け（等配分・スコア加重）
  - position_sizing.py — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — raw_news -> OpenAI による銘柄別センチメント取得 / ai_scores 書込
  - regime_detector.py — MA200 + マクロニュースによる日次レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- data 関連
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - Monitoring SQLite: data/monitoring.db（デフォルト）
  - Paper trading SQLite: data/paper_trading.db（paper_trading 用）

---

## 開発メモ / テスト時のヒント

- 多くのモジュールは純粋関数または DuckDB/SQLite の接続を引数に取る設計のため、モックや in-memory DB を使った単体テストがしやすいです（例: duckdb.connect(":memory:")）。
- OpenAI 呼び出し部分はラッパー関数を用意しており、テスト時は該当関数をパッチしてレスポンスを制御できます（module のコメント参照）。
- .env のロードロジックはプロジェクトルート探索式のため、パッケージ配布後も動作する設計です。テスト時に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。

---

## ライセンス / 貢献

本 README にはライセンス情報は含まれていません。実際のプロジェクトで利用する場合は適切な LICENSE ファイルを追加してください。バグレポートや機能提案は issue を通してお願いします。

---

README はここまでです。必要に応じて、実行コマンドの具体例や .env.example のテンプレートを追加できます。どの情報をより詳しく書きたいか教えてください。