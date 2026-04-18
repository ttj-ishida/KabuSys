# KabuSys

日本株自動売買システムの一部（ライブラリ／起動スクリプト／ツール群）。  
このリポジトリには、ExecutionEngine（発注系）、Monitoring（稼働監視／Kill Switch）、ポートフォリオ構築・リスク調整、ファクター計算・リサーチ、AI（ニュース NLP / レジーム判定）などのモジュールが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な役割は次のとおりです。

- ExecutionEngine: ブローカーへ発注を行うエンジン（本番 / ペーパートレード切替対応）。
- Monitoring: システム稼働状況・注文状況・リスクをポーリングしてログ記録・アラート・Kill Switch を制御。
- Portfolio: 銘柄選定・重み付け・株数決定・セクター制限などの純関数ロジック。
- Research: DuckDB を用いたファクター計算・特徴量分析ユーティリティ。
- AI: ニュースに対する LLM（OpenAI）ベースのセンチメント採点や市場レジーム判定。
- Tools: ペーパートレード検証レポート等の実行スクリプト。

設計上の要点:
- 開発・ペーパートレード・本番を KABUSYS_ENV で切替可能。
- 設定は .env（自動読み込み機能あり）と config/*.yaml（任意）で管理。
- DuckDB（分析用）と SQLite（監視/ペーパートレードログ）を併用。
- ログはコンソールと日次ローテートファイルに出力。
- AI 呼び出しは OpenAI SDK を利用、失敗時はフェイルセーフで継続。

---

## 機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution — ExecutionEngine を起動（ペーパートレード環境は専用 DB を使用）
  - python -m kabusys.run_monitoring — SystemMonitor のポーリングループを起動

- 設定管理・検証
  - python -m kabusys.config_setup — 対話式 .env ウィザード
  - python -m kabusys.validate_config — .env と config/*.yaml の事前チェック（--strict オプションあり）

- 監視 / リスク管理
  - system_monitor: CPU/メモリ/Disk、Execution プロセスの存否、株価データ鮮度を監視
  - trade_monitor: 発注ログの滞留・約定異常などを検出（該当モジュールはリポジトリ内に存在）
  - risk_monitor: ドローダウン・ポジション上限を監視し、risk_logs に記録
  - kill_switch: 条件に応じて data/kill.flag を生成し ExecutionEngine に停止シグナルを送る
  - monitoring_engine: 各 Monitor を束ね、アラート／Kill Switch を統合

- ポートフォリオ構築
  - 銘柄選定（スコアソート）、等金額/スコア重み、リスクベース株数計算、セクターキャップ適用、レジーム乗数

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI
  - ニュース NLP（OpenAI を用いた銘柄別センチメントスコア生成）
  - レジーム判定（ETF MA とマクロニュースセンチメントの合成）

- ツール
  - Paper Trading の検証レポート生成: kabusys.tools.paper_verification_report

---

## セットアップ手順

以下は開発環境での一般的なセットアップ手順です。プロジェクト固有の追加手順がある場合は適宜補ってください。

前提:
- Python 3.9+（typing の演算子や型注釈を使用しているため 3.9 以上を推奨）
- Git, ネットワーク接続（OpenAI 利用時）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone … 
   - cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai
   - 推奨／任意:
     - PyYAML （validate_config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt が無い場合は上記を個別にインストールしてください。

4. 必要ディレクトリ作成
   - mkdir -p data logs

5. 環境変数の設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または直接 .env を作成。必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 代表的な環境変数:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - OPENAI_API_KEY — AI 機能の利用に必須
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
     - PAPER_FILL_MODE — ペーパートレード時の約定モード（instant|partial|never|reject）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

6. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - エラーが出た場合は .env を修正
   - --strict を付けると警告も失敗扱い（exit 1）

---

## 使い方（起動例・主要コマンド）

- ExecutionEngine を起動
  - 常用:
    - python -m kabusys.run_execution
  - ペーパートレード環境（KABUSYS_ENV=paper_trading を .env で設定）:
    - 実行時は settings.is_paper が True になり、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動前に data/kill.flag が存在する場合、エンジンは起動しません（停止フラグ検知）。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔秒を上書き（デフォルト 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path を使用（環境に関係なく本番 sqlite_path を参照する設計）

- Kill Switch の手動トリガー（実行中の ExecutionEngine を停止したい場合）
  - data/kill.flag に任意のテキストを書き込む（ファイル作成）
  - Monitoring の kill_switch が条件を満たすと同様に kill.flag を作成します
  - ExecutionEngine は起動ループで stop フラグを監視し、検出すると停止します

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可

- ロギング
  - ログ出力先: コンソール (stdout) と logs/<app_name>.log（日次ローテート、30日分保持）
  - ログディレクトリを変更するには LOG_DIR 環境変数または setup_logging の引数を利用

---

## 重要な挙動・注意点

- Settings（kabusys.config）:
  - プロジェクトルート（.git または pyproject.toml）を起点に自動で .env を読み込みます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
  - 必須環境変数が未設定の場合、多くの機能が ValueError を投げます。validate_config の使用を推奨。

- Monitoring と Execution の DB 分離:
  - run_monitoring はモニタリング用に settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します。
  - run_execution は KABUSYS_ENV=paper_trading のとき settings.paper_sqlite_path を使用し、本番 DB と分離します。

- Kill / Stop flag:
  - run_execution と run_monitoring はそれぞれ data/stop_requested.flag や data/kill.flag を監視します。
  - stop/kill フラグの有無で起動・停止を制御するため、手動でファイルを作成／削除するとプロセスの挙動が変わります。

- OpenAI 利用:
  - AI 機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要。
  - API 呼び出しで 429 / 一時的な接続エラー / タイムアウト / 5xx が発生した場合は指数バックオフでリトライし、最終的に失敗してもシステム全体は継続する設計（フェイルセーフ）。

- マイグレーション:
  - monitoring_db.init_monitoring_db は必要テーブル・インデックスを冪等に作成し、軽微なスキーマ追加（例: dashboard.peak_value, trade_logs.latency_ms）を自動で適用します。

---

## ディレクトリ構成（主要部分）

リポジトリの主要ファイル・モジュール構成（src/kabusys を起点）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py          — システム状態監視
    - trade_monitor.py           — 発注ログ監視（滞留／異常検出）※実装含む
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag の作成／評価
    - monitoring_engine.py       — 各 Monitor の統合実行ループ
    - alert_manager.py           — アラート送信管理（LINE など、実装に依存）
  - execution/
    - broker_factory.py          — ブローカークライアントの生成（実ポート／モック）
    - execution_engine.py        — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・丸め・集計キャップ処理
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py         — モメンタム/ボラ/バリュー計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py         — 市場レジーム判定（ETF MA + マクロ NLP）
    - __init__.py

補足:
- data/ — 実行時に使用する SQLite / PID / flag ファイル（リポジトリルート）
- logs/ — ログファイル

---

## 開発・貢献に関するヒント

- 単体テストやモック:
  - AI 呼び出しや外部 API はテスト時に差し替え可能（モジュール内に _call_openai_api のような抽象化があり、patch しやすい設計）。
- ローカルでの検証:
  - validate_config → run_monitoring.run_once 相当のテスト → run_execution を順に実行し、データフローとログを確認してください。
- 実運用上の注意:
  - 本番（KABUSYS_ENV=live）では LINE トークン等のアラート設定を必ず確認し、KILL_FLAG_CLEAR_ON_START は 0 を推奨します。

---

もし README に載せたい追加の例（.env のサンプル、より詳しい起動フロー、ユニットテスト実行方法、依存関係リストなど）があれば教えてください。必要に応じてサンプル .env や systemd / supervisor 用の起動ユニット例も作成できます。