# KabuSys

KabuSys は日本株自動売買システムのコンポーネント群です。本リポジトリはトレーディング実行エンジン、監視（Monitoring）、ポートフォリオ構築・リスク制御、リサーチ/ファクター計算、そしてニュース NLP（OpenAI）を含む補助ツール群を提供します。

以下の README はコードベース（src/kabusys）に基づく概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 目的: 日本株の自動売買に必要な実行・監視・リスク管理・ポートフォリオ構築・リサーチ機能をモジュール化して提供する。
- 特徴:
  - ExecutionEngine と監視（MonitoringEngine）は別プロセスで動作し、監視が Execution を監視・停止できる Kill Switch を備える。
  - Paper Trading モード（完全分離された SQLite DB を使用）により実取引とは独立して検証可能。
  - DuckDB を利用したファクター計算 / リサーチ機能（prices_daily / raw_financials ベース）。
  - ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp）、およびレジーム判定（regime_detector）。
  - Streamlit を用いた監視ダッシュボード。
  - ロギング、DB マイグレーション（軽微なカラム追加）を備えた堅牢な設計。

---

## 主な機能一覧

- 実行関連
  - 起動スクリプト: run_execution.py（ExecutionEngine 起動）
  - ブローカー抽象化: BrokerClientFactory（本番/モック切替）
  - 注文管理: OrderManager / OrderRepository / Reconciler（再起動時の自動リコンシリエーション）
  - リスク管理: RiskManager（発注前チェック等）

- 監視関連
  - 起動スクリプト: run_monitoring.py（SystemMonitor のポーリングループ）
  - SystemMonitor: CPU / メモリ / ディスク / PID の監視、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き ExecutionEngine 停止
  - AlertManager: LINE Messaging API への通知（クールダウン機能）
  - MonitoringDB: SQLite を使った監視ログ永続化・マイグレーション

- ポートフォリオ構築
  - 候補選定・重み付け（等分配 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（リスクベース / ウェイトベース）・単元株丸め

- リサーチ / ファクター
  - momentum / volatility / value ファクター計算（DuckDB 上で SQL 実行）
  - forward returns / IC / 統計サマリ等のユーティリティ

- AI / ニュース
  - news_nlp: OpenAI (gpt-4o-mini) でニュースを銘柄別にセンチメント評価して ai_scores に書き込み
  - regime_detector: ETF (1321) の MA とマクロニュースセンチメントを合成して market_regime を更新

- ツール
  - paper_verification_report: Paper Trading 用の検証レポートを生成
  - streamlit_dashboard: Monitoring DB を可視化するダッシュボード

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（型アノテーションの仕様に対応）
- git / pyproject.toml のあるプロジェクトルート構造を想定

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   以下は主要依存の例です（プロジェクトに requirements.txt / pyproject があればそちらを利用してください）。
   ```
   pip install duckdb openai psutil requests streamlit
   ```
   - duckdb: リサーチ・AI処理用 DB
   - openai: news_nlp / regime_detector
   - psutil: プロセス優先度・システムモニタ
   - requests: LINE API 通信
   - streamlit: ダッシュボード

4. data ディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```
   ※ デフォルトの DB パスや PID/flag ファイルは data/*. になります。

5. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。例:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-xxxx
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   PAPER_FILL_MODE=instant
   ```
   主な環境変数（Settings 参照）:
   - KABUSYS_ENV: development | paper_trading | live
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用
   - KABU_API_PASSWORD: kabuステーション API 用
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用
   - PAPER_FILL_MODE: instant | partial | never | reject
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）

6. （任意）KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテスト時に自動読み込みを無効化できます。

---

## 使い方（主要コマンド）

- 監視ループを起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存せず）。
  - 停止: data/stop_requested.flag を作成するとループが終了します。

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 専用 DB（paper_sqlite_path）に記録します（本番 DB と完全分離）。
  - 実行中は data/execution.pid に PID が書かれます。停止は data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が作成されると停止処理が行われます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  オプション:
  - --from YYYY-MM-DD, --to YYYY-MM-DD
  - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

- Streamlit ダッシュボード（監視 DB の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB が存在しない/読み取り不可の場合はエラーメッセージが出ます。

- AI 関連（プログラムから呼び出す形）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。
  - モデルは gpt-4o-mini（コード内定義）を利用します。API 呼び出しはリトライ・フェイルセーフ実装あり。

---

## 実行に関する注意点 / 運用メモ

- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると、実行エンジンは MockBrokerClient を使用し、paper_sqlite_path（デフォルト data/paper_trading.db）にデータを保存します。本番データベースとは分離されます。

- フラグ / PID ファイル:
  - 停止リクエスト: data/stop_requested.flag を作成すると run_monitoring / run_execution のループは検知して終了します。
  - ExecutionEngine 停止条件（KillSwitch）が成立すると data/kill.flag が作成され、次回起動時や運用者に停止理由を知らせます。
  - PID ファイル: data/execution.pid（ExecutionEngine 起動時に書き込まれ、SystemMonitor がプロセスの存否チェックに使用）

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存 DB に不足カラム（例: latency_ms, peak_value）があれば自動で追加するロジックを持ちます。

- OpenAI の使用:
  - API 呼び出しはレート制限や 5xx エラーに対して指数バックオフでリトライしますが、API キーやコスト管理は運用者の責任です。
  - news_nlp と regime_detector はモデル出力の JSON 構造を期待します。レスポンスのバリデーションを行い、不正な応答はスキップしてフェイルセーフに動作します。

- 環境設定の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を検索）にある `.env` / `.env.local` を実行時に自動読み込みします。
  - OS 環境変数が優先され、.env.local は上書き、.env は未設定の値を補完します。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / Settings 管理（.env 自動読み込み含む）
  - run_monitoring.py         -- SystemMonitor のポーリング起動スクリプト
  - run_execution.py          -- ExecutionEngine の起動スクリプト
- src/kabusys/monitoring/
  - __init__.py
  - monitoring_db.py          -- SQLite の監視テーブル定義と MonitoringDB ラッパー
  - system_monitor.py         -- CPU/Memory/Disk/データ鮮度/PID チェック
  - trade_monitor.py          -- 注文滞留・約定異常チェック
  - risk_monitor.py           -- ドローダウン・ポジション上限監視
  - kill_switch.py            -- kill.flag 書き出しロジック
  - alert_manager.py          -- LINE 通知（クールダウン付き）
  - monitoring_engine.py      -- 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py    -- Streamlit ダッシュボード
- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py      (実装ファイルは抜粋により省略されている可能性あり)
  - broker_factory.py
  - broker_api.py
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- src/kabusys/tools/
  - paper_verification_report.py
  - __init__.py
- src/kabusys/utils/
  - process_priority.py
  - __init__.py

data/ 以下（実行時に作成／利用）
- data/kabusys.duckdb          -- DuckDB（デフォルト）
- data/monitoring.db           -- 監視 SQLite（デフォルト）
- data/paper_trading.db        -- Paper Trading 用 SQLite（paper_trading 時）
- data/execution.pid           -- ExecutionEngine の PID
- data/stop_requested.flag     -- 手動停止フラグ（作成するとループを終了）
- data/kill.flag               -- KillSwitch が書き込む停止理由フラグ

---

## サンプル .env（最小例）

```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
PAPER_FILL_MODE=instant
```

---

## テスト / デバッグに関する補足

- Settings モジュールは自動で .env をロードしますが、ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制すると良いです。
- news_nlp / regime_detector の OpenAI 呼び出しは内部で呼び出し関数を抽象化しており、ユニットテストではモック可能です（コード内に patch を想定したコメントあり）。
- MonitoringEngine.run_once() を利用すると単回のみの監視サイクルを実行できるためテストに便利です。

---

この README はコードベース（src/kabusys）から抜粋して作成しています。実際の運用時は pyproject.toml / requirements.txt を用いて依存管理を行い、API キーや運用パラメータは安全に管理してください。必要があれば運用手順書（手動停止手順、バックアップ、ログローテーション、監視アラート条件のチューニング等）を別途作成することを推奨します。