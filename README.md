# KabuSys

日本株自動売買システムの一部をまとめたコードベースの README（日本語）。

このリポジトリは、戦略・ポートフォリオ構築、発注/実行エンジン、監視、研究ツール、LLM ベースのニュース解析などを含むモジュール群を提供します。以下は使い方、セットアップ、主要コンポーネントの説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な目的は次のとおりです。

- ファクター計算（モメンタム、バリュー、ボラティリティ等）を DuckDB 上で実行する研究モジュール
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（発注・注文管理・リスク管理）の起動スクリプト
- Monitoring（システム状態、注文件数、ドローダウンなどの監視）と Kill Switch（条件到達で発注エンジン停止）
- News NLP（OpenAI を用いたニュースセンチメント評価）や市場レジーム判定
- 開発支援ツール（.env 作成ウィザード、設定検証、Paper Trading 検証レポート）

設計方針として、ルックアヘッドバイアスを避ける実装や、本番 DB とペーパートレード DB の分離、フェイルセーフ（API 失敗時はデフォルト動作で継続）を重視しています。

---

## 機能一覧（抜粋）

- 環境設定関連
  - 対話式 .env ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`（`--strict` あり）
- 実行／監視
  - ExecutionEngine 起動スクリプト: `run_execution.py`
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使い、別 DB に記録
  - Monitoring ポーリング起動スクリプト: `run_monitoring.py`
    - 環境に関係なく監視用 sqlite（本番 sqlite_path）を使用
  - Kill Switch（`data/kill.flag`）による発注エンジン停止機構
- ポートフォリオ系
  - 候補選定、等金額/スコア重み、リスク調整、ポジションサイズ計算
- 研究（research）
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI 関連
  - ニュースセンチメント評価（OpenAI 使用）: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定（MA + LLM 組合せ）: `kabusys.ai.regime_detector.score_regime`
- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 必要な依存パッケージ（例）

プロジェクトに明示的な requirements.txt はありませんが、本コードで使用している主要ライブラリは以下です。環境に応じてインストールしてください。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の構文チェックを行う場合に必要）
- （標準ライブラリ）sqlite3, logging, threading, datetime 等

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化し、依存パッケージをインストール（上記参照）
3. 初期 .env を作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV （development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - ※.env は決して Git にコミットしないでください
4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. 必要なら data ディレクトリや logs ディレクトリを作成（多くはコード側で自動作成されます）

---

## 基本的な使い方

- ExecutionEngine をローカルで起動する:
  - 通常実行（本番または development 設定に従う）:
    ```
    python -m kabusys.run_execution
    ```
  - 注意: `KABUSYS_ENV=paper_trading` のときは MockBroker を使い、`data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）へ記録されます。

- Monitoring を起動する（ポーリング）:
  ```
  # MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で調整可能（デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 停止制御:
    - プロジェクトルートの `data/stop_requested.flag` が存在すると、起動ループが終了します。
    - ExecutionEngine 側は `data/kill.flag` の存在で停止指示を受け取る設計です。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / LLM 機能（プログラムから呼び出し）
  - ニューススコア付与:
    ```py
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,4,20), api_key="sk-...")
    ```
  - 市場レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,20), api_key="sk-...")
    ```

- ログ設定
  - 各起動スクリプト内で `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼んで統一的なログ出力（標準出力 + 日次ローテーションファイル）を行います。
  - デフォルトログディレクトリ: `logs/`。環境変数 `LOG_DIR` または `log_dir` 引数で変更可能。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: execution モード。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = クリア, 0 = クリアしない）

開発時に自動で .env を読み込む挙動を無効にするには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 注意点・運用上のメモ

- Paper Trading と本番 DB は分離されています。`KABUSYS_ENV=paper_trading` を使うと専用 DB に記録されます（設定参照）。
- Monitoring（監視）は、run_monitoring により本番 sqlite_path を用いて動作します（環境に依らず本番 DB を参照する意図の箇所あり）。
- Kill Switch（`data/kill.flag`）は一度書かれると ExecutionEngine を停止させます。`KILL_FLAG_CLEAR_ON_START` を本番で 1 にするのは危険です（自動でクリアしてしまうため）。
- OpenAI を利用する処理は API 呼び出しに失敗した場合はフェイルセーフでスコア 0 や未実施で継続する実装です。ただし API キーの管理には注意してください。
- ログは日次ローテーションされ、デフォルトで 30 日分保持されます。ログ出力先に対するディスク容量や権限を確認してください。
- プロセス優先度・CPU affinity は `psutil` を利用して設定します。権限不足で失敗するケースがあるため、該当ログを確認してください。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在)
  - execution/
    - execution_engine.py (存在)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - data/ (想定データ・DB の置き場)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (DuckDB)
    - execution.pid, kill.flag, stop_requested.flag（制御用フラグ／PID）
  - utils/
    - logging_setup.py
    - process_priority.py

注: 上記はコードベースの主要ファイルを抜粋しています。細部はリポジトリの実際のツリーを参照してください。

---

## 追加情報 / 開発者向けヒント

- 設定検証 (`validate_config`) は `.env` と `config/*.yaml`（存在すれば）をチェックします。YAML 構文のチェックには PyYAML が必要です。
- DuckDB 接続を渡して研究モジュールを利用する設計のため、データ投入（prices_daily / raw_financials / raw_news 等）を行ってから解析関数を呼び出してください。
- LLM 呼び出し部分はテストのために内部呼び出しをモックしやすいように分離してあります（ユニットテストでの差替え推奨）。
- ローカルで実行する際、`data/` 配下のファイルに対する読み書き権限とディスク容量を確認してください。

---

もし README に追加したい具体的な項目（例: 実行時のログ出力例、よくあるトラブルシュート、CI 用の手順、より詳細な API 使用例など）があれば教えてください。必要に応じてサンプル .env テンプレートや運用手順のドラフトも作成します。