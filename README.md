# KabuSys

日本株向け自動売買システムのライブラリ / 起動スクリプト群です。  
本リポジトリは以下を含みます：戦略構築・ポートフォリオ構成ロジック、Research（ファクター計算・特徴量探索）、AI 製のニュース NLP / レジーム判定、Execution エンジン起動スクリプト、Monitoring（監視・Kill Switch）など。

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコンポーネント群を提供します。主な目的は次の通りです。

- 戦略に基づく銘柄選定と配分（portfolio）
- ポジションサイジング、リスク制御（position_sizing / risk_adjustment）
- DuckDB を用いたファクター計算・リサーチ（research）
- OpenAI を用いたニュースセンチメント評価（ai/news_nlp）と市場レジーム判定（ai/regime_detector）
- 実行エンジン起動スクリプト（run_execution.py）および監視用ポーリング（run_monitoring.py）
- 監視 DB（SQLite）と監視ロジック（monitoring/*）、Kill Switch による自動停止
- 各種ユーティリティ（ログ設定・プロセス優先度など）
- ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）
- 環境設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）

注意：実際の発注には外部 API（kabuステーション等）と資格情報が必要です。ペーパートレードモードやテスト用のモックが用意されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live を切替）
  - run_monitoring.py : SystemMonitor をポーリングして監視ログを記録
- 設定管理
  - config_setup.py : .env を対話形式で作成・更新
  - validate_config.py : .env と config/*.yaml の基本チェック
  - config.Settings : 環境変数ラッパー（デフォルト値・バリデーション）
- モニタリング
  - monitoring/monitoring_db.py : SQLite による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py
  - AlertManager 等を通じた通知フック（LINE 等を利用可能）
- ポートフォリオ構築（純関数）
  - portfolio.portfolio_builder: 候補選定・重み算出
  - portfolio.position_sizing: 株数算出（ロット丸め・スケーリング）
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- Research（DuckDB 前提）
  - research.factor_research: momentum / volatility / value 等のファクター計算
  - research.feature_exploration: 将来リターン / IC / 統計サマリ
- AI（OpenAI）
  - ai.news_nlp: ニュースを LLM でスコアリングし ai_scores テーブルへ書込
  - ai.regime_detector: 1321 の MA200 とマクロニュースでレジーム判定し market_regime に保存
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、プロジェクトルートへ移動
   - 本リードミーは `src/` 配下の Python パッケージを前提としています。プロジェクトルートが `.git` や `pyproject.toml` を持つ構成を想定。

2. 仮想環境を作成・有効化（例: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須（開発時に最低限必要となる想定パッケージ）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （実運用では他に HTTP クライアントや kabu API クライアントが必要）

4. .env の作成
   - 推奨: 対話式ウィザードを実行して .env を生成
     - python -m kabusys.config_setup
   - 必須環境変数の例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使用する場合）
   - 自動ロード:
     - デフォルトでプロジェクトルートの `.env` と `.env.local` を自動読み込みします（OS 環境変数優先）。
     - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意だが強く推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリ
   - デフォルトで SQLite / DuckDB / logs は `data/` / `logs/` に作られます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を変更してください。

注意: 本番運用時は KABUSYS_ENV を `live` に設定し、設定・権限を慎重に管理してください。

---

## 使い方（よく使うコマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 DB（デフォルト data/paper_trading.db）に記録されます。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成すると安全に停止できます（起動中のスクリプトはこのフラグを監視します）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使用します。
  - 停止: data/stop_requested.flag を設置するとループが終了します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数を優先）

- プログラム的に利用（例）
  - DuckDB 接続を作って research / ai 関数を呼ぶ:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.research import calc_momentum
    - recs = calc_momentum(conn, date(2026, 4, 1))

- ログ
  - デフォルトのログ出力先: logs/<app_name>.log（setup_logging により stdout + 日次ローテートファイル）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- PAPER_FILL_MODE — ペーパートレードのフィルモード（instant | partial | never | reject）

---

## ディレクトリ構成

以下は主要なファイル・ディレクトリの構成（src 以下を想定）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py     — ペーパートレード検証レポート CLI
  - ai/
    - news_nlp.py                      — ニュース NLP（OpenAI）
    - regime_detector.py               — 市場レジーム判定（OpenAI）
  - portfolio/
    - portfolio_builder.py             — 候補選定・重み
    - position_sizing.py               — 株数・スケール計算
    - risk_adjustment.py               — セクター上限・レジーム乗数
  - research/
    - factor_research.py               — ファクター計算（DuckDB）
    - feature_exploration.py           — forward returns / IC / summary
  - monitoring/
    - monitoring_db.py                 — SQLite スキーマ + 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (注: スニペット内で参照されるが実装はリポジトリに依存)
  - execution/                         — Execution 関連（broker, engine, order_manager 等）
    - (実装ファイル群)
  - utils/
    - logging_setup.py                 — 統一的ロギング設定
    - process_priority.py              — プロセス優先度・CPU affinity ユーティリティ
  - data/ (runtime)
    - *.db, kill.flag, stop_requested.flag, execution.pid などが置かれる
- config/
  - system_config.yaml, data_config.yaml, ... （運用用 YAML 設定ファイル）

---

## 運用上の注意点 / 実装上のポイント

- Kill Switch
  - RiskMonitor が閾値を超えるなどの条件で kill.flag を書くと ExecutionEngine に停止シグナルが送られます。KILL_FLAG_CLEAR_ON_START を本番で 1 に設定するのは危険です。
- データベースの分離
  - paper_trading モードでは paper_trading 用 SQLite（デフォルト data/paper_trading.db）に記録され、本番の監視 DB と分離されます。
- ロギング
  - 全起動スクリプトは setup_logging を呼んで stdout + 日次ローテーションログを使用します。logs ディレクトリが作成できない場合はコンソールのみで継続します。
- 環境読み込み
  - プロジェクトルート（.git／pyproject.toml があるディレクトリ）から .env および .env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite
  - research / ai モジュールは DuckDB を利用する想定です。price / raw_financials / raw_news 等のテーブルスキーマに依存します。
- OpenAI
  - AI モジュールは OpenAI API を利用します。API 呼び出しは再試行、レスポンス検証、部分失敗保護（部分成功時の DB 書込保護）等の安全策が組み込まれていますが、API キーの管理に注意してください。

---

## よくある操作フロー（例）

1. .env を作成（config_setup）
2. python -m kabusys.validate_config で設定を確認
3. 必要な DuckDB・SQLite のデータを用意（レコード投入 / ETL）
4. python -m kabusys.run_execution を起動して ExecutionEngine を開始（バックグラウンド実行）
5. 別プロセスで python -m kabusys.run_monitoring を起動して監視
6. 定期的に tools/paper_verification_report で検証レポートを生成

---

## 参考 / 補足

- コード内ドキュメント（docstring）に設計方針や注意点が多く記載されています。詳細な動作は各モジュールの docstring を参照してください。
- config/*.yaml の雛形生成スクリプト（scripts/generate_config.py）などがある想定のメッセージを validate_config が出します。プロジェクトに合わせて適宜用意してください。
- この README はソースコードのスニペットに基づく概要です。実際に運用する際はユニットテスト・統合テスト・権限管理・監査ログ等の追加対策を行ってください。

---

ライセンスや貢献ルールがある場合はプロジェクトルートに LICENSE / CONTRIBUTING を置いてください。質問や追加で載せたい内容があれば教えてください。