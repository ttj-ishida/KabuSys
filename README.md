# KabuSys

日本株自動売買システムの軽量ライブラリ群・起動スクリプト群の一式です。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）・Kill Switch、ポートフォリオ構築、ファクター計算、AI ベースのニュースセンチメント評価など、アルゴリズム売買に必要なコンポーネント群を含みます。

バージョン: 0.1.0

---

## 概要

主な役割・コンポーネント
- ExecutionEngine（実際の発注ロジック、paper_trading モードでのモックブローカー対応）
- Monitoring（System / Trade / Risk モニタリング、Kill Switch、アラート）
- Portfolio（銘柄選定、重み計算、ポジションサイズ決定）
- Research（ファクター計算、将来リターン、IC 計算など）
- AI モジュール（ニュース NLP によるセンチメント算出、レジーム検出）
- ユーティリティ（設定読み込み・ウィザード、ログ設定、プロセス優先度設定）
- ツール（Paper Trading 検証レポート生成スクリプト等）

設計方針の一部
- 環境変数・.env による設定管理（自動読み込み、テスト用に無効化可能）
- DuckDB / SQLite をデータ永続化に併用（分析用に DuckDB、監視・発注ログに SQLite）
- 本番/ペーパーは DB を分離（paper_trading は data/paper_trading.db）
- LLM (OpenAI) を利用する機能は API エラーに対して耐性を持つ（リトライやフェイルセーフ）

---

## 機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading.db に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可（デフォルト 60 秒）
  - Monitoring は常に sqlite_path（本番用）を参照
- Monitoring サブコンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス存在チェック
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常等）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 指定閾値超過時に data/kill.flag を書き込みエンジンを停止
  - MonitoringDB: SQLite にテーブル作成・読み書き（冪等）
- Portfolio: 候補選定、等配分・スコア加重、ポジションサイズ算出、セクターキャップ、レジーム乗数
- Research: Momentum / Volatility / Value のファクター計算、将来リターン・IC・統計要約
- AI:
  - news_nlp.score_news: ニュースを集約し OpenAI (gpt-4o-mini) により銘柄ごとにスコアを算出して ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF の MA200 とマクロニュースの LLM 評価を合成して市場レジームを判定・保存
- ツール:
  - paper_verification_report: Paper Trading の検証レポートを生成

---

## 前提 / 必要ライブラリ

推奨 Python バージョン: 3.10+

主要依存（抜粋）
- duckdb
- psutil
- openai
- PyYAML（設定ファイルの検証を行う場合に必要）
- （標準ライブラリ: sqlite3 等）

インストール例（仮想環境を推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
実プロジェクトでは requirements.txt または poetry/pip-tools を用意してください。

---

## セットアップ手順

1. リポジトリを取得して仮想環境を作成・有効化する
2. 依存パッケージをインストール（上記参照）
3. .env の作成
   - 対話式ウィザードを使用:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で .env を作成（例は下部の「環境変数」参照）
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります
5. 必要に応じてデータディレクトリを作成（logs/ や data/ はログ生成時に自動作成されることがありますが、権限等に注意してください）

注意:
- 自動で .env を読み込む処理はデフォルトで有効です（プロジェクトルートに .env / .env.local がある場合）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主要なもの）

（キー — 説明 — デフォルト）

- KABUSYS_ENV — 実行環境。development | paper_trading | live — default: development
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API ベース URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — DuckDB ファイルパス — default: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB (SQLite) — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite — default: data/paper_trading.db
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject） — default: instant
- LOG_LEVEL — ログレベル（DEBUG/INFO/...） — default: INFO
- LOG_DIR — ログ出力ディレクトリ — default: logs/
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（本番なら 0 推奨） — default: 0
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒） — default: 60

その他: Settings クラス（kabusys.config.Settings）で利用可能なプロパティを参照してください。

.env 例（簡易）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxx
```

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を上書きする場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
  - 実行中に data/stop_requested.flag が作られると安全に停止を試みます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で別の DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使えます。

- プログラムから個別 API を呼ぶ例（REPL / スクリプト内）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date は datetime.date
  score_news(conn, target_date, api_key="sk-...")
  ```

ログ設定は各起動スクリプトで setup_logging(app_name=...) を呼んでおり、logs/<app_name>.log に日次ローテーションで出力されます（デフォルト 30 日保持）。

---

## 運用上のメモ

- Kill Switch:
  - RiskMonitor が閾値超過を検出すると KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して安全停止します。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にして自動クリアを避けることを推奨します。
- PID / Stop フラグ:
  - 実行用 PID ファイル: data/execution.pid（run_execution が利用）
  - 停止リクエスト: data/stop_requested.flag（手動で作成して監視ループ／エンジンを停止）
- 監視 DB:
  - monitoring_db.init_monitoring_db が必要テーブルを冪等に作成します
  - monitoring は常に sqlite_path（本番）を参照します（環境にかかわらず）
- Paper Trading:
  - paper_trading モード時、発注はモック化され DB は paper_trading_db に保存され本番 DB と分離されます

---

## ディレクトリ構成（抜粋・主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数読み込み・Settings クラス（.env 自動読込機能含む）
- config_setup.py — .env 対話式ウィザード CLI
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリングループ起動スクリプト

package モジュール群
- ai/
  - news_nlp.py — ニュースセンチメント算出（OpenAI 使用）
  - regime_detector.py — 市場レジーム判定（MA200 とマクロニュースを合成）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル定義/操作）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文ログ監視（ファイル内にロジックあり）
  - risk_monitor.py — ドローダウン・ポジション監視
  - monitoring_engine.py — 各 Monitor を束ねる実行ロジック
  - kill_switch.py — kill.flag の書込ロジック
  - alert_manager.py — （アラート通知管理。コード参照）
- execution/
  - execution_engine.py — ExecutionEngine（発注セッションの起動/停止）
  - broker_factory.py — ブローカークライアント生成（本番 / mock）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注関連
- portfolio/
  - portfolio_builder.py — 候補選定・スコア基準
  - position_sizing.py — 株数決定・資金割当
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 等ファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py — 統一ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

data/（実行時に作成されることが多い）
- data/monitoring.db — デフォルト監視 DB
- data/paper_trading.db — Paper Trading 用 DB（paper_trading モード）
- data/kabusys.duckdb — デフォルト DuckDB（分析用）
- data/kill.flag, data/stop_requested.flag, data/execution.pid — 運用フラグ / PID

logs/
- execution.log, monitoring.log ... — 日次ローテートされるログファイル

---

## 例: 起動フロー（ローカルテスト）

1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の初期テーブルは起動時に自動作成されます
4. 監視を起動（別ターミナル）:
   ```
   python -m kabusys.run_monitoring
   ```
5. 実行エンジンを起動:
   ```
   python -m kabusys.run_execution
   ```
6. 異常時に kill.flag が生成されると ExecutionEngine 側で安全停止を行います

---

## 開発・拡張ノート

- settings（kabusys.config.Settings）を通して型付きで環境値にアクセスできます。必要に応じて Settings を拡張してください。
- AI モジュールは OpenAI の利用を前提としており、API キーの管理に注意してください（.env に記載しない運用や Vault の利用を推奨）。
- DuckDB / SQLite スキーマはコード内に定義済み。DB スキーマ変更時はマイグレーションを検討してください（簡単な ALTER は monitoring_db が一部対応）。
- テスト: 各モジュールは純粋関数化されている部分が多く、ユニットテストを書きやすい設計です。API 呼び出し部分は patch / mock で差し替え可能。

---

この README はコードベースの主要な使い方・構成を概説したものです。詳細は各モジュールの docstring / ソースコード内コメントを参照してください。必要であれば README に「デプロイ手順」「監視ダッシュボード」や「詳細な DB スキーマ」などの追加セクションを追記できます。