# KabuSys

軽量な日本株自動売買システムのライブラリ群・起動スクリプト群です。  
本リポジトリは戦略・ポートフォリオ構築、取引執行、監視、研究用ユーティリティ、AI を使ったニュース解析などをモジュール化しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のコンポーネントを備えた自動売買プラットフォームのコア実装です。

- ExecutionEngine（発注・注文管理・リスク管理・再整合）
- Monitoring（システム稼働・注文ログ・リスク監視・Kill Switch）
- Portfolio construction（候補選定・重み付け・ポジションサイズ算出）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定）
- 各種 CLI スクリプト（設定ウィザード、設定検証、起動スクリプト、レポート生成）

設計方針の一部:
- 本番・ペーパートレードはデータベースを分離（paper_trading 環境時は専用 SQLite を使用）
- ルックアヘッドバイアス回避のため、日付参照は引数ベース（date.today() 依存を最小化）
- フェイルセーフを重視（API 失敗時はスキップ or フォールバック）
- 純粋関数化（portfolio / research の多くは DB を直接参照しないか限定的）

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み（プロジェクトルートに .env / .env.local）
  - Settings クラスによる集中取得（環境変数のバリデーション）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行エンジン
  - BrokerClient 抽象化（本番/ペーパーで分離）
  - OrderManager / OrderRepository / Reconciler / RiskManager の組合せ
  - ExecutionEngine をスレッドで起動する起動スクリプト（python -m kabusys.run_execution）

- 監視
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセス存否、データ鮮度
  - TradeMonitor: 注文滞留・約定異常などの検出（実装モジュールあり）
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件により data/kill.flag を書き込み、ExecutionEngine を停止
  - MonitoringEngine と run_monitoring スクリプト（ポーリングループ）

- ポートフォリオ構築
  - 候補選定（スコア順）、等重/スコア重み、リスクベースの株数算出
  - セクター上限適用、レジームに応じた投下乗数

- リサーチ
  - モメンタム / ボラティリティ / バリューのファクター算出（DuckDB 利用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI（OpenAI）
  - ニュース NLP による銘柄別センチメント（ai_scores への書き込み）
  - マクロニュース + ETF MA200 による市場レジーム判定
  - API 呼び出しは冪等・リトライ・JSON バリデーション実装あり

- ツール
  - Paper Trading 用検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境向け）

前提: Python 3.10+ を想定（typing の型注釈・ match 等ではなくとも一部の型構文に依存）。  
実行環境に合わせて Python バージョンを選んでください。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - 要件ファイルがない場合、最低限以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（config 検証で YAML のパースを有効にする場合）
   例:
     pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは、プロジェクトルートに手動で .env を作成（.env.example を参考に）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付与

6. データディレクトリの確認
   - デフォルトの SQLite / DuckDB ファイルパスは data/ 配下です。起動時に自動作成されますが、書込み権限などに注意してください。

---

## 環境変数（主なものとデフォルト）

- 必須（validate_config でもチェック）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)

- 実行環境選択
  - KABUSYS_ENV: development | paper_trading | live
    - デフォルト: development

- データベース
  - DUCKDB_PATH: data/kabusys.duckdb (デフォルト)
  - SQLITE_PATH: data/monitoring.db (デフォルト)
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用 DB)

- PAPER_TRADING オプション
  - PAPER_FILL_MODE: instant | partial | never | reject (デフォルト: instant)

- ロギング
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）

- Kill / PID ファイル
  - PID_FILE_PATH: data/execution.pid (デフォルト)
  - KILL_FLAG_PATH: data/kill.flag (デフォルト)
  - KILL_FLAG_CLEAR_ON_START: 1 または 0（本番では 0 推奨）

- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

- その他
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

---

## 使い方

基本的な起動コマンド例を示します。

- 設定ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（常用）
  - python -m kabusys.run_execution
  - ポイント:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - 停止は data/stop_requested.flag 書き込みにより行います（運用上は kill.flag 等と組み合わせる場合あり）。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を参照してログ保存します（環境に依存せず本番 DB を使用する設計）

- Paper Trading 検証レポート（標準出力に出力）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチ関数（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - research モジュール:
    - kabusys.research.calc_momentum(duckdb_conn, date)
    - kabusys.research.calc_volatility(...)
    - kabusys.research.calc_value(...)
    - kabusys.research.calc_forward_returns(...), calc_ic(...)

- ログ設定ユーティリティ（ライブラリ使用例）
  - from kabusys.utils.logging_setup import setup_logging
  - setup_logging(app_name="execution")

---

## 停止・Kill フラグについて

- stop_requested.flag (run_*.py で使用)
  - run_monitoring / run_execution はプロジェクト data/stop_requested.flag を監視し、存在する場合ループを終了または起動をスキップします。
  - ストップ制御用に外部プロセスがこのファイルを作成／削除する運用を想定。

- kill.flag (KillSwitch)
  - KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine 側で検出して安全停止する仕組みです。
  - 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすることで誤って自動クリアする挙動を防止できます。

---

## ディレクトリ構成

以下は主要なファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み・Settings
  - config_setup.py              — .env 対話式ウィザード CLI
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - execution/                   — 発注系（BrokerFactory, Engine, OrderManager など）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（冪等なテーブル作成含む）
    - system_monitor.py          — システム・データ鮮度監視
    - trade_monitor.py           — 注文ログ監視（滞留・価格異常等）
    - risk_monitor.py            — ドローダウン・ポジション監視
    - kill_switch.py             — KillSwitch 制御
    - monitoring_engine.py       — 各 Monitor を束ねる
    - alert_manager.py           — アラート送信管理（LINE など、実装次第で使用）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数計算・キャップ処理
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py         — momentum/value/volatility ファクター
    - feature_exploration.py     — forward returns, IC, summary
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py         — マクロ + ETF MA200 を合成したレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では設定（LINE トークン・KILL フラグ動作など）を十分に確認してください。validate_config は live で追加の注意喚起を行います。
- OpenAI API を使用する機能は API キーが必要です。API 呼び出しはリトライ・フォールバック実装がありますが、API 利用コストとレート制限に注意してください。
- ログはデフォルトで logs/ に日次ローテートで出力されますが、ファイル作成権限に注意してください。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- ペーパートレード用 DB は本番 DB と分離されています（paper_trading 環境のときのみ paper_sqlite_path を使用）。データ損失防止のため適切にバックアップしてください。
- モジュールはユニットテストを想定した実装（副作用を小さくする）になっています。CI に組み込む際は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動ロードを無効化できます。

---

## 参考コマンドまとめ

- .env を作る（対話式）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README にサンプル .env テンプレートや systemd / Supervisor などでのデプロイ例、より詳しいモジュール別 API ドキュメントを追加します。どの情報を優先して追加しますか？