# KabuSys

日本株向け自動売買プラットフォームの一部実装（ライブラリ・起動スクリプト・ツール群）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI補助（ニュースNLP / レジーム判定）などのコンポーネントを含みます。

以下は本コードベースの概要、主要機能、導入手順、使い方、ディレクトリ構成の README です。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ解析（DuckDB を使ったファクター計算・研究用関数）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- 発注実行（ExecutionEngine / Broker クライアントの抽象化）
- 監視（System / Trade / Risk のポーリング、kill flag による強制停止）
- AI 補助（OpenAI を用いたニュースセンチメント評価・レジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、ログ設定、プロセス優先度制御）
- 運用ツール（ペーパー取引検証レポート生成など）

設計上の特徴：
- 環境変数による設定管理（.env をサポート）
- 本番 / ペーパートレードで DB を分離（paper_trading 環境）
- フェイルセーフ指向（API失敗時のフォールバック、部分的書き込みで既存データ保護）
- ロギングは stdout と日次ローテーションファイルに出力

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution: ExecutionEngine を起動して発注セッションを実行
  - run_monitoring: SystemMonitor をポーリングして監視ログを保存
- 設定管理
  - config_setup: 対話式に .env を生成/更新
  - validate_config: .env・config/*.yaml の基本チェック（--strict オプションあり）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - kill_switch: 条件に応じて data/kill.flag を書き込み Execution に停止指示
  - monitoring_db: SQLite ベースの監視ログスキーマ（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ
  - 候補選定、等重/スコア重み、ポジションサイズ算出、セクター制限、レジーム乗数
- 研究 / リサーチ
  - factor_research: モメンタム / バリュー / ボラティリティ等の計算（DuckDB 利用）
  - feature_exploration: 将来リターン・IC・統計サマリー
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント評価（ai_scores への書き込み）
  - regime_detector: ETF + マクロニュースで市場レジームを判定
- ツール
  - paper_verification_report: ペーパートレード DB からパフォーマンス / 安定性の検証レポートを生成

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン・プロジェクトルートに移動
   - プロジェクトルートには `pyproject.toml` や `.git` がある想定

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がない場合は主要依存をインストールしてください（例）:
     - pip install duckdb psutil openai
   - （任意）PyYAML をインストールすると validate_config が YAML の中身検証を行えます:
     - pip install pyyaml

4. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成（.env.example を参照してください）
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（デフォルト: INFO）
   - 設定を検証:
     - python -m kabusys.validate_config
     - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

5. データディレクトリの準備（必要に応じて）
   - data/ ディレクトリはログ・DB・PID/flag 用に使用されます。起動時に自動作成されることが多いですが、権限などで作成できない場合は手動で作成してください。

---

## 使い方（主要スクリプトとオプション）

- 実行（モジュールとして）
  - 監視ループを起動:
    - python -m kabusys.run_monitoring
    - 環境変数でポーリング間隔を変更: export MONITOR_POLL_INTERVAL=30
    - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます（監視は運用 DB を見ます）
  - 発注エンジンを起動:
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離します
  - 設定ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB パス指定:
      - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- 停止 / Kill Switch
  - 強制停止（ExecutionEngine 停止）:
    - KillSwitch は条件に応じて `data/kill.flag` を生成します。ExecutionEngine は起動時や定期チェックでこのファイルを確認して停止する実装を組み込む想定です。
  - 停止リクエスト（運用用簡易フラグ）:
    - `data/stop_requested.flag` が存在すると run_monitoring や run_execution のループを抜けます（起動中のプロセスを優雅に終了させるため）。
  - PID ファイル:
    - ExecutionEngine はデフォルト `data/execution.pid` に PID を書きます（設定で変更可）。

- ロギング
  - 共通のユーティリティ `kabusys.utils.logging_setup.setup_logging` により標準出力（stdout）と日次ローテーションファイル（logs/<app>.log）に出力されます。
  - ログレベルは環境変数 `LOG_LEVEL` か引数で指定可能。ログディレクトリは `LOG_DIR` で変更できます（デフォルト: logs/）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意、本番では必須推奨）
- KABUSYS_ENV — 実行環境（development | paper_trading | live。デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — MockBroker のフィルモード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリを上書き（デフォルト: logs/）
- PID_FILE_PATH — Execution PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト: "0"）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

---

## 実運用上の注意事項

- 本番実行時は必須環境変数（特に API シークレット）を適切に設定してください。`.env` をリポジトリにコミットしないでください。
- KABUSYS_ENV=live の際は validate_config で警告を必ず確認してください（LINE 通知や Kill Switch の設定など）。
- run_monitoring は監視専用に本番の SQLite パス（SQLITE_PATH）を参照します。監視ログとペーパートレードログは分離されます（paper_trading モード）。
- OpenAI を使う機能は API レート制限や料金が発生するため、API キーと呼び出し頻度に注意してください。API 失敗時はフェイルセーフでスコア0.0などにフォールバックする設計になっていますが、想定外の副作用を避けるため運用ルールを定めてください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定取得ユーティリティ（Settings クラス）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI）による ai_scores 書き込みロジック
  - regime_detector.py       — レジーム判定（ETF + マクロニュース）
- monitoring/
  - monitoring_db.py         — SQLite スキーマ & 永続化 API（MonitoringDB）
  - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - system_monitor.py        — システム / データ鮮度監視
  - risk_monitor.py          — ドローダウンとポジション上限監視
  - kill_switch.py           — kill.flag の生成 / 管理
  - (trade_monitor 等 他モジュール)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py         — ロギング設定
  - process_priority.py      — プロセス優先度 / CPU affinity
- monitoring/、execution/、data/ 等の実装ファイル群（詳細はコード参照）

プロジェクトルート（参考）
- .env.example
- pyproject.toml / setup.cfg など（該当する場合）
- data/                     — DB / pid / flag を置くデフォルトディレクトリ
- logs/                     — ログ出力先（デフォルト）

---

## 開発者向けヒント

- DuckDB 接続を渡してデータ処理関数（research.*）を呼ぶことで、ローカルで高速にリサーチが可能です。
- AI 関連機能はテスト時に API 呼び出し部分をモック可能（モジュール内で明示的に _call_openai_api を分離しているため、patch で差し替えやすい構造）。
- validate_config は起動前チェックに便利です。--strict モードでは警告も失敗扱いになります。
- ロギングは全体で共通関数を使うことで一貫したログ出力になります。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

---

README に書かれている以外の詳細は各モジュールの docstring / コメントをご参照ください。必要であればこの README を元にデプロイ手順（systemd ユニット例、Dockerfile、CI/CD）や運用ドキュメントを追加します。