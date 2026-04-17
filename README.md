# KabuSys

日本株向けの自動売買／調査プラットフォーム（ライブラリ＋実行スクリプト群）。

本リポジトリは、戦略実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、ニュースNLP（OpenAI を利用したセンチメント評価）などの主要コンポーネントを含みます。

> 現在のバージョン: 0.1.0

---

## 概要

KabuSys は、以下の目的を持ったモジュール群を提供します。

- 戦略に基づく銘柄選定と発注（ExecutionEngine）
- 実行環境・注文・リスクの監視（Monitoring）
- ポートフォリオ構築（weights／position sizing）
- DuckDB を用いたファクター計算・リサーチ
- ニュース記事の LLM（OpenAI）によるセンチメントスコアリング
- ペーパートレード専用の分離された DB を用いた検証ツール

設計方針として、実行系と監視系は分離され、ペーパートレード時は発注データを本番 DB と分離して記録します。設定は .env（環境変数）で管理します。

---

## 機能一覧

- 実行
  - ExecutionEngine を起動して戦略に基づく発注を行う（KABUSYS_ENV により paper_trading / live / development を切替）
  - paper_trading モードでは MockBrokerClient を使い、専用の SQLite（デフォルト: data/paper_trading.db）へ記録
- 監視
  - SystemMonitor: CPU／メモリ／ディスク、プロセス生存、データ鮮度を監視し SQLite にログ
  - TradeMonitor: 注文滞留・約定価格異常を検出してリスクログへ記録
  - RiskMonitor: ドローダウン・ポジション上限などをチェックし必要に応じて Kill Switch（フラグファイル）を作成
  - AlertManager: LINE Messaging API による通知（設定がある場合）
- データベース
  - DuckDB（分析用）と SQLite（監視／注文ログ）を併用
  - monitoring_db モジュールにより監視テーブルを自動作成／マイグレーション
- リサーチ
  - ファクター計算（Momentum / Volatility / Value など）
  - 将来リターン・IC 計算・ファクター要約
- AI（OpenAI）
  - ニュースをまとめて LLM に投げ、銘柄別センチメントを ai_scores に書き込む
  - 市場レジーム判定（ETF MA200 とマクロニュースセンチメントの組合せ）
- ツール
  - config_setup: .env を対話式に生成・更新
  - validate_config: 起動前に環境設定と config/*.yaml の整合性チェック
  - paper_verification_report: ペーパートレード DB を元に検証レポート生成

---

## セットアップ手順

前提:
- Python 3.8+（ソースは typing 型ヒントを使用）
- システム依存ライブラリ: psutil（プロセス優先度 / CPU affinity）、duckdb、openai（AI 機能）、requests（LINE 通知）、PyYAML（オプションで config 検証に使用）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージをインストール
   - (requirements.txt がある場合)
     - pip install -r requirements.txt
   - 最低限必要なパッケージ例:
     - pip install duckdb psutil openai requests pyyaml

4. data ディレクトリ作成
   - mkdir -p data

5. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成してください。
   - 注意: .env は絶対に Git にコミットしないでください。

6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

7. 初回起動時の DB 初期化
   - 実際に run_monitoring / run_execution を起動すると必要テーブルが自動作成されます（monitoring_db.init_monitoring_db）。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / regime_detector を利用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — 監視モジュールは環境にかかわらずこのパスを参照します
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60 秒。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - デフォルト（KABUSYS_ENV に従う）
    - python -m kabusys.run_execution
  - ペーパートレード時は KABUSYS_ENV=paper_trading を設定:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に停止させたいときは monitoring の KillSwitch が data/kill.flag を生成、もしくは data/stop_requested.flag を作成することで停止できます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視プロセスは常に Settings.sqlite_path（本番用 monitoring.db）を使用します（KABUSYS_ENV に依存しません）。
  - 監視プロセスを終了させるにはプロジェクトルートの data/stop_requested.flag を作成してください（監視ループが検知して終了します）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- 注意（停止 / Kill）
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。flag は明示的に削除しない限り残ります（本番での誤設定に注意）。
  - ExecutionEngine は data/execution.pid を用いてプロセス生存を管理します（PID ファイルを検出してプロセスが生きていない場合は stale PID と見なして削除します）。

---

## 実装上のポイント / 注意事項

- DB 初期化／マイグレーションは monitoring_db.init_monitoring_db にて自動実行されます（テーブル作成・カラム追加などを冪等に行います）。
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path を使用します。run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して DB を分離します。
- process_priority の設定は psutil を利用します。権限不足や未対応 OS の場合は警告を出してスキップします。
- OpenAI を使う機能（news_nlp, regime_detector）は API キー必須。API 呼び出しは冗長性（リトライ・バックオフ）やレスポンス検証を行っており、失敗時はフェイルセーフ（スコアを 0 にフォールバックなど）で継続します。
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- セキュリティ:
  - .env 内のシークレットは絶対に Git にコミットしないこと。config_setup は .env ヘッダに注意喚起を記載します。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数／Settings 管理（.env 読込ロジックを含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor（監視ループ）起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続化 API
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止制御
    - alert_manager.py — LINE 通知管理
  - execution/ (参照のみ: 実際の詳細は別ファイル群に実装)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
  - portfolio/
    - portfolio_builder.py — 候補選定と重み計算
    - position_sizing.py — 発注株数計算・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI で銘柄ごとにスコア）
    - regime_detector.py — マクロ + ETF MA200 で市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

その他、data/ ディレクトリ（DB ファイルやフラグファイルを置く）を想定しています。

---

## よくある操作・トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートが自動検出できない場合、自動読み込みをスキップします。手動で .env を配置するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して動作を制御してください。
- 実行がすぐ終了する（stop フラグ）
  - data/stop_requested.flag や data/kill.flag が存在しないか確認してください。存在する場合は削除して再起動してください。
- OpenAI 周りで失敗が出る
  - OPENAI_API_KEY が正しく設定されているか、API 利用制限に達していないかを確認してください。API 呼び出しはリトライ実装がありますが、キー未設定だと例外で停止します。
- psutil による優先度設定でエラー
  - 権限不足の場合や未サポート OS の場合は警告が出ますが、処理自体は継続されます。

---

## 開発／拡張のポイント

- ポートフォリオ構築関数群は純粋関数（副作用なし）で設計されているため、ユニットテストが容易です。
- DuckDB を分析用 DB として用いることで、SQL ベースでの高速なファクター計算が可能です。
- AI 関連の呼び出しは外部依存（OpenAI）を持つため、ユニットテスト時は _call_openai_api をモックしてください（コード内で明示的にそうした差し替えを想定しています）。

---

必要に応じて、README に追加したいコマンド例や設定例を教えてください。README のサンプル .env 内容や systemd / supervisor 用の起動例なども作成できます。