# KabuSys — README (日本語)

このリポジトリは日本株自動売買プラットフォーム「KabuSys」のコアライブラリ群です。戦略の研究／ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI ベースのニュース解析などを含むモジュール群を提供します。

以下はリポジトリの概要・機能一覧、セットアップ・起動方法、主要ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されます。

- research: DuckDB 上でのファクター計算や将来リターン／IC 計算などの研究用関数群
- portfolio: 銘柄選定、重み計算、ポジションサイズ算出、セクター制約やレジーム調整
- execution: ブローカークライアントを介した注文管理・実行（本番 / ペーパートレード対応）
- monitoring: システム稼働・注文状況・リスク監視、Kill Switch（停止フラグ）管理、アラート
- ai: ニュース NLP によるセンチメント算出、レジーム判定のための LLM 呼び出し
- tools: ペーパートレード検証レポート等のユーティリティスクリプト
- utils: ロギング設定・プロセス優先度などのユーティリティ

設計上の特徴：
- DuckDB（分析用）と SQLite（監視・発注履歴）を併用
- 環境変数 / .env による設定管理（config モジュール）
- 本番（live）／開発（development）／ペーパートレード（paper_trading）モードに対応
- LLM（OpenAI）を使ったニュース分析はフェイルセーフ（API失敗時はスキップ/フォールバック）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を生成・更新
- 設定検証 CLI（python -m kabusys.validate_config）で起動前チェック
- ExecutionEngine 起動スクリプト（本番/ペーパーで DB 分離）
- Monitoring のポーリング起動（システム状態・注文・リスクの監視）
- Kill Switch：リスク条件（ドローダウンやポジション上限）で停止フラグを書込む仕組み
- AI モジュール：ニュースを LLM で解析して銘柄ごとのスコアを生成（ai.news_nlp）、市場レジーム判定（ai.regime_detector）
- 研究用ユーティリティ：ファクター計算（momentum/value/volatility）、特徴量解析、IC 計算 等
- portfolio モジュール：候補選定、重み計算、ポジションサイズ算出、セクターキャップ／レジーム乗数
- tools: Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提：Python 3.9+ がインストールされていることを想定します。

1. リポジトリをクローンして、Python 仮想環境を作成／有効化
   - 例:
     ```
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージをインストール
   - 必要な主要ライブラリ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で YAML パースを行う場合）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - （本リポジトリに requirements.txt があればそちらを使用してください）

3. .env ファイルの作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - または手動でプロジェクトルートに `.env` を作成（.env.example を参照）。
   - 主な環境変数（デフォルト値や意味）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の専用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能利用時に必要）
     - KILL_FLAG_CLEAR_ON_START（0/1、デフォルト 0。起動時に kill.flag を自動クリアするか）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 — 60 秒がデフォルト）

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

5. データディレクトリの準備（通常は自動作成されますが、手動で作る場合）
   - data/（SQLite DB、PID・flag 用）
   - logs/（ログファイル）

---

## 使い方（実行例）

- Monitoring の起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き可能（例: 30）
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視は常に本番 sqlite_path を参照します）。

- ExecutionEngine（発注エンジン）の起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
  - 起動中は data/execution.pid が使用されます。停止は data/stop_requested.flag の作成や kill.flag によるシグナルで制御されます。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（SQLite DB を参照）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db` オプションで別パス指定可。

- AI / レジーム判定・ニューススコアリング（ライブラリ関数として）
  - ai.score_news（kabusys.ai.news_nlp.score_news）や ai.regime_detector.score_regime をプログラムから呼び出せます。呼び出しには OpenAI API キーが必要です（引数または環境変数 OPENAI_API_KEY）。

---

## 重要な挙動・運用上の注意

- Monitoring は環境に関係なく Settings.sqlite_path（監視 DB）を使用します。Execution は KABUSYS_ENV によって本番/ペーパー DB を切り替えます。
- Kill Switch（data/kill.flag）:
  - RiskMonitor の条件（ドローダウン超過やポジション上限超過）で KillSwitch が kill.flag を書き込みます。
  - ExecutionEngine は kill.flag を検知すると安全に停止動作を行います。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアします（本番では 0 を推奨）。
- stop_requested.flag（data/stop_requested.flag）:
  - run_monitoring.py / run_execution.py が終了を検知するための簡易停止フラグです。存在するとループを抜けます。
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を全スクリプトで使っています。ログファイルはデフォルト logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリは LOG_DIR 環境変数で変更可。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・モジュールです（重要なファイルを抜粋しています）。

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / .env 自動ロード / Settings クラス
    - config_setup.py                # 対話式 .env ウィザード
    - validate_config.py             # 起動前検証 CLI
    - run_execution.py               # ExecutionEngine 起動スクリプト
    - run_monitoring.py              # Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py # ペーパートレード検証レポート
    - utils/
      - logging_setup.py             # ログ設定ユーティリティ
      - process_priority.py          # プロセス優先度・CPU affinity 設定
    - monitoring/
      - monitoring_db.py             # SQLite 永続化層（テーブル初期化 / CRUD）
      - monitoring_engine.py         # 各 Monitor をまとめるエンジン
      - system_monitor.py            # CPU/メモリ/ディスク・データ鮮度監視
      - trade_monitor.py             # （注：コードベースに存在）注文滞留・約定異常検出
      - risk_monitor.py              # ドローダウン・ポジション上限監視
      - kill_switch.py               # kill.flag 書込/判定
      - alert_manager.py             # （通知管理: LINE 等、実装により存在）
    - execution/
      - broker_factory.py            # ブローカークライアント生成（本番/Mock）
      - execution_engine.py          # 実際の取引セッションを動かす Engine
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py                  # ニュース NLP スコアリング（OpenAI呼出）
      - regime_detector.py          # レジーム判定（MA + マクロ NLP 合成）
    - data/                           # 実行時に使う DB ファイル・flag・pid など（data/*.db）
    - logs/                           # デフォルトログ保存先

（上記は実際のツリーを抜粋したもので、さらに補助モジュールやテスト等が含まれる場合があります。）

---

## よく使う環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB のパス）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用 DB）
- LOG_LEVEL / LOG_DIR: ログ設定
- OPENAI_API_KEY: AI 機能で使用
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

---

## 開発・拡張メモ

- DuckDB 接続を受ける研究・AI モジュールは DB スキーマ（prices_daily / raw_financials / raw_news 等）に依存します。サンプルデータの投入や DB スキーマ生成スクリプトを整備しておくと開発が容易です。
- OpenAI の呼び出しはリトライやレスポンスのバリデーションを備えていますが、API 料金・レート制限に注意してください。
- 実運用では KABUSYS_ENV=live とし、LINE 通知や Kill Switch の設定を十分に確認してください（validate_config の live ガードを参照）。

---

必要があれば、README に次の追加を行えます：
- 手順をまとめたデータベース初期化コマンド
- 開発用の Dockerfile / docker-compose 例
- 具体的な .env.example（テンプレート）
- 各モジュールの API リファレンス（関数一覧と引数の説明）

必要な追加や修正点があれば教えてください。README を更新して反映します。