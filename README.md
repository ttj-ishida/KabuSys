# KabuSys

日本株向けの自動売買システム（軽量プロトタイプ）。  
戦略の研究・ファクター計算、ポートフォリオ構築、注文実行（本番／ペーパートレード切替）、および稼働監視・アラート・Kill Switch を含むモジュール群で構成されています。

## 概要
- DuckDB / SQLite をデータ格納に利用し、取引ロジックと監視ロジックを分離して実装しています。
- 環境切替（development / paper_trading / live）によりペーパートレード用 DB を分離可能。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／レジーム判定機能を備えています（API キー必須）。
- psutil を使ったプロセス優先度設定、監視、ログ保管機能を提供します。

## 主な機能
- 環境設定ウィザード（.env の対話的生成）: `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml のチェック）: `python -m kabusys.validate_config`
- ExecutionEngine：注文実行の起動（paper_trading では MockBroker を使用）
- MonitoringEngine：システム状態・注文状態・リスク監視と Kill Switch 評価
- Portfolio コンポーネント：銘柄選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- Research：ファクター計算（Momentum, Volatility, Value 等）、IC 計算、特徴量解析
- AI モジュール：ニュース NLP による銘柄センチメント（ai.news_nlp）、市場レジーム判定（ai.regime_detector）
- ツール：Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- 監視ログ永続化（SQLite）用ユーティリティ（monitoring_db.py）

## 必要条件（例）
- Python 3.9+（ソースは型注釈で分岐あり。3.10 以上を推奨）
- pip パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
  - そのほかプロジェクト仕様に応じて追加パッケージ

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそれを使用してください）

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 用）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

.env の作成はウィザード（config_setup）を使うと簡単です。

## セットアップ手順（簡易）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. .env を生成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力してください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要に応じて data ディレクトリを作成
   ```
   mkdir -p data
   ```

6. 実行前に kill.flag の自動クリア設定に注意（本番では KILL_FLAG_CLEAR_ON_START=0 推奨）。

## 使い方（主要コマンド）
- ExecutionEngine（発注エンジン）起動
  - 本番 / 開発 / ペーパーは KABUSYS_ENV で切替
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 起動時に data/execution.pid に PID が書かれます。停止は kill.flag を作成するか data/stop_requested.flag を作成して監視プロセスに検知させることができます（実装上 stop flag は stop_requested.flag を参照）。

- Monitoring（監視ループ）起動
  ```
  # ポーリング間隔を環境変数で上書き可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は本番 sqlite_path を使って監視データを書き込みます（環境に依存せず監視 DB は同じ本番パスを使用する実装になっています）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼び出し）
  - ニューススコアリング（例: DuckDB 接続と日付を渡して実行）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  ```
  - レジーム判定（同様に）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  ```

- 設定検証/ウィザード
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

## Kill Switch / 停止フロー
- Kill Switch（監視が重大リスクを検出した場合）:
  - data/kill.flag に理由を記載して書き込むことで ExecutionEngine 側で停止シグナルとして検出できます。
  - KillSwitch は冪等（既に存在する場合は上書きしない）。
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが止まります（スクリプト内でチェック）。

## ディレクトリ構成（主要ファイル）
以下はリポジトリ内の主要モジュールと役割の概観です（この README に含まれるソース群に基づく抜粋）：

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン情報
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 対応）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - monitoring/
    - monitoring_db.py — SQLite 用永続化レイヤ（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
    - trade_monitor.py — 注文滞留・異常約定監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag の作成・評価
    - monitoring_engine.py — 各 Monitor を束ねる実行ロジック
    - alert_manager.py — （アラート送信管理: 実装の詳細はソース参照）

  - execution/  (存在を示唆するモジュール。一部参照)
    - execution_engine.py — 発注エンジン本体（起動 / stop / run_session）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py — 発注関連ロジック

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金割当・lot 単位処理
    - risk_adjustment.py — セクターキャップ / レジーム乗数

  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

  - ai/
    - news_nlp.py — raw_news を LLM に投げて銘柄別センチメント算出
    - regime_detector.py — MA200 と LLM マクロセンチメントを合成して日次レジーム判定

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - process_priority.py — psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ

## 開発・デバッグのヒント
- DB 初期化: 監視用 SQLite は init_monitoring_db() によりテーブル自動作成されます。起動時に自動で作成されるため手動マイグレーションは不要です（ただし config/*.yaml の雛形生成は scripts 参照）。
- ログ: Settings.log_level で制御。logging.basicConfig による INFO レベルがデフォルトで設定されます。
- テスト: MonitoringEngine.run_once() を使うと単発で各モニタを呼べるためユニットテストや手動確認に便利です。

---

何か特定の実行方法（Docker 化、systemd のユニットファイル、CI 設定、詳細な依存関係ファイル作成など）を README に追記したい場合は、用途に応じたテンプレートを作成します。どの部分を拡張しますか？