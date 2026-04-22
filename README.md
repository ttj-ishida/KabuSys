# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築・発注実行・監視・調査・AI（ニュース）モジュールなどを含むモジュール群です。

---

## 概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- 戦略（ファクター計算・特徴量探索）とポートフォリオ構築
- 発注実行エンジン（本番／ペーパートレード対応）
- システム監視・リスク監視・Kill Switch（フラグで ExecutionEngine 停止）
- DuckDB を用いた分析データ層、SQLite を用いた監視・トレードログ保存
- OpenAI を用いたニュースセンチメント分析及び市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定 等）
- CLI/ユーティリティ：.env ウィザード、設定検証、ペーパートレード検証レポート

---

## 主な機能一覧

- ExecutionEngine 起動／管理（run_execution.py）
  - KABUSYS_ENV に応じて本番／ペーパートレード（MockBroker）を切替
  - 発注履歴（trade_logs）・ポジション（positions）等を SQLite に記録
  - PID ファイル管理、停止フラグ監視（data/stop_requested.flag）

- Monitoring（run_monitoring.py / monitoring_engine）
  - システムリソース、データ鮮度、発注状態、リスク指標を定期監視
  - KillSwitch による自動停止フラグ書き込み（data/kill.flag）
  - 通知マネージャ（AlertManager）への通知フック

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重／スコア加重、リスク調整（セクター上限・レジーム乗数）
  - 株数決定・単元株丸め・投下資金スケーリング

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（kabusys.ai）
  - news_nlp: OpenAI を使ったニュースセンチメント解析（ai_scores テーブルへ書込）
  - regime_detector: MA200乖離 + マクロニュースで市場レジーム判定し DB へ永続化

- ツール
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

- ユーティリティ
  - ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity（utils/process_priority.py）
  - 環境設定読み込み（config.py）

---

## 前提 / 必要要件

- Python 3.9+
- 推奨インストールパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定 YAML 検証を行う場合）
- データディレクトリ（デフォルト）:
  - data/kabusys.duckdb（DuckDB）
  - data/monitoring.db（監視 SQLite）
  - data/paper_trading.db（ペーパートレード用 SQLite, KABUSYS_ENV=paper_trading 時に使用）
  - logs/（ログ出力先）

例（pip）:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. レポジトリをクローン / ソースを準備。

2. Python 環境を用意して依存パッケージをインストール（上記参照）。

3. デフォルトのデータ／ログディレクトリ作成（実行時に自動作成される場合あり）:
```bash
mkdir -p data logs
```

4. 環境変数設定（.env を作成する方法は次節を参照）:
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレ用 DB)
     - LOG_LEVEL, LOG_DIR
     - OPENAI_API_KEY（AI モジュール使用時）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

5. .env の作成（対話式ウィザード推奨）:
```bash
python -m kabusys.config_setup
```

6. 設定を検証:
```bash
python -m kabusys.validate_config       # 警告は許容
python -m kabusys.validate_config --strict  # 警告もエラー扱い
```

---

## 使い方

- ExecutionEngine（発注エンジン）起動
  - デフォルトで KABUSYS_ENV によって本番/ペーパートレードを切替えます。
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止:
    - 管理用の停止フラグファイルを作成すると（data/stop_requested.flag）エンジンは安全に停止します。
    - Kill Switch（monitoring により作成される data/kill.flag）も ExecutionEngine を停止させます。

- Monitoring（監視）起動
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数で上書き可能:
    ```bash
    export MONITOR_POLL_INTERVAL=30  # 秒
    python -m kabusys.run_monitoring
    ```
  - 監視は常に production の sqlite_path（デフォルト data/monitoring.db）を使用します。

- ペーパートレード検証レポート
  - 既に記録されたペーパートレード用 SQLite DB（デフォルト: data/paper_trading.db）からレポートを作成:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB を明示する場合:
    ```bash
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- AI（ニューススコアリング / レジーム判定）をプログラムから使う
  - 例: ai.score_news を呼ぶ
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - regime_detector:
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

- リサーチ / ポートフォリオ関数（ライブラリ利用）
  - DuckDB 接続を作成し、research や portfolio の関数を直接呼び出せます。
    - 例: calc_momentum / calc_volatility / calc_value
    - 例: select_candidates, calc_score_weights, calc_position_sizes

---

## 環境変数一覧（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / ロギング:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR

- DB / ファイルパス:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (execution.pid のパス)
  - KILL_FLAG_PATH (kill.flag のパス)
  - KILL_FLAG_CLEAR_ON_START (0/1)

- AI:
  - OPENAI_API_KEY

- Monitoring:
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - MONITOR_POLL_INTERVAL（run_monitoring の起動時に環境変数で上書き可能）

詳細は kabusys/config.py と kabusys/validate_config.py を参照してください（自動 .env ロード機能あり）。

---

## ログ / ディレクトリ

- デフォルトログディレクトリ: logs/
  - ログファイルは <app_name>.log（日次ローテート）として出力されます。
  - setup_logging() で LOG_DIR / LOG_LEVEL を上書き可能。

- データディレクトリ: data/
  - stop/kill フラグ: data/stop_requested.flag, data/kill.flag
  - PID ファイル: data/execution.pid（ExecutionEngine 起動時に書き込み）

---

## トラブルシューティング / 運用メモ

- Stop / Kill の仕組み
  - 手動停止: data/stop_requested.flag を作成すると run_execution/run_monitoring のループは検知して終了します。
  - 自動停止: Monitoring の KillSwitch が data/kill.flag を書くと ExecutionEngine に停止シグナルを送ります。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は既存 DB に対して冪等にテーブルを作成し、必要なカラムを追加する簡易マイグレーションを実装しています。

- 権限や OS 固有の制約
  - process_priority の設定は OS により成功しない場合があります（権限不足や未対応 OS）。その場合は警告を出してスキップします。

- OpenAI 呼び出し
  - ネットワークエラーや 429/5xx はリトライ実装がありますが、API キーや料金設定を確認してください。
  - AI モジュールは API キーの未設定時に例外を投げます（明示的に api_key を渡すか OPENAI_API_KEY を設定してください）。

---

## ディレクトリ構成（主要ファイル説明）

（src/kabusys 以下の抜粋）

- __init__.py
  - パッケージ情報（バージョン等）

- run_execution.py
  - ExecutionEngine 起動スクリプト。スレッドでエンジンを起動し停止フラグを監視。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。

- config.py
  - 環境変数の読み込み・提供（Settings クラス）。.env 自動読み込み機能あり。

- config_setup.py
  - 対話式 .env ウィザード（python -m kabusys.config_setup）。

- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）。

- monitoring/
  - monitoring_db.py — SQLite によるログ永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / プロセス監視
  - trade_monitor.py — （トレード関連の監視ロジック）
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各モニタを統合する実行ループ
  - alert_manager.py — 通知マネージャ（LINE 等へ送る実装のフック想定）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注・リスク制御・リコンシリエーションの実装

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み付け・株数算出・セクター制限・レジーム乗数

- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py — ニュースのセンチメント解析（OpenAI 呼び出し・バッチ・リトライ・検証）
  - regime_detector.py — MA200 乖離 + マクロニュースを使ったレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定

---

## 開発者向けメモ

- DuckDB は分析専用。research / ai の多くの関数は DuckDB 接続を受け取り SQL / Python 混在で計算します。
- DB 書き込み処理はトランザクション（BEGIN / COMMIT / ROLLBACK）を使用している箇所があり、例外時の取り扱いに注意してください。
- AI モジュールはテスト容易性のため API 呼び出し関数を差し替え可能（ユニットテスト時は patch しやすい設計）。
- 設定ファイル（config/*.yaml）や PyYAML は任意。validate_config は YAML の存在・パースをチェックします（PyYAML 未インストール時は警告）。

---

必要に応じて README に追記します。特に「実行例」「依存関係の厳密なバージョン」「各コンポーネントの詳細な API 使用例」を追加したい場合は教えてください。