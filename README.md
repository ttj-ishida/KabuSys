# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリです。
戦略・ポートフォリオ構築、実行エンジン、監視・アラート、AI を用いたニュース解析などの主要コンポーネントを含みます。

以下はこのコードベースの概要、主な機能、セットアップと実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要
- 目的: 日本株自動売買に必要なコンポーネント（シグナル生成、ポートフォリオ構築、発注管理、監視、レポート、AIベースのニューススコアリング）を提供する。
- 設計方針:
  - 本番・ペーパートレードを環境変数で切り替え（KABUSYS_ENV）。
  - DuckDB を分析用 DB、SQLite を監視・注文ログ用 DB として利用。
  - 外部 API 呼び出し（OpenAI 等）は明示的な API キーで制御。
  - 可能な限りフェイルセーフ（API失敗時のフォールバック、部分書き込みで既存データ保護等）。

---

## 主な機能一覧
- 環境設定
  - 対話式の .env 作成ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）

- 実行エンジン
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - 本番（live）/ペーパートレード（paper_trading）切替
  - ペーパートレード時は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）

- 監視
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせた MonitoringEngine
  - run_monitoring スクリプトでポーリング監視を実行
  - 監視結果・リスクイベントの永続化（SQLite） — monitoring_db モジュール
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止を促す）

- ポートフォリオ構築
  - 候補選定、等配分・スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め・利用可能現金でスケーリング）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）連携
  - ニュース記事のセンチメントスコア化（kabusys.ai.news_nlp）
  - マクロニュースと価格指標を組み合わせた市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI 呼び出しは API キー必須。失敗時はフォールバック動作。

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発用）
1. リポジトリをクローンし、作業ディレクトリに移動
   - git clone ...
   - cd <project-root>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt はこの配布サンプルに含まれていませんが、実行に必要な代表的パッケージは:
     - duckdb
     - psutil
     - openai
     - PyYAML（任意、config YAML の検証用）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 環境変数（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに `.env` を手動で作成。
   - 必須環境変数（少なくとも以下を設定）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他主要変数（デフォルト値は README 内や Settings 参照）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 時）
     - OPENAI_API_KEY — OpenAI を利用する場合に必要
     - LOG_LEVEL — INFO 等

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）

6. data ディレクトリ
   - 実行中に PID/flag ファイルや DB が data/ 以下に作成されます。必要なら事前に作成しておく。

---

## 実行方法（代表的なコマンド）
- 監視を起動する（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。
  - 備考:
    - run_monitoring は Monitoring の DB に接続する際、KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
    - 起動時にプロセス優先度を "high" に設定します（可能な場合）。

- ExecutionEngine を起動する（注文エンジン）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定します。
    - 実行中は data/execution.pid や data/stop_requested.flag を利用して停止検出を行います。

- ペーパートレード検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- その他ユーティリティ
  - python -m kabusys.config_setup     （.env 対話ウィザード）
  - python -m kabusys.validate_config  （設定検証）

---

## 停止・Kill の仕組み
- 停止フラグ（外部からの停止要求）
  - data/stop_requested.flag
    - run_monitoring と run_execution はこのファイルの存在を定期的にチェックして自発的に終了します（停止フラグを作成すると安全に停止）。
- Kill Switch（監視による強制停止）
  - KillSwitch は監視ロジックの結果（ドローダウン超過やポジション上限超過など）により data/kill.flag を書き込みます。
  - ExecutionEngine は kill.flag を検査して自動停止する実装になっている想定です（KillSwitch による停止シグナル）。
- 実行時クリーンアップや kill.flag の自動クリアは Settings の KILL_FLAG_CLEAR_ON_START にて制御可能（本番環境では 0 推奨）。

---

## 主な設定環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading の約定シミュレーション（instant, partial, never, reject）

詳細は kabusys.config.Settings クラスをご確認ください（バリデーションやデフォルト値が記載されています）。

---

## 使い方（簡単なワークフロー）
1. .env を作成して必要な環境変数を設定する（config_setup を推奨）。
2. 設定検証: python -m kabusys.validate_config
3. DuckDB / SQLite の初期データや config/*.yaml を用意（必要に応じて scripts 等を利用）。
4. 監視を起動（常時監視）:
   - python -m kabusys.run_monitoring
5. 実際の発注セッションを起動（またはペーパートレード）:
   - python -m kabusys.run_execution
6. 運用中は data ディレクトリ内のログ / DB / flag ファイルを確認・管理する。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys の主要なモジュール一覧（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（.env の自動読み込み含む）
    - config_setup.py          — 対話式 .env ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（MA + マクロ記事の LLM）
    - monitoring/
      - monitoring_db.py       — SQLite 監視ログ永続化層
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — 注文滞留・約定異常監視
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — Kill Switch ロジック
      - monitoring_engine.py   — 複数モニタを束ねるエンジン
      - alert_manager.py       — （アラート送信管理）※実装はコード内で参照
    - execution/
      - （ExecutionEngine / OrderManager / BrokerFactory 等 — 実行関連）
    - portfolio/
      - portfolio_builder.py   — 候補選定 / 重み計算
      - position_sizing.py     — 発注株数算出
      - risk_adjustment.py     — セクターキャップ / レジーム乗数
    - research/
      - factor_research.py     — ファクター計算（momentum / value / volatility）
      - feature_exploration.py — 将来リターン・IC・統計サマリー
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - utils/
      - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
    - data/                     — 実行時生成ファイル（DB, pid, flag 等）
    - config/                   — YAML 設定ファイル群（system_config.yaml 等）

---

## 運用上の注意・推奨
- 本番環境での KABUSYS_ENV=live 設定時は、LINE 通知や KILL_FLAG_CLEAR_ON_START 等の設定を慎重に確認してください（validate_config が警告を出します）。
- .env は機密情報を含むため Git にコミットしないでください。
- OpenAI API を利用する機能は API キーとコストに注意して運用してください（呼び出し回数やレート制限によりリトライが発生します）。
- ペーパートレード用 DB は本番 DB と必ず分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

README はコードベース全体の導入・運用のための概要をまとめたものです。内部の API 詳細や追加の実行オプション、依存関係は各モジュールの docstring（コード内コメント）を参照してください。必要であれば、特定モジュール（例: ai.news_nlp の挙動、ExecutionEngine の設定項目など）の詳細なドキュメントを別途作成します。