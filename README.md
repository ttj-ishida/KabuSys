# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視を想定した小規模フレームワークです。このリポジトリは以下の機能群を含みます：注文実行エンジン、監視（モニタリング）サブシステム、ポートフォリオ構築ユーティリティ、ファクター計算・研究ツール、AI（ニュース NLP / レジーム判定）連携ツール、ユーティリティ群（設定読み込み、ロギング、プロセス優先度設定など）。

※ 本 README はソースコード（src/kabusys 以下）を基に作成しています。

## 主な特徴（機能一覧）

- 実行エンジン（ExecutionEngine）
  - 実際のブローカークライアントと連携して発注を行う（Kabuステーション連携を想定）
  - `paper_trading` モード時は MockBroker を使用し、ペーパートレード用 DB に書き込む（本番 DB と完全分離）
  - リスク管理、オーダー管理、リコンシリエーション機能を備える

- 監視（Monitoring）
  - システム（CPU / メモリ / ディスク・プロセスの生存）やデータ鮮度を監視する `SystemMonitor`
  - 注文ログの監視（滞留注文、異常約定など）を扱う `TradeMonitor`
  - ドローダウンやポジション上限を監視する `RiskMonitor`
  - Kill Switch（条件によりフラグファイルを書いて実行エンジンを停止）を備える
  - 監視データの永続化は SQLite（デフォルト: `data/monitoring.db`）

- ポートフォリオ構築
  - 候補選定、等重・スコア重み配分、セクター上限適用、ポジションサイズ計算（単元株丸め含む）

- リサーチ（研究）
  - DuckDB 上の時系列データからファクター（モメンタム、ボラティリティ、バリュー等）を計算
  - 将来リターン、IC 計算、ファクター統計サマリ等のユーティリティ

- AI（OpenAI）連携
  - ニュース記事を LLM（gpt-4o-mini 等）でスコアリングして ai_scores テーブルへ書き込み
  - マクロ記事 + ETF MA200 乖離を用いて市場レジーム（bull/neutral/bear）を判定し DB に保存
  - API コールは冪等・リトライ・フェイルセーフ設計

- ユーティリティ
  - .env 対話式ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - ロギングセットアップユーティリティ（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定（Windows / POSIX の差異を吸収）

- 補助ツール
  - Paper Trading の検証レポート生成スクリプト（`tools/paper_verification_report.py`）

## 必須 / 推奨環境

- Python 3.10+
  - 型アノテーション（`X | None` 等）や新しい型ヒントを利用しています。
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の YAML 検証を行う場合）
- SQLite は標準ライブラリで利用します。

インストール例（仮）:
```
python -m pip install duckdb psutil openai pyyaml
```
（実際の requirements はプロジェクトで管理してください）

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 環境を準備（仮想環境推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai pyyaml
   ```

3. 初期 .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは `.env` を生成・更新します。必須項目:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   注意:
   - `.env` は Git にコミットしないでください（機密情報を含みます）。
   - 自動ロードはデフォルトで有効。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗（exit(1)）として扱います。
   - PyYAML が無い場合、config/*.yaml の検証はスキップされます（警告出力）。

5. データディレクトリ / ログディレクトリ確認
   - デフォルト DB / ログ:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (monitoring): `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`
     - ログディレクトリ: `logs/`
   - 必要に応じて `.env` で `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`, `LOG_DIR` を上書きしてください。

## 起動・使い方

各主要スクリプトはモジュール実行で起動できます。

- 監視ループの起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 既定でポーリング間隔は 60 秒（環境変数 `MONITOR_POLL_INTERVAL` で上書き可能）。
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず監視 DB は本番 DB を参照する設計）。
  - プロセス優先度を "high" に設定し、監視結果を SQLite に書き込みます。
  - 停止はプロジェクトルート下 `data/stop_requested.flag` ファイルを作成することで行えます（存在検出でループ終了）。

- 実行エンジンの起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV` が `paper_trading` の場合、MockBrokerClient が使われ、データは `data/paper_trading.db` に記録されます（本番 DB と分離）。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動しません。
  - 実行エンジンは別スレッドでセッションを走らせ、停止フラグが検知されると `engine.stop()` を呼んで終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `data/paper_trading.db`。`--db PATH` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を算出し PASS/FAIL 判定を出力します。

- AI（ニューススコア / レジーム判定）
  - プログラム的に利用する関数:
    - `kabusys.ai.score_news.score_news(conn, target_date, api_key=None)`
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - 事前に環境変数 `OPENAI_API_KEY` を設定するか、関数の `api_key` 引数で渡してください。
  - 実行は DuckDB 接続（`duckdb.connect(path)`) を作成してから呼び出します。
  - API 呼び出しはリトライ・エラーハンドリングを実装しています。失敗時は安全側にフォールバックします（例: macro_sentiment=0）。

- 設定読み込み仕様（ポイント）
  - 自動 .env ロード順:
    1. OS 環境変数（既存）
    2. `.env.local`（存在すれば上書き。ただし OS 環境変数は保護）
    3. `.env`
  - 自動ロードを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- 監視 / 実行の停止フラグ・Kill Switch
  - Execution 側の停止には `data/kill.flag`（Kill Switch）／`data/stop_requested.flag` を利用する設計です。
  - `KillSwitch` はリスク条件（ドローダウン超過やポジション上限超過）で `kill.flag` を書き込みます。エンジンはその存在を検知して停止します。
  - `KillSwitch.clear()` を起動時に呼ぶオプション（設定で `KILL_FLAG_CLEAR_ON_START=1`）がありますが、本番では `0` を推奨します。

## 重要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う / 設定可能:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading モード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定動作（"instant" | "partial" | "never" | "reject"）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1/0）

## ディレクトリ構成（src 側の主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定の読み込み・検証ロジック
  - config_setup.py
    - .env の対話式ウィザード生成スクリプト
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (監視ロジックファイル群)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (アラート送信類想定)
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py（実行ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py, stats.py 等（データ取得 / 前処理ユーティリティ）
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要なファイルを抜粋した概略です。実際のファイル数・詳細はソースツリーを参照してください。）

## 開発・テスト時の便利なポイント

- 設定チェック:
  - `python -m kabusys.validate_config` で起動前設定を素早くチェックできます。
- .env を手早く作る:
  - `python -m kabusys.config_setup` で対話式に .env を生成できます。
- ログ:
  - `kabusys.utils.logging_setup.setup_logging()` を各スクリプトで利用して統一されたログ出力を得られます。ログは stdout と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- Paper Trading 検証:
  - `python -m kabusys.tools.paper_verification_report` でペーパートレード DB の統計レポートを出力できます。

## セキュリティ / 運用上の注意

- `.env`（アクセストークンやパスワード）を絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します（自動クリアは危険）。
- OpenAI API 等外部サービスのキーは適切に管理してください（環境変数・シークレット管理ツール推奨）。
- プロセス優先度や CPU affinity 設定は権限により失敗する場合があります（ログに警告が出ます）。

---

この README はソースコードの意図と主要な使い方をまとめたものです。実運用時は config/*.yaml（プロジェクトに含まれる設定テンプレート）や実装コメント、ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が別に用意されていれば併せて参照してください。必要であれば、起動・デプロイ手順（systemd / Supervisor / Cron など）やより詳細な運用ガイドを別途作成できます。