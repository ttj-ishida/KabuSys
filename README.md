# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリです。戦略の研究・ファクター計算、ポートフォリオ構築、注文実行エンジン、監視系、AIベースのニュースセンチメント評価など、実運用を想定したコンポーネントが揃っています。

バージョン: 0.1.0

---

## 目次
- 概要
- 主な機能
- 必要要件
- セットアップ手順
- 使い方（コマンド一覧）
- 環境変数 / .env の説明
- 運用上の注意点
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は以下の責務を持つモジュールで構成されています。

- データ処理・研究（DuckDB を用いたファクター計算、将来リターン、IC 計算など）
- ポートフォリオ構築（シグナル選定、重み算出、リスク調整、ポジションサイズ計算）
- 実行エンジン（発注管理、ブローカー抽象化、ペーパートレード対応）
- 監視（システム稼働、自動 Kill Switch、トレードログ監視、リスク監視）
- AI モジュール（ニュースのセンチメント評価、レジーム判定）
- 開発支援ツール（設定ウィザード、設定検証、レポート生成）

設計方針として、ルックアヘッドバイアス回避、フェイルセーフ（API失敗時の安全挙動）、および本番 / ペーパーの明確な分離が取られています。

---

## 主な機能
- 環境設定ウィザード（対話式 .env 作成 / 更新）
- 設定検証 CLI（必須環境変数、config/*.yaml の存在・パース確認）
- ExecutionEngine 起動スクリプト（本番 / ペーパーで DB を分離）
- Monitoring 起動スクリプト（システム・トレード・リスク監視のポーリング）
- Kill Switch（条件に応じて data/kill.flag を作成し Execution を停止）
- Paper Trading 検証レポート生成スクリプト
- DuckDB ベースの研究モジュール（モメンタム・ボラティリティ・バリュー等）
- OpenAI を用いるニュース NLP（記事群をまとめてセンチメント評価）
- ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）

---

## 必要要件（推奨）
- Python 3.9+（コードは型アノテーションやパス操作を利用）
- 必須 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML — config/*.yaml のパース検証に使用
- SQLite は標準ライブラリで利用
- ネットワーク接続（OpenAI API / kabuステーション 等を利用する場合）

requirements.txt が無い場合は上記パッケージを pip でインストールしてください:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

4. ディレクトリ作成（ログ・データ用）
   - mkdir -p data logs

5. 初期環境変数作成
   - python -m kabusys.config_setup
     - 対話式に .env を生成します（.env は Git にコミットしないでください）

6. 設定検証（必須環境変数や config ファイルをチェック）
   - python -m kabusys.validate_config
   - 問題があれば指摘に従い .env や config/*.yaml を修正

7. DB 初期化等
   - 実行スクリプト側で起動時に必要なテーブルを作成します（monitoring などは自動で init を行います）

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告を失敗扱いにしたい場合: python -m kabusys.validate_config --strict

- Execution（注文実行エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録します
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中は data/execution.pid に PID が書き込まれます（設定で変更可能）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト: 60
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを保存します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- 研究用関数（ライブラリとして利用）
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.calc_forward_returns / calc_ic / factor_summary
  - これらは DuckDB の接続とターゲット日付を引数に取ります

---

## 主要な環境変数（簡易説明）
（.env で管理することを推奨）

- JQUANTS_REFRESH_TOKEN: J-Quants API (必須)
- KABU_API_PASSWORD: kabuステーション API パスワード (必須)
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector 使用時）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
  - paper_trading: MockBroker を使用し paper DB に記録
  - live: 本番モード（注意して設定してください）
- DUCKDB_PATH: DuckDB ファイル (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH: 監視用 SQLite (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）

自動で .env をロードする仕組み:
- プロジェクトルートにある `.env` と `.env.local` を自動読み込み（OS 環境変数を上書きしない設定）
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 運用上の注意点
- Kill Switch
  - risk_monitor 等の評価で条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は冪等で既に flag がある場合は再書込しません。
  - 本番 (`KABUSYS_ENV=live`) では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（誤って自動クリアされると危険）。

- 停止フラグ / PID
  - data/stop_requested.flag: 起動中の監視 / エンジンがこれを検知すると安全に停止します。
  - data/execution.pid: ExecutionEngine の PID（起動時に書き込まれます）

- ログ
  - kabusys.utils.logging_setup.setup_logging を介して、stdout と logs/<app_name>.log（毎日ローテート）へ出力します。
  - ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります。

- DB 分離
  - Paper Trading モードでは発注ログ等が本番 DB と分離され、PAPER_TRADING_SQLITE_PATH に保存されます。これにより本番環境への影響を防ぎます。

- OpenAI / 外部 API
  - news_nlp や regime_detector は OpenAI を利用します。API 課金やレートリミットに注意してください。
  - リトライやフェイルセーフが入っていますが、APIキー未設定時は明示的に例外が出ます（テスト時は差し替え可能）。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル・ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数自動読み込みと Settings クラス
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — raw_news を OpenAI で評価して ai_scores へ書き込む
    - regime_detector.py — MA200 とマクロニュースを合成して market_regime を決定

  - monitoring/
    - monitoring_db.py — SQLite 単体の永続化層（テーブル作成 / CRUD）
    - system_monitor.py — CPU / メモリ / データ鮮度 / Execution プロセス監視
    - trade_monitor.py — (トレード監視ロジック：ログの検査等) ※詳細はファイル参照
    - risk_monitor.py — ドローダウン / ポジション数監視、リスクアラート記録
    - kill_switch.py — kill.flag の作成・管理
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — (アラート送信管理: LINE 等) ※実装参照

  - execution/
    - execution_engine.py — ExecutionEngine コア（セッション実行）
    - broker_factory.py — ブローカークライアントの生成（Mock / 実ブローカー）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注・リスク管理関連

  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出（等金額・スコア加重）
    - position_sizing.py — 発注株数計算（リスクベース、等分配など）
    - risk_adjustment.py — セクター上限やレジーム乗数

  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリューの計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー

  - data/ (ローカル実行時に生成・利用)
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード）
    - kill.flag, stop_requested.flag, execution.pid など

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発・拡張ポイント（参考）
- research/* の関数は DuckDB 接続を受け取る純粋関数として設計されており、データセットを差し替えて再利用できます。
- news_nlp と regime_detector は OpenAI API 呼び出し部をモック差し替え可能に実装しており、ユニットテストしやすくなっています。
- monitoring_db.init_monitoring_db はマイグレーション的に既存カラムの追加を行うため、運用中 DB の互換性を保ちやすい設計です。

---

不明点や README に追記したい項目（例: 実際の broker 接続設定例、config/*.yaml の内容テンプレートなど）があれば教えてください。必要に応じてセクションを追加・具体化します。