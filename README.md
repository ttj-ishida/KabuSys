# KabuSys

日本株向け自動売買システムのリファレンス実装（モジュール群）。  
このリポジトリは、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、
AI を用いたニュース NLP、ユーティリティ等を含む構成になっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。主な役割は以下です。

- シグナル → 発注までの ExecutionEngine（本番 / ペーパートレード対応）
- システム・注文・リスク監視とアラート / Kill Switch
- ファクター計算や特徴量探索を行う Research ツール群（DuckDB ベース）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 運用を支援する CLI（.env ウィザード・設定検証・ペーパートレード検証レポート等）

設計方針の一部：
- 環境変数 / .env で設定を管理
- DuckDB（分析用） / SQLite（監視・発注ログ）を併用
- OpenAI API を用いる処理はフェイルセーフ（API失敗時はスキップまたはデフォルト値）
- 本番(DB)とペーパートレード(DB)は分離可能

---

## 主な機能一覧

- 実行エンジン（run_execution.py）
  - KABUSYS_ENV によるモード切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を利用し、ペーパートレード専用 DB に記録
  - リスク管理（RiskManager）、OrderManager、Reconciler などを組み合わせて発注を実行

- 監視（run_monitoring.py / monitoring パッケージ）
  - CPU / メモリ / ディスク 使用率や ExecutionProcess の生存確認
  - 注文滞留や約定異常、ドローダウン監視
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナル）
  - ログを SQLite に永続化（monitoring_db.py）

- AI（kabusys.ai）
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に書き込み
  - regime_detector: ETF の MA とマクロ記事から市場レジーム判定を行い market_regime に保存

- Research（kabusys.research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン / IC 計算 / 統計サマリ等（DuckDB を利用）

- Portfolio（kabusys.portfolio）
  - 候補選定、重み計算（等金額・スコア加重）
  - セクター集中制限、レジーム乗数
  - 発注株数決定（単元株丸め・aggregate cap 調整）

- ツール（kabusys.tools）
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定と集計を出力

- 設定支援
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証

- 共通ユーティリティ
  - ログセットアップ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity の設定

---

## セットアップ手順

前提:
- Python 3.9+
- システムにより追加のライブラリが必要（下記）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo>
   cd <repo>
   ```

2. 依存パッケージをインストール（例）
   ```
   pip install -r requirements.txt
   ```
   必要な主なパッケージ（本コードで利用）:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で任意）
   - （必要に応じて）その他ライブラリ

   ※ requirements.txt がない場合は上記パッケージを個別にインストールしてください。

3. .env を作成
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` を編集 / 作成（.env.example を参考に）。

   重要な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live）
   - DUCKDB_PATH（例: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、例: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、paper_trading モード時）
   - OPENAI_API_KEY（AI モジュールを利用する場合）
   - LOG_LEVEL, LOG_DIR 等

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗として扱います。

---

## 使い方

各コンポーネントはモジュール実行方式で起動します。

- 監視プロセス起動（SystemMonitor のポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - run_monitoring は監視用の SQLite パス（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）

  停止:
  - プロジェクトルート/data/stop_requested.flag を作成するとループは検出して安全に終了します。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  動作モード:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - それ以外は本番 sqlite_path を使用します。

  停止:
  - data/stop_requested.flag を作成すると起動済みエンジンを停止します。
  - Kill Switch（監視が条件を満たした場合）で data/kill.flag が書かれると ExecutionEngine による停止トリガーとなります。
  - 実行中、PID ファイルは data/execution.pid（設定に応じて可変）に作成されます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パス指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  または環境変数 PAPER_TRADING_SQLITE_PATH を使用。

- AI / レジーム判定等
  - ai モジュールは OpenAI API キー（OPENAI_API_KEY）を必要とします。キーが無ければ呼び出し時にエラーになります（呼び出し元は捕捉している場合があります）。
  - news_nlp.score_news, regime_detector.score_regime などを呼び出して DuckDB 上のテーブルを更新します。

- ログ
  - デフォルトでコンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）へ出力されます。
  - ログレベルは LOG_LEVEL 環境変数または設定で制御。

---

## よく使う環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（例 data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（例 data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（paper_trading モード）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

---

## 停止・Kill Switch の挙動

- 手動停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution がこのファイルの存在を検知すると安全に終了します（手動で作成して停止可能）。

- Kill Switch:
  - RiskMonitor 等が閾値を超えると KillSwitch が data/kill.flag を作成します（既に存在する場合は上書きしない）。
  - ExecutionEngine 側は kill.flag の存在を参照して停止する設計です（設定に従って動作）。

- 注意:
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすることが推奨されます（誤って自動クリアされると安全機構が無効化される恐れがあるため）。

---

## ディレクトリ構成

以下は主要なファイル / モジュールの抜粋（src/kabusys 以下）。実際のプロジェクトルートは src/ をパッケージ化して使用します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常監視（ファイル内にあり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 複数モニタを束ねるエンジン
    - alert_manager.py       — 通知管理（LINE 等を想定）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig / run_session 等）
    - broker_factory.py      — ブローカークライアント生成（実・Mock）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み付け
    - position_sizing.py     — 発注株数算出
    - risk_adjustment.py     — セクター制限 / レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC 等
  - ai/
    - news_nlp.py            — ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## 開発時の注意点 / 補足

- .env の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を検出して `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、既存 DB に対する簡易マイグレーション（列追加）も実行します。

- ロギング:
  - setup_logging() は stdout 出力と日次ローテートファイル（logs/<app>.log）を設定します。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続します。

- 外部 API キー:
  - OpenAI API キーやサードパーティ API トークンは .env に保存し、Git 管理下に絶対にコミットしないでください。

---

もし README に追記してほしい箇所（API の詳細な仕様、各クラスの使い方、CI/デプロイ手順、requirements.txt の候補など）があれば教えてください。必要に応じてサンプル .env のテンプレートや起動スクリプトの systemd ユニット例も作成します。