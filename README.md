# KabuSys

日本株自動売買システムの軽量リポジトリ（ライブラリ＋起動スクリプト群）。  
本 README はコードベースの概要、主要機能、セットアップ／起動手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の主要コンポーネントを含むシステムです。

- ExecutionEngine：発注の実行管理（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文状況・リスク監視
- Portfolio Construction：銘柄選定・配分・ポジションサイズ計算（純関数群）
- Research：ファクター計算・特徴量解析（DuckDB を用いた分析）
- AI モジュール：ニュース NLP によるセンチメント算出／市場レジーム判定（OpenAI API）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード／検証 CLI など

設計で意識している点：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による）
- DuckDB を分析用に利用、SQLite を監視・履歴保存に利用
- 起動スクリプトは環境変数ベースの設定（.env をサポート）
- OpenAI 呼び出しはフェイルセーフ（失敗時は無効化やデフォルト化）

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution — ExecutionEngine を起動
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパー用 DB（data/paper_trading.db）に記録
  - python -m kabusys.run_monitoring — SystemMonitor のポーリングループを開始
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
- 設定管理 / ツール
  - python -m kabusys.config_setup — 対話式 .env 作成ウィザード
  - python -m kabusys.validate_config — 設定（.env / config/*.yaml）事前検証 CLI
- 監視（monitoring）
  - system_monitor：CPU / メモリ / ディスク / プロセス可否 / データ鮮度監視
  - trade_monitor（注文関連監視／アラート） — モジュール化された監視 Engine で統合
  - risk_monitor：ドローダウン監視、ポジション数上限監視、リスクログ記録、Kill Switch 評価
  - monitoring_db：SQLite にテーブルを冪等作成・読み書き
- ポートフォリオ構築（純関数）
  - 候補選定、等配分・スコア加重、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ（DuckDB を利用）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI（OpenAI 連携）
  - news_nlp.score_news：ニュース記事を LLM でセンチメント化して ai_scores に書き込み
  - regime_detector.score_regime：ETF の MA とマクロニュースで市場レジーム判定
- レポート
  - kabusys.tools.paper_verification_report：ペーパートレードの稼働率・成功率・レイテンシ等の検証レポート生成 CLI

---

## セットアップ手順

前提：
- Python 3.10+ を想定（typing の記法より）
- 仮想環境の利用を推奨

1. リポジトリをチェックアウトし、仮想環境を作成・有効化する
   - 例（Unix 系）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
2. 依存パッケージをインストール
   - 必要な主要パッケージ（プロジェクトで使われているものの例）:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（validate_config が YAML のパース検証を行うため）
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - 実プロジェクトでは requirements.txt / poetry を用意してください（ここでは例示のみ）。
3. .env を用意する
   - 対話式ウィザード推奨:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を環境変数に設定するか、.env に登録
4. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いにできます
5. 必要なディレクトリを作成（.env の DB パスやログディレクトリがデフォルトのままなら）
   ```
   mkdir -p data logs
   ```

補足:
- 自動で .env をロードする挙動を無効化したい場合は環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 使い方（代表的なコマンド）

- ExecutionEngine の起動（本番 / ペーパー共通）
  - 本番（設定に応じて本番 DB を使用）
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（KABUSYS_ENV=paper_trading）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - ExecutionEngine 起動時はプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid デフォルト）を扱います。
  - ペーパートレード時は MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます。

- Monitoring の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）にログします。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計です（監視は本番 DB に関連ログを取る前提）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB の指定（オプション）
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- LOG_DIR（デフォルト logs/）
- OPENAI_API_KEY（AI モジュールで必須）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか 0/1）

設定・初期化時には `python -m kabusys.validate_config` を推奨します。

---

## 停止・Kill Switch の運用

- シグナル（停止）にはフラグファイルを利用します:
  - 停止リクエスト（監視ループ等の外部停止用）:`data/stop_requested.flag`
  - Execution の停止トリガー（Kill Switch が書き込む）:`data/kill.flag`
- ExecutionEngine は PID ファイル（data/execution.pid）を使用してプロセス管理を行います。
- KillSwitch はドローダウンやポジション上限などの条件で `data/kill.flag` を書き込み、Execution 側はこれを検知して安全停止します。

---

## トラブルシューティング・注意点

- ログが出力されない場合は `LOG_DIR` のパーミッションやディレクトリ存在を確認してください（logs/<app>.log に日次ローテーションで出力されます）。
- process priority の設定は OS の権限に依存します。権限不足だと設定に失敗して警告が出ますが、致命的ではありません。
- OpenAI 呼び出しはネットワーク障害や API レートに対してリトライやフォールバックロジックが実装されていますが、API キーが未設定の場合は例外になるので事前に設定してください。
- validate_config で YAML の解析を行うには PyYAML が必要です。未インストール時は該当検証をスキップします。
- Monitoring は設計上、環境にかかわらず「本番 sqlite_path」を使用します。ペーパートレードと監視 DB を混同しないよう注意してください。

---

## ディレクトリ構成（抜粋）

以下は main なファイル・モジュールの構成（リポジトリ内 `src/kabusys/` を想定）：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py 等は参照あり)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - (その他 execution/*、data/*、strategy/* などが存在する想定)

---

## 開発メモ / 拡張ポイント

- ポートフォリオ／ポジションサイズ計算は純関数群として実装されており、ユニットテストが容易です。
- DuckDB を使ったリサーチコードは SQL と Python を組み合わせた設計。データ準備（prices_daily / raw_financials / raw_news 等）が必要です。
- AI モジュールは JSON Mode を利用して厳密な構造を期待しますが、LLM の出力ゆらぎを吸収する耐性（パースの復元、クリッピング、リトライ等）を持っています。
- 将来的にログ収集やメトリクス出力を Prometheus / Grafana 等と連携する拡張が可能です。

---

必要であれば README の英訳、さらに詳細な API リファレンス（関数ごとの引数/戻り値/例）、運用手順（systemd / Docker / Supervisor 用のユニット定義例）も作成できます。どれを優先して作成しましょうか？