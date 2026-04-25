# KabuSys

日本株自動売買システム（KabuSys）の簡易リポジトリ説明書です。  
この README はソースコード（src/kabusys）を基に、セットアップ・実行方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 環境変数（主なキー）
- セットアップ手順
- 使い方（実行コマンド例）
- 停止・Kill Switch、フラグファイル
- 開発用ツール
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主要なコンポーネントは以下のとおりです。

- ExecutionEngine：発注・注文管理・リスク管理を担う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働状態・注文状態・リスクを巡回監視し、アラート／Kill Switch を制御
- Portfolio：銘柄選定・配分・ポジションサイズ計算などのポートフォリオ構築ロジック（純関数群）
- Research：DuckDB を用いたファクター計算・特徴量探索モジュール
- AI：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ユーティリティ：設定読み込み、ロギング、プロセス優先度設定 等

設計方針として本番 DB とペーパートレード DB を分離可能にしており、DuckDB を分析用、SQLite を監視・発注ログ保存用に使用します。

---

## 機能一覧

- 実行エンジン（ExecutionEngine）
  - ブローカークライアントの抽象化（本番・Mock を切替）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager、閾値やサーキットブレーカー等）
  - Reconciler による注文整合性維持
- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率監視
  - Execution プロセスの生存監視（PID ファイル）
  - 注文滞留・約定異常・ドローダウン・ポジション数監視
  - Kill Switch（閾値超過時に停止フラグを書き込み）
  - アラート送信（LINE 等拡張可能）
- ポートフォリオ構築
  - 候補選定、等配分 / スコア配分、リスクベースの枚数算出
  - セクターキャップ適用、レジーム乗数適用
- リサーチ / 指標算出（DuckDB）
  - モメンタム・ボラティリティ・バリュー等のファクター算出
  - 将来リターン・IC（Spearman）等の解析ユーティリティ
- AI 関連
  - ニュース記事を OpenAI（gpt-4o-mini等）でセンチメント化して ai_scores に格納
  - マクロニュース + ETF MA で市場レジーム（bull/neutral/bear）を判定
- ツール
  - ペーパートレード検証レポート生成スクリプト（paper_verification_report）
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 環境変数（主なキー）

（.env を使用して設定することを想定）

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB に記録されます
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の Fill 動作（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で使用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = 自動クリア）

自動読み込み
- リポジトリルートの .env, .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 推奨パッケージ（実装参照）:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （リポジトリに requirements.txt がない場合、上記を参考にしてください）

4. .env の初期作成
   - 対話式ウィザードで作成
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に自分で作成（.env を絶対にリポジトリにコミットしないこと）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

6. データディレクトリ
   - デフォルトは data/、logs/ が自動作成されます。必要に応じて .env のパスを変更してください。

注: SQLite / DuckDB ファイルは起動時に自動でテーブル作成（マイグレーション）される箇所があります（例: monitoring DB 初期化）。

---

## 使い方（実行例）

重要: 実行はモジュールを直接呼び出す形が想定されています。

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - シンプル実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード時は MockBrokerClient を使い、記録先は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視用 sqlite）を使用します

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH でも DB を指定可能

- AI スコアリング / レジーム判定（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

- ログ
  - デフォルト: logs/<app_name>.log（app_name は run 時に "execution" / "monitoring" など）
  - ログ設定は kabusys.utils.logging_setup.setup_logging を使用
  - LOG_DIR 環境変数でログディレクトリを変更可能

---

## 停止・Kill Switch・フラグファイル

- stop_requested.flag
  - run_execution と run_monitoring のループを外部から終了させるためのフラグファイル（data/stop_requested.flag）
  - ファイルが存在するとループは検知して終了します

- kill.flag（Kill Switch）
  - KillSwitch によって書き込まれるフラグ（Settings.kill_flag_path、デフォルト data/kill.flag）
  - ExecutionEngine は kill.flag の存在を検知して安全停止することを想定
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨（誤って自動クリアさせない）

- PID ファイル
  - run_execution は data/execution.pid（execution 起動時の PID）を /settings.pid_file_path を使用して処理

---

## 開発用ツール・ユーティリティ

- config_setup: .env 対話式生成（python -m kabusys.config_setup）
- validate_config: .env と config/*.yaml の簡易検証（python -m kabusys.validate_config）
- paper_verification_report: ペーパートレード検証レポート生成
- ロギング設定: kabusys.utils.logging_setup.setup_logging を呼ぶことで統一されたログ出力を得られます
- プロセス優先度: kabusys.utils.process_priority.set_process_priority で起動時に優先度を上げる（実行スクリプト内で既に呼び出されます）

---

## 主要な環境の挙動メモ

- Monitoring は監視用 sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）
- ExecutionEngine は KABUSYS_ENV=paper_trading のときに paper_sqlite_path を使い、MockBrokerClient を選択します（本番 DB と完全分離）
- OpenAI を利用する機能（news_nlp, regime_detector 等）は OPENAI_API_KEY を必要とします。API の失敗は冪等的に扱うようフェイルセーフ設計（スコア 0 にフォールバック等）が実装されています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — Settings: 環境変数読み込み・検証・デフォルト
- config_setup.py — .env 対話式ウィザード（CLI）
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite 用永続化層（テーブル初期化 / read/write）
  - system_monitor.py — システム稼働 / データ鮮度監視
  - trade_monitor.py — （約定 / 注文監視）※ソースに含まれるがここでは割愛
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — Kill Switch 実装
  - alert_manager.py — （アラート送信管理）※実装参照
- execution/ — Execution 系コンポーネント（Engine, OrderManager, RiskManager 等）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py — ファクター計算
  - feature_exploration.py — IC / 統計解析
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — レジーム判定（MA + マクロセンチメント）
- data/ — 既定のデータディレクトリ（DB / フラグ / PID 等を置く想定）
- logs/ — ログファイル出力先（デフォルト）

（実際のリポジトリにはさらに多くのモジュールがあり、上は主要ファイルの抜粋です）

---

## 最後に（運用上の注意）

- .env は機微な情報を含むため絶対にリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）での起動前に必ず validate_config を実行し、LINE 通知等の設定を確認してください。
- Kill Switch / stop_requested.flag の運用ルールをチームで定めておくと安全です。
- OpenAI API を運用で使う際は料金・レート制限に注意してください（リトライ / バックオフは実装済みですが注意は必要です）。

---

必要があれば README をさらに拡張して、具体的な .env のサンプル（.env.example の内容）、起動時の systemd / Supervisor の unit サンプル、Docker イメージ化手順、テスト実行方法などを追加します。どの情報が必要か教えてください。