# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアモジュール群を含みます。戦略・ポートフォリオ構築・実行エンジン・監視・リサーチ・AI 補助（ニュース NLP / レジーム判定）などの機能を備えています。

---

## 概要

KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine：発注・注文管理・リスク制御を担当する実行エンジン（paper/live 両対応）
- Monitoring：システム稼働・データ鮮度・注文状況・リスクを定期チェックし、Kill Switch を発動可能
- Portfolio：候補選定、重み付け、ポジションサイジング、セクター制限等の純粋関数ライブラリ
- Research：ファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析ユーティリティ
- AI：ニュースセンチメント（OpenAI ベース）やレジーム判定の補助モジュール
- Tools：ペーパートレード検証レポート生成などのユーティリティスクリプト
- CLI：設定ウィザード・設定検証ツールなど実行・運用に便利なスクリプト群

設計方針として、DB（DuckDB / SQLite）を用いたデータ永続化や、外部 API（kabuステーション / J-Quants / OpenAI）への最小限の依存、運用時の安全装置（Kill Switch、停止フラグ、ログ回転など）を重視しています。

---

## 機能一覧（主なもの）

- 設定管理（.env 自動読み込み / config ウィザード）
- 実行エンジン起動（paper_trading と live の切替）
- モニタリングループ（CPU/メモリ/Disk、プロセス生存確認、データ鮮度）
- リスク監視（ドローダウン、ポジション上限・ログ保存）
- Kill Switch（条件を満たしたら data/kill.flag を作成して ExecutionEngine を停止）
- News NLP（OpenAI を使った銘柄別センチメント集約 & ai_scores 書込み）
- Market Regime 判定（ETF MA とマクロニュースを合成）
- Portfolio 構築（候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限）
- Research ツール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- Paper Trading の検証レポート生成（成功率、レイテンシ、稼働率評価）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | 記法を使用）
- Git リポジトリをクローンし、プロジェクトルートに移動

推奨インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を行う場合）pip install PyYAML
   - （その他、使用する Broker クライアント等は適宜追加）

※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください（本リポジトリに無い場合は上記参照パッケージを導入）。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は `--strict` を付与

5. データディレクトリ
   - デフォルトでは data/ 以下に SQLite / PID / フラグファイルが作成されます。必要があれば .env でパスを上書きしてください。

---

## 使い方（主要コマンド）

プロジェクトルートで実行することを前提に例を示します。

- 環境設定ウィザード（.env の生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 起動中に data/stop_requested.flag を作成すると安全に停止できます

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を参照します（監視データは統一DB）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ライブラリ関数（プログラム内で利用）
  - ai のニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログ出力ディレクトリは環境変数 LOG_DIR または setup_logging の引数で変更可能です。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading では ExecutionEngine が専用 Paper DB を使用
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — Paper Broker の約定動作（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START — 実行開始時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動でプロジェクトルートの .env を読み込まない

注意:
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。
- 自動読み込み無効化が必要なテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 運用上のファイル・フラグ

- data/kill.flag — Kill Switch が起動した際に書き込まれる停止指示ファイル
- data/stop_requested.flag — run_*.py スクリプトが検知して安全にループを抜ける停止フラグ
- data/execution.pid — ExecutionEngine の PID ファイル（デフォルトパスは Settings.pid_file_path）
- logs/<app>.log — 日次ローテーションされるログファイル

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・ディレクトリです（主要モジュールに限定）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py        — （存在する想定。注文滞留・異常判定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （通知用抽象）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - broker_factory.py       — Broker クライアント生成（Mock/実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（他実行関連モジュール）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

（フル構成はソースツリーを参照してください。）

---

## トラブルシューティング（よくある問題）

- OpenAI キー未設定
  - ai モジュールを使う場合は OPENAI_API_KEY を設定してください。関数は引数で上書き可能です。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない
  - validate_config は親ディレクトリがない場合に警告を出します。起動時に自動作成されることが多いですが権限の問題に注意してください。
- permission エラー
  - PID / フラグ / DB ファイル作成に対して書き込み権限が必要です。サービス化する場合は実行ユーザーの確認を行ってください。
- プロセス優先度の設定に失敗
  - set_process_priority はプラットフォームや権限により AccessDenied になることがあります（ログに警告が出ますが処理は継続します）。
- 監視が本番 DB を参照する理由
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。監視用 DB を別にしたい場合はパスを環境変数で変更してください。

---

## 開発メモ / 注意点

- 多くのユーティリティ関数は副作用を持たず純粋関数として実装されています（ポートフォリオ / position sizing 等）。モジュール間の依存は最小限に抑えられています。
- AI 呼び出しはリトライ・バックオフ・レスポンス検証を実装しており、失敗時はフェイルセーフ（スコア 0 やスキップ）で続行します。
- 本番起動時は KABUSYS_ENV=live とし、LINE 通知や kill flag の設定を十分に確認してください（validate_config の live ガードを参照）。

---

必要に応じて README を拡張します。特にデプロイ手順（systemd / Supervisor / コンテナ化）、テスト方法、CI / CD、外部 Broker の設定方法などを追加したい場合は指示をください。