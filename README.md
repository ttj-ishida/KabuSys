# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ + 実行スクリプト群）。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 要件（依存関係）
- セットアップ手順
- 環境変数（主要なもの）
- 使い方（コマンドとオプション）
- 動作上の注意点
- ディレクトリ構成（主要ファイル一覧）

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたパッケージです。  
主な役割は以下の通りです。

- 発注エンジン（ExecutionEngine）および注文管理
- 監視（System / Trade / Risk）と Kill Switch（異常時にエンジンを停止）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 計算）
- AI（ニュースセンチメント、レジーム検出）による情報付与
- ペーパートレード用分離データベースと検証レポート生成ツール

設計方針として、ルックアヘッドバイアスを避ける実装、DB を用いた永続化、AI 呼び出しのリトライ/フォールバックを備えています。

---

## 主な機能（抜粋）

- Execution
  - 実際のブローカー／Mock ブローカー切替（KABUSYS_ENV=paper_trading）
  - リスク管理（利用率・ドローダウン等）
  - 注文履歴の永続化（SQLite）
- Monitoring
  - CPU/メモリ/ディスク・プロセス生存チェック
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視
  - Kill Switch（data/kill.flag）による安全停止
- Portfolio
  - 候補選定（スコア/順位）
  - 等金額・スコア重み・リスクベースのポジションサイズ算出
  - セクター上限・レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（スピアマンランク相関）計算、統計サマリー
- AI
  - ニュースのセンチメントスコアリング（OpenAI を利用）
  - マクロニュース + ETF MA による市場レジーム推定
- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール

---

## 要件（依存関係）

最低限必要なパッケージ（例）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の構文チェックを行う場合に任意で必要）
- sqlite3（標準ライブラリ）

インストール例（仮の requirements）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

注: 実行時に必要なパッケージは用途（AI / YAML 検証など）によって変わります。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化し、必要なパッケージをインストール
3. 環境変数を設定
   - 対話式で .env を作成する:
     ```
     python -m kabusys.config_setup
     ```
   - または .env を手動で作成（.env.example を参照）
4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告もエラー扱いになります
5. データディレクトリや DB パスが指す親ディレクトリは自動生成されますが、権限等に注意してください。

---

## 環境変数（主要なもの）

（.env ファイルで管理できます、config_setup.py で作成可能）

必須（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

重要な設定
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）
- OPENAI_API_KEY — OpenAI を使う機能で必要（ai.news_nlp / ai.regime_detector）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

監視関連の挙動を調整する環境変数
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか 1/0（本番では 0 推奨）

その他の環境変数は config.Settings クラスのプロパティを参照してください。

---

## 使い方（主要 CLI / 実行例）

- .env を作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（実取引または paper_trading に応じて設定）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
  - 起動時にプロセス優先度を "high" に設定し、PID ファイルを生成します。
  - data/stop_requested.flag が存在すると起動せず終了します。
  - 停止は data/stop_requested.flag を作るか、Kill Switch（data/kill.flag）が付加されると実行側が停止処理を行います。

- Monitoring 起動（SystemMonitor 単体のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位でオーバーライド可能（デフォルト 60）
  - 監視処理は常に本番 sqlite_path を参照します（環境に関わらず）

- Paper Trading 検証レポート作成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼出す）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    count = score_news(duckdb_conn, target_date, api_key="...")  # 書き込み件数を返す
    ```
  - レジームスコア:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

- ライブラリ API（ポートフォリオ / リサーチ）
  - ポートフォリオ:
    ```
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```
  - リサーチ:
    ```
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    ```

---

## 動作上の注意点 / 実運用上の安全策

- paper_trading 環境は本番 DB と明確に分離されています（PAPER_TRADING_SQLITE_PATH）。
- 監視（monitoring）は環境に関係なく production の sqlite_path を参照する設計です（実運用での一貫した監視のため）。
- Kill Switch（data/kill.flag）は一度書かれると ExecutionEngine によって読み取られて停止されます。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（デフォルト 0 推奨）。
- OpenAI など外部 API は失敗時にフォールバック（スコア 0 等）する設計になっているため、AI の失敗で全体が停止することは基本的にありませんが、結果の妥当性は運用者が確認してください。
- set_process_priority: psutil を使ってプロセス優先度を上げます。権限がないと警告を出してスキップします。
- SQLite / DuckDB のファイルパスは .env で適切に設定し、バックアップ・排他制御に注意してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロードを含む）
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - execution/                      — 発注エンジン & ブローカー関連（実装本体）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconcilier.py
    - risk_manager.py
    - ...
  - monitoring/
    - monitoring_db.py             — SQLite スキーマ & ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/ (ランタイム生成)
    - kill.flag
    - execution.pid
    - monitoring.db / paper_trading.db など

---

README は以上です。実際の運用では .env の管理（絶対に Git にコミットしないこと）、DB のバックアップ、監視アラート受信設定（LINE 連携等）を必ず行ってください。必要であれば各モジュールの詳細な API 使用例や設定テンプレート（.env.example、config/*.yaml のサンプル）も作成できます。ご希望があれば追って追加します。