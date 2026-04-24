# KabuSys

日本株向け自動売買システムの一部を抜粋したコードベースの README。  
本ドキュメントではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買/リサーチ/モニタリングを目的としたモジュール群です。  
主要機能は以下のとおりです：

- 注文実行エンジン（ExecutionEngine）およびブローカークライアント抽象化（paper_trading と live をサポート）
- 監視（Monitoring）：システム状態の定期チェック、リスク監視、Kill Switch（停止フラグ）連携、アラート送信
- ポートフォリオ構築：候補選定・重み計算・ポジションサイズ算出・セクター調整
- リサーチ：ファクター計算（モメンタム／ボラティリティ／バリュー等）、特徴量解析（IC、forward returns など）
- AI モジュール：ニュースの NLP スコアリング・市場レジーム判定（OpenAI を利用）
- ユーティリティ：設定管理、対話式 .env ウィザード、設定検証、ロギング設定、プロセス優先度設定など
- ツール：ペーパートレード結果の検証レポート生成スクリプト 等

設計方針として、外部 API（例えば証券ブローカー）へのアクセスは抽象化され、paper_trading モードでは完全に分離された専用 DB（data/paper_trading.db）を使用します。DuckDB はリサーチ／分析用に想定されています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を読み込む）
  - 対話式ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config`
- 実行系
  - 実注文エンジン起動スクリプト: `python -m kabusys.run_execution`
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
  - モニタリングループ起動スクリプト: `python -m kabusys.run_monitoring`
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 監視 / リスク管理
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文/約定ログの整合性チェックや滞留注文検出（コードベースに存在）
  - RiskMonitor: ドローダウン監視、ポジション数上限の監視、リスクイベントの永続化
  - KillSwitch: 条件を満たすと data/kill.flag を作成し ExecutionEngine を停止させる
- ポートフォリオ構築
  - 候補選定、等配分/スコア配分、リスクベースのポジションサイズ算出、セクター上限適用等
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - forward returns, IC 計算、統計サマリー 等（DuckDB を利用）
- AI
  - ニュース NLP による銘柄ごとのセンチメント算出（OpenAI API 使用）
  - 市場レジーム判定（ma200 + マクロニュースの LLM 評価を合成）
- ツール
  - ペーパートレード検証レポート: `python -m kabusys.tools.paper_verification_report`

---

## 必要な依存関係（主要）

以下はコードから推測される主要依存パッケージの一覧です（バージョンはプロジェクト側で管理する想定）。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合に必要）
- （標準ライブラリ: sqlite3, logging, pathlib, datetime, threading, math など）

pip を使ったインストール例（仮の requirements）:

pip install duckdb psutil openai PyYAML

※ 実際の requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. ソースを取得
   - git clone などでリポジトリを取得します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の準備（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env（デフォルトプロジェクトルート）を作成／更新します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番運用時は KABUSYS_ENV を `live` に設定（デフォルトは `development`）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば表示されるエラー/警告を元に修正してください。
   - --strict オプションを付けると警告も FAIL 扱いになります。

6. データディレクトリの準備
   - デフォルト DB パス等は .env に書いた値または以下のデフォルトを使用します:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - 必要に応じて空ディレクトリ `data/` と `logs/` を作成してください。`logs/` は LOG_DIR 環境変数で変更できます。

---

## 実行方法（使い方）

基本的にはモジュール単位で起動します。主要な起動とオプション例を示します。

1. ExecutionEngine（発注エンジン）起動
   - 本番/開発/ペーパートレードは KABUSYS_ENV に依存します（.env に設定）。
   - 直接起動:
     - python -m kabusys.run_execution
   - ペーパートレードで起動（環境変数を直接上書きする例）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録され、本番 DB と分離されます。
   - 実行中の停止:
     - data/stop_requested.flag が存在すると起動済みのループが検出して終了します。
     - data/execution.pid に PID 情報を持つことがあります。

2. Monitoring（監視ループ）起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     - 無効な値（0以下や非整数）はデフォルト 60 秒にフォールバックします。
   - 監視は常に本番 sqlite_path を使用（環境にかかわらず）。

3. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db /path/to/paper_trading.db
   - 簡単な例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

4. AI 関連関数（プログラムから呼び出す）
   - ニュース NLP スコア付け:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
   - 市場レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
   - OpenAI API キーは環境変数 OPENAI_API_KEY で指定するか、関数引数に渡します。

5. 設定検証とトラブルシューティング
   - 設定不足や環境変数未設定は `python -m kabusys.validate_config` で検出できます。
   - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。ログ設定は `kabusys.utils.logging_setup.setup_logging` を使用して統一管理されます。
   - LOG_LEVEL 環境変数でログレベルを変更可能（DEBUG/INFO/...）。

6. Kill Switch / フラグ制御
   - KillSwitch はリスク条件を検出すると data/kill.flag を作成します。ExecutionEngine 側はこれを参照して安全に停止します。
   - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 推奨）。

---

## よく使う環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（実行環境）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py (パッケージ初期化)
  - config.py — 環境変数/設定管理（.env 自動読み込み・Settings クラス）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト（python -m kabusys.run_monitoring）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - system_monitor.py — CPU/メモリ/Disk、データ鮮度、プロセス生存監視
    - trade_monitor.py — （注文ログの整合性等）※コードベースに一部実装あり
    - risk_monitor.py — ドローダウン等のリスク監視
    - kill_switch.py — Kill Switch 実装（flag ファイル操作）
    - alert_manager.py — アラート通知管理（実装に応じて LINE 等へ通知）
  - execution/ — ExecutionEngine や OrderManager, Reconciler, RiskManager など（ファイル群）
  - portfolio/
    - portfolio_builder.py — 候補選定 / スコアソート
    - position_sizing.py — 発注株数計算（lot 単位の丸め・スケーリング）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — forward returns, IC, factor summary
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ファイルローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil 利用）
  - data/（実行時に使用するデータ・DB・flag を置く想定ディレクトリ）
  - config/（プロジェクトルート: system_config.yaml 等の YAML 設定ファイル群）

---

## 開発・運用上の注意点

- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 本番稼働時は KABUSYS_ENV=live を設定し、KILL_FLAG_CLEAR_ON_START は 0（自動クリア無効）を推奨します。
- AI モジュールは OpenAI API を利用するため、API キー必須。API コールに伴うコスト・レート制限に注意してください。
- Monitoring は本番 sqlite_path を参照するため、monitoring の DB は実運用で一貫性を持って管理してください。
- DuckDB は分析用途に最適化されています。リサーチ処理は DuckDB 接続を受け取り SQL を実行します。

---

README はこのプロジェクトの主要な使い方と構成の要約です。さらに詳細な設計や API 仕様（ExecutionEngine の内部、BrokerClient の実装、AlertManager の設定など）はコード内の docstring や個別ドキュメント（例えば PortfolioConstruction.md / StrategyModel.md 等）を参照してください。必要であれば README に追記・具体化します。