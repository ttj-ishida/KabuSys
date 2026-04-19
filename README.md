# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、取引エンジン、監視（Monitoring）、研究用ファクター計算、ニュース NLP / レジーム判定、ポートフォリオ構築などの主要コンポーネントを含む自動売買システムのコードベースです。

---

## 概要

KabuSys は以下の機能を備えたモジュール式の自動売買プラットフォームです。

- 実行エンジン（ExecutionEngine）: ブローカークライアントを通じた発注管理、リスク管理、整合処理
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）監視、Kill Switch
- 研究（Research）: ファクター計算（モメンタム、バリュー、ボラティリティ等）、特徴量探索、IC計算
- ポートフォリオ構築: 候補選定・重み付け・ポジションサイジング・セクター制約等
- AI 支援: ニュース記事のセンチメントスコアリング（OpenAI を利用）、市場レジーム判定
- ツール: ペーパートレード検証レポート生成など

設計方針として、DB（DuckDB / SQLite）を利用したデータ永続化、外部 API 呼び出しは明確に分離、テストしやすい純粋関数の採用、フェイルセーフ性（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- 設定ウィザード・検証
  - `.env` を対話式に生成する CLI: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`（--strict オプションあり）
- 実行・監視
  - 実行起動スクリプト: `run_execution.py`（KABUSYS_ENV により paper_trading と本番を切替）
  - 監視起動スクリプト: `run_monitoring.py`（SystemMonitor のポーリング）
  - 停止フラグ: `data/stop_requested.flag` により外部から停止制御
  - Kill Switch: `data/kill.flag` を書き込むことで実行エンジンを停止させる仕組み
- データ・ログ
  - DuckDB（分析用）と SQLite（監視・注文ログ）を利用
  - ログは stdout と日次ローテートファイル（logs/<app>.log）に出力
- 研究用モジュール
  - ファクター計算（momentum / volatility / value）
  - forward returns / IC（スピアマン） / 統計サマリ
- ポートフォリオ構築
  - 候補選定（スコア降順）、等金額/スコア重み付け、ポジションサイズ計算、セクター上限適用
- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini 等）で解析し銘柄別スコアを生成
  - マクロニュース + ETF MA を合わせて市場レジーム判定
- 補助ツール
  - ペーパートレード検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 前提 / 推奨環境

- Python 3.9+（ソース上は型ヒント等を利用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証でオプション）
- SQLite は標準ライブラリで利用可能

（requirements.txt は本リポジトリに含まれていない想定のため、実行時に足りないパッケージを pip で追加してください。）

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン／配置する
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 必要ライブラリをインストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（下参照の必須変数を設定）
   - 自動ロード: パッケージ起動時にプロジェクトルート（.git または pyproject.toml）が見つかれば
     `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証（必須設定のチェック）
   - python -m kabusys.validate_config
   - 本番で警告も失敗としたい場合: python -m kabusys.validate_config --strict
6. 必要なディレクトリ作成
   - data/ （SQLite DB や PID/flag 保存）
   - logs/ （ログ出力）
   これらはスクリプトで自動生成される場合があるものの、権限等に注意してください。

必須環境変数（代表）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意/設定項目（config.Settings を参照）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
- PAPER_FILL_MODE（paper_trading の注文の挙動: instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか）

例（.env の最小例）:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

## 使い方（コマンド例）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV によって切り替わります:
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db を使用
    - live: 実際のブローカー API を利用
  - 実行中の停止: ファイル data/stop_requested.flag を作成すると安全に停止します。
  - エンジンは data/execution.pid を PID ファイルとして使用します。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は Settings.sqlite_path（本番 DB）を使用してログを出力します。
  - 監視ループの停止: data/stop_requested.flag を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか、PAPER_TRADING_SQLITE_PATH 環境変数で指定

- AI モジュール（プログラムから利用）
  - ニューススコアリング:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

注意点:
- OpenAI API を使う処理は API キー（OPENAI_API_KEY）が必要です。設定がない場合は例外を投げます（ただし内部でフォールバックするケースもあります）。
- モジュールはルックアヘッドバイアス回避のために date/today を直接参照しない設計になっています（target_date を引数で与える形）。

---

## 停止 / Kill Switch の仕組み

- 外部から実行停止を要求する方法
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のメインループが検知して終了します。
- Kill Switch
  - リスク監視（RiskMonitor）や MonitoringEngine 内で条件を満たすと KillSwitch が `data/kill.flag` を書き込みます。
  - ExecutionEngine は起動時にこの kill flag を見て起動を抑止したり、稼働中に kill.flag を検知して停止します。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って自動クリアしない）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 設定管理（.env 自動読み込み、Settings クラス）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI を使用）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ定義 / DB ユーティリティ
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （注文関連監視 — 本リストでは一部省略）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各モニタを束ねる
    - alert_manager.py       — （通知管理 — 実装参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring_db, order_repository 等の永続層モジュール
- data/                      — データファイル（DB, pid, flags）
  - monitoring.db (default)
  - paper_trading.db (paper mode)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                      — ログファイル（logs/<app>.log）

（注）実装ファイルはここに列挙した以外にも多くの補助モジュールが含まれます。上記は主要な構成のサマリです。

---

## 開発・運用上の注意

- .env は絶対にリポジトリにコミットしないでください（config_setup.py でも警告が出ます）。
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知などのアラート先を必ず確認してください。
- run_execution は paper_trading モードをサポートし、実際のブローカー API と分離された専用 SQLite（paper_trading.db）を使います。ペーパー環境での挙動は PAPER_FILL_MODE で制御できます。
- ロギングは共通設定関数 setup_logging を全スクリプトで呼んでいます。ログディレクトリの権限やディスク容量に注意してください。
- psutil を使ってプロセス優先度や CPU affinity を設定しますが、権限不足や OS 非対応の場合は警告を出してスキップします。
- AI (OpenAI) を使う処理は API のレートリミットや一時エラーに対してリトライとバックオフを実装していますが、費用・レート制限には注意してください。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はここまでです。実際に環境で起動する際は、`.env` の必須設定、DBパス、OpenAIキー（必要時）、ログディレクトリ、data ディレクトリのパーミッション等を事前に確認してください。必要であれば、README の拡張（依存関係リスト、起動時のデバッグ手順、ユニットテストの実行方法等）も作成できます。