# KabuSys

日本株自動売買システムの軽量ライブラリ / 実行スクリプト群。  
このリポジトリは、シグナル生成・ポートフォリオ構築・注文発行（ExecutionEngine）・監視（Monitoring）・研究用ファクター計算・AI を使ったニュース評価などの機能を含むモジュール群で構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（実行例）
- 主要な環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買運用に必要な要素をモジュール化したプロジェクトです。  
主な目的は以下のとおりです。

- 戦略／ファクター計算（DuckDB 上の時系列データを参照）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- ExecutionEngine（ブローカークライアント経由での注文発行）
  - 本番（live） / ペーパートレード（paper_trading）を区別
- Monitoring（システム状態・発注ログ・リスク監視・Kill Switch）
- AI（OpenAI を利用したニュースセンチメント評価や市場レジーム判定）
- 研究用ユーティリティ（IC 計算、ファクター統計など）
- 開発時の支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動読込（プロジェクトルート判定）
  - 対話式環境設定ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
- Execution
  - run_execution スクリプト（ExecutionEngine 起動、paper_trading 時は MockBrokerClient、専用 DB を使用）
  - 注文管理・リスク管理（OrderManager, RiskManager, Reconciler 等）
- Monitoring
  - run_monitoring スクリプト（SystemMonitor のポーリング、MONITOR_POLL_INTERVAL で間隔制御）
  - MonitoringDB: SQLite にシステム状態・発注ログ・リスクログ等を永続化
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - RiskMonitor / TradeMonitor / SystemMonitor / MonitoringEngine
- ポートフォリオ構築
  - 候補選定（select_candidates）、重み計算（等重・スコア重み）
  - セクター制限、レジームによる乗数、ポジションサイズ決定（lot 丸め、利用可能資金に対するスケーリング）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ETF の MA とマクロニュースを組み合わせて market_regime を判定・保存
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを生成

---

## セットアップ手順

前提
- Python 3.9+（本コードは typing の新構文などを使用）
- OS: Linux / macOS / Windows（ただし一部プロセス優先度設定は権限や OS に依存します）

依存パッケージ（代表例）
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- その他（標準ライブラリ以外のものは requirements.txt があればそちらを参照）

例: pip インストール
```
pip install duckdb psutil openai PyYAML
```

リポジトリの初期設定
1. プロジェクトルートに移動（.git または pyproject.toml がルート検出に使われます）。
2. 対話式に .env を作成する（推奨）:
   ```
   python -m kabusys.config_setup
   ```
3. 設定の検証:
   ```
   python -m kabusys.validate_config
   ```
   警告も FAIL にしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

データディレクトリ
- デフォルトで使用するファイル:
  - data/kabusys.duckdb （DuckDB）
  - data/monitoring.db （監視用 SQLite）
  - data/paper_trading.db （ペーパートレード専用 SQLite）
  - data/execution.pid（ExecutionEngine の PID ファイル）
  - data/kill.flag（Kill Switch）
  - data/stop_requested.flag（起動済みスクリプトを停止させる外部フラグ）

ログ
- デフォルトログディレクトリ: logs/
- ログは daily ローテート（30 日分保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一

注意: 自動 .env 読込は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

---

## 使い方（主な実行例）

1. ExecutionEngine を起動（本番は KABUSYS_ENV=live、ペーパートレードは paper_trading）
   - ペーパートレードでは MockBrokerClient を使い、DB は data/paper_trading.db に分離されます。
   ```
   python -m kabusys.run_execution
   ```
   実行中に外部から停止したい場合:
   - data/stop_requested.flag を作成すると run_execution は検知して安全終了します。
   - Kill Switch（監視側）によって data/kill.flag が書かれると ExecutionEngine は停止されます。

2. Monitoring を起動
   - MONITOR_POLL_INTERVAL 環境変数でループ間隔（秒）を上書き可能（デフォルト 60 秒）。
   ```
   python -m kabusys.run_monitoring
   ```
   停止は同様に data/stop_requested.flag を作成、Ctrl+C（KeyboardInterrupt）でも停止します。

3. .env を対話的に作成 / 更新
   ```
   python -m kabusys.config_setup
   ```

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```

5. ペーパートレードの検証レポート
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   DB パスはオプション --db か環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

6. AI スコアリング・レジーム判定（プログラムから呼び出す）
   - news_nlp.score_news(conn, target_date, api_key=...)
   - regime_detector.score_regime(conn, target_date, api_key=...)
   など、DuckDB 接続を渡して呼び出します。OpenAI API キーは OPENAI_API_KEY 環境変数でも指定できます。

---

## 主要な環境変数（抜粋）

必須（運用に応じて設定）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

動作モード
- KABUSYS_ENV — execution/monitoring の動作モード:
  - development / paper_trading / live（デフォルト: development）

データベース・ログ
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）

AI / OpenAI
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）

監視関連
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

ペーパートレード挙動
- PAPER_FILL_MODE — MockBrokerClient の約定モード（instant / partial / never / reject、デフォルト: instant）

その他
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## 停止 / Kill フロー

- run_monitoring / run_execution は起動時に data/stop_requested.flag の存在をチェックします。運用者が速やかに起動スクリプトを終わらせたい場合はこのフラグを作成してください。
- Monitoring の KillSwitch は条件（ドローダウン超過・ポジション上限超過など）を満たすと data/kill.flag を作成します。ExecutionEngine は kill.flag の存在を検知して注文を停止します。
- ExecutionEngine 側での起動時オプションにより、KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に kill.flag を自動削除する挙動になります（本番では無効推奨）。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - execution/                 — 発注エンジン関連（OrderManager 等）
      - (OrderManager, ExecutionEngine, broker_factory, risk_manager, ... )
    - monitoring/
      - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py     — 候補選定・重み付け
      - position_sizing.py       — 株数決定・スケーリング
      - risk_adjustment.py       — セクター制限・レジーム乗数
    - research/
      - factor_research.py      — Momentum/Value/Volatility 計算
      - feature_exploration.py  — forward returns / IC / summary
    - ai/
      - news_nlp.py             — OpenAI を用いたニュースセンチメント評価
      - regime_detector.py      — 市場レジーム判定
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート生成
    - data/ (実行時生成・運用)
      - *.db, *.flag, *.pid
- config/
  - *.yaml（system_config.yaml 等。validate_config で参照）

---

## 補足 / 開発者向けノート

- DuckDB は分析向けの DB として使用し、prices_daily や raw_financials、raw_news 等の大規模時系列データを高速に処理します。
- MonitoringDB（SQLite）は軽量な永続化層として採用。テーブル作成・マイグレーションは init_monitoring_db() により冪等に実行されます。
- AI 関連は OpenAI API（gpt-4o-mini 等）を前提としています。API の失敗時は安全側フォールバック（0.0 またはスキップ）を行うよう実装されていますが、API キーとコスト管理に注意してください。
- テスト環境では KABUSYS_ENV=paper_trading を利用すると本番 DB と分離され、MockBrokerClient による発注評価が行われます。

---

必要があれば、README に含める実行コマンド例や環境変数テンプレート（.env.example）、依存パッケージリスト（requirements.txt）を追加で作成します。どの情報を追加したいか教えてください。