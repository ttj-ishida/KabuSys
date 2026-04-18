# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
本プロジェクトはシステム監視、注文実行エンジン、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）等のコンポーネントを含む自動売買フレームワークです。

## プロジェクト概要
- 目的: 日本株の自動売買を行うためのモジュール群（実行エンジン、監視、リスク管理、ポートフォリオ構築、ファクター計算、AIベースのニューススコアリング等）。
- 設計方針:
  - モジュール分割（監視 / 実行 / ポートフォリオ / リサーチ / AI / utils）。
  - 環境変数 / `.env` による設定管理。
  - DuckDB / SQLite を使用したデータ処理・永続化。
  - Paper Trading（模擬発注）と Live（本番）を環境で切替可能。
  - フェイルセーフ設計（API失敗や部分失敗を許容して継続する処理が多数）。

## 主な機能（機能一覧）
- 実行エンジン (ExecutionEngine)
  - ブローカークライアント経由で発注・注文管理
  - リスク管理（ポジション上限、ドローダウン等）
  - ペーパートレード用に本番 DB と分離
- 監視（Monitoring）
  - システム状態（CPU/Mem/Disk）、データ鮮度、プロセス生存確認
  - トレードログ、リスクログ、ダッシュボード永続化（SQLite）
  - Kill Switch（条件に応じて停止フラグを書き込み Execution を停止）
  - MonitoringEngine によるポーリング運転
- ポートフォリオ構築
  - 候補選定、等比率・スコア比率の重み計算
  - セクター上限適用、レジーム乗数
  - 発注株数（単元）算出、available cash によるスケール調整
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB から計算
  - 将来リターン計算、IC（Information Coefficient）等
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコア化（ai_scores テーブルへ）
  - ETF（1321）MA とマクロニュースを組み合わせた市場レジーム判定（market_regime への書き込み）
  - 再試行、レスポンスバリデーション、スコアのクリップ等の堅牢化を実装
- ツール
  - 環境設定ウィザード：`.env` の対話的生成（kabusys.config_setup）
  - 設定検証 CLI：環境変数・config YAML ファイルの事前検証（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

## 必要環境・依存
- Python 3.9+
- 必須（機能により必要）パッケージ:
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML — config/*.yaml のパース検証時に使用
- SQLite は標準ライブラリで利用
- ネットワーク接続：kabuステーション API / J-Quants / OpenAI を利用する場合

（プロジェクト配布時に `requirements.txt` があればそれを使用してください。なければ上記パッケージを pip でインストールしてください。）

例:
```
pip install duckdb psutil openai PyYAML
```

## セットアップ手順
1. リポジトリをチェックアウト / クローン
2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. `.env` の作成:
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` をプロジェクトルートに作成（`.env.example` を参考に）。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリとログディレクトリの確認/作成（`data/`, `logs/`）
   - デフォルトデータパス:
     - DuckDB: `data/kabusys.duckdb`（env: `DUCKDB_PATH`）
     - SQLite (monitoring): `data/monitoring.db`（env: `SQLITE_PATH`）
     - Paper Trading SQLite: `data/paper_trading.db`（env: `PAPER_TRADING_SQLITE_PATH`）
   - ログ: `logs/<app>.log`（環境変数 `LOG_DIR` / `LOG_LEVEL` で制御）

注意: 実行環境によりプロセス優先度変更（set_process_priority）や CPU affinity 設定は権限が必要です。

## 環境変数（主要）
- 認証系:
  - `JQUANTS_REFRESH_TOKEN`（必須）
  - `KABU_API_PASSWORD`（必須）
  - `OPENAI_API_KEY`（AI 機能利用時）
- 実行環境切替:
  - `KABUSYS_ENV` = `development` | `paper_trading` | `live`（デフォルト: `development`）
- DB / ファイルパス:
  - `DUCKDB_PATH`（デフォルト `data/kabusys.duckdb`）
  - `SQLITE_PATH`（デフォルト `data/monitoring.db`）
  - `PAPER_TRADING_SQLITE_PATH`（paper_trading 用 DB、デフォルト `data/paper_trading.db`）
  - `PID_FILE_PATH`, `KILL_FLAG_PATH` など監視関連
- ログ:
  - `LOG_LEVEL`（`INFO` デフォルト）
  - `LOG_DIR`（`logs/` デフォルト）
- その他:
  - `MONITOR_POLL_INTERVAL`（監視ループの秒間隔、デフォルト 60）
  - `PAPER_FILL_MODE`（`instant` | `partial` | `never` | `reject`）
  - `KILL_FLAG_CLEAR_ON_START`（`0` or `1`）
  - `CPU_THRESHOLD_PCT`, `MEMORY_THRESHOLD_PCT`, `DISK_THRESHOLD_PCT`（監視閾値）

## 使い方（起動コマンド例）
- 環境ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine の起動（本番 or paper_trading は KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - Paper trading 時は `KABUSYS_ENV=paper_trading` を設定してください。ペーパートレードは MockBrokerClient を使用し、`data/paper_trading.db` に記録します。

- SystemMonitor（監視ループ）の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔をオーバーライドする場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルトDBパスは `data/paper_trading.db`。`--db` で別パス指定可能。

- AI 機能（ライブラリ呼び出し）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: DuckDB 接続, target_date: datetime.date, api_key: str|None
    score_news(duckdb_conn, target_date, api_key=None)
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)
    ```

- 注意: 実行スクリプトは `setup_logging()` を呼び出してログを統一的に管理します。ログファイルは `logs/<app>.log` に日次ローテーションで出力されます。

## 運用上の注意
- Kill Switch:
  - `data/kill.flag` を作成すると ExecutionEngine に停止シグナルを送ります。Kill flag のクリアは `KILL_FLAG_CLEAR_ON_START` 等の設定を確認してください。
- PID / Stop フラグ:
  - `data/execution.pid` や `data/stop_requested.flag` などのフラグファイルを監視してプロセス制御を行います。
- 権限:
  - プロセス優先度 / CPU affinity の設定は OS 権限が必要になる場合があります。設定に失敗した場合は警告を出してスキップします。
- 本番運用:
  - `KABUSYS_ENV=live` の場合は LINE 通知設定や kill_flag の扱い etc. を十分に確認してください。`validate_config` が追加の警告を出します。

## ディレクトリ構成
主要ファイル・ディレクトリを抜粋して説明します（`src/kabusys` をパッケージルートとする構成）。

- kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / Settings 管理、自動ロード（.env / .env.local）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - execution/  — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — （注文状況監視）※該当ファイルはコードベースで実装済み想定
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各モニタを束ねる実行ループ
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — （通知管理、LINE等、実装想定）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数算出・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ （ランタイムで作成）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - execution.pid / kill.flag / stop_requested.flag などの制御ファイル
  - logs/ （ログ出力先、デフォルト）

（上記は主要ファイルを抜粋したもので、実際のリポジトリにはさらにモジュール群が存在します。）

## 開発・デバッグ
- 単体機能のテストや関数呼び出しはモジュール単位で行えます（例: research.calc_momentum、portfolio.calc_position_sizes 等は DuckDB / Python の接続を渡して実行可能）。
- モジュールは副作用を最小化する設計ですが、DB 書き込みを伴う関数は適切なテスト DB を用意してください（paper_trading 用 DB 等）。
- AI 呼び出し部分は外部 API への依存があるため、ユニットテスト時は `_call_openai_api` をモックしてテストしてください。

## よくある質問 / トラブルシュート（簡易）
- 「.env が読み込まれない」
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` が設定されていないか確認。プロジェクトルートの特定に失敗すると自動ロードはスキップされます。
- 「監視ループが起動しない／即停止する」
  - `data/stop_requested.flag` が存在する場合、監視・実行は起動しません。該当ファイルを確認してください。
- 「OpenAI を呼べない」
  - `OPENAI_API_KEY` を設定し、ネットワークアクセスが可能か確認してください。API のレート制限やエラーはリトライ設計がありますが、キー未設定は例外になります。

---

この README はコードベースの主要点をまとめたものです。各モジュールの詳細な API やパラメータ、実装ノートは該当ソースファイル内の docstring とコメントを参照してください。必要であれば、追加の利用例や運用手順（systemd / supervisor によるプロセス管理、Docker 化等）も追記します。