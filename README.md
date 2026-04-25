# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買・リサーチ・監視を目的とした小規模なシステム群です。戦略のリサーチ、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI を使ったニュース評価などのコンポーネントを含みます。

以下はこのリポジトリの README（日本語）です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード (.env)
  - 設定検証
  - 実行エンジン起動（Execution）
  - 監視ループ起動（Monitoring）
  - ペーパートレード検証レポート
  - AI 関連機能（ニュース NLP / レジーム判定）
- 主要環境変数（抜粋）
- 注意事項
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は次を目的としています。

- データ（DuckDB）を用いたファクター計算 / リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- ExecutionEngine による発注管理（本番 / ペーパートレード対応）
- システムの状態・注文状況・リスク監視とアラート（Kill Switch）
- ニュースを LLM（OpenAI）で評価してスコア化する機能
- ペーパートレード結果の検証レポート生成ツール

設計方針の一部：
- DB（SQLite / DuckDB）やログはファイルベースで管理し、環境変数でパスを上書き可能
- 本番・ペーパートレードを明確に分離（DB も分離）
- LLM 呼び出しは明示的な API キーを要求し、失敗はフォールバックして続行するフェイルセーフ設計

---

## 機能一覧

主な機能（実装済み）：

- 設定管理
  - .env ファイル自動読み込み（プロジェクトルートに基づく）
  - Settings クラスで環境変数をラップ
- 設定ウィザード
  - `kabusys.config_setup` による対話式 .env 生成
- 設定検証 CLI
  - `kabusys.validate_config` による環境変数 / config/*.yaml の検証（--strict オプションあり）
- ExecutionEngine 起動スクリプト
  - `kabusys.run_execution`（KABUSYS_ENV に応じて本番/ペーパートレードを切替）
- Monitoring 起動スクリプト
  - `kabusys.run_monitoring`（定期ポーリングで各 Monitor を実行）
- Monitoring DB 層（SQLite）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
- モニタリングコンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager / MonitoringEngine
- ポートフォリオ構築ユーティリティ（純粋関数）
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ機能（DuckDB を利用）
  - モメンタム・バリュー・ボラティリティ等の計算、将来リターン・IC・統計サマリー
- AI 機能
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア付与（ai_scores への書き込み）
  - レジーム判定（ETF の MA とマクロニュースの LLM 評価を合成）
- ツール
  - ペーパートレード検証レポート（期間指定でサマリを出力）

---

## セットアップ手順

1. Python 環境を準備
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

2. 必要パッケージをインストール
   - 依存ライブラリ（実際の requirements.txt がないため、少なくとも以下は必要です）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に自分で作成
   - 最小必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

4. （任意）ログ / data ディレクトリを作成
   - デフォルトでログは `logs/` に出力されます（設定可能）
   - 各種 DB は `data/` 下のデフォルトパスを使用します（存在しない場合は作成されます）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - エラーがないか、--strict オプションで警告をエラー扱いにすることも可能:
     - python -m kabusys.validate_config --strict

---

## 使い方

以下は主要なモジュールの実行方法と重要オプションの説明です。いずれもパッケージルート（src 配下がパッケージ化されている場合）で実行します。

- 環境変数読み込みについて
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` / `.env.local` を自動読み込みします。
  - 自動読み込みを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### 環境設定ウィザード（.env 作成）
- 実行:
  - python -m kabusys.config_setup
- 説明:
  - 対話式で主要な環境変数を作成 / 更新します。
  - 完了後は python -m kabusys.validate_config で確認してください。

### 設定検証
- 実行:
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

### ExecutionEngine（発注エンジン）起動
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - Settings.KABUSYS_ENV を参照して paper_trading（ペーパー）か live（本番）かを切り替えます。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用しデータは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH で上書き可）に記録され、本番 DB とは分離されます。
  - プロセス優先度を high に設定し、Engine のスレッドをデーモンで起動します。
  - 起動中に `data/stop_requested.flag` が置かれると Engine を停止します（同様に kill.flag を使った停止も別途あります）。

- 重要ファイル:
  - PID ファイル: デフォルト `data/execution.pid`（Settings.pid_file_path）

### Monitoring（監視）起動
- 実行:
  - python -m kabusys.run_monitoring
- 挙動:
  - SystemMonitor（CPU/メモリ/Disk/プロセス状態/データ鮮度）や TradeMonitor / RiskMonitor をポーリングして DB に記録・アラート判定を行います。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルトは 60 秒。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視記録を残します（監視 DB は production path を参照する仕様）。
  - プロセス優先度を high に設定します。
  - 停止判定: プロジェクトルートの `data/stop_requested.flag` を検出するとループを終了します。

### ペーパートレード検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で指定している場合は省略可能）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを表示し PASS/FAIL 判定を行います。

### AI 機能（ニュース NLP / レジーム判定）
- ニュース NLP（銘柄別スコア付与）
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 必要: OpenAI API キー（引数または環境変数 OPENAI_API_KEY）
  - 出力: ai_scores テーブルへ書き込み
- レジーム判定
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）の ma200 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルに書き込み

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の fill モード（instant | partial | never | reject）デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用。デフォルト 60）
- KILL_FLAG_PATH: kill.flag のパス（Settings.kill_flag_path）。デフォルト data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

---

## 注意事項 / 運用メモ

- .env は秘匿情報を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。
- Monitoring は監視 DB に本番 path を使うため、開発中に誤って本番 DB を上書きしないよう注意してください。
- OpenAI 等の外部 API 呼び出しは失敗時にフォールバックして処理を継続する設計ですが、API 利用料やレート制限に注意してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテート（30日保存）されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py  (バージョン情報等)
  - config.py  (環境変数と Settings クラス、.env 自動読み込み)
  - config_setup.py  (対話式 .env 作成ウィザード)
  - validate_config.py  (設定検証 CLI)
  - run_execution.py  (ExecutionEngine 起動スクリプト)
  - run_monitoring.py  (Monitoring 起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py  (ペーパートレード検証ツール)
  - ai/
    - __init__.py
    - news_nlp.py  (ニュース NLP スコアリング)
    - regime_detector.py  (市場レジーム判定)
  - monitoring/
    - monitoring_db.py  (SQLite テーブル作成・永続化ユーティリティ)
    - system_monitor.py
    - trade_monitor.py  (存在するがここでは省略)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py  (アラート送信ロジック、詳細はコード参照)
  - execution/ (発注周りの実装群: broker_factory, execution_engine, order_manager, risk_manager, etc.)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に使用されるデフォルトディレクトリ: data/*.db, pid/flag ファイル 等)

---

必要に応じて README の各セクションを拡張して、より具体的な実行例、systemd ユニット例、CI 設定、テスト方法などを追加できます。必要であればその内容で追記します。