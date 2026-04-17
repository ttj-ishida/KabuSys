# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
このドキュメントはコードベースの主要コンポーネント、セットアップ手順、使い方、ディレクトリ構成を簡潔にまとめたものです。

## プロジェクト概要
KabuSys は日本株の自動売買・研究・監視機能を備えたシステムです。  
主な目的は以下：

- 発注エンジン（ExecutionEngine）による注文実行（本番 / ペーパートレードに対応）
- 監視コンポーネントによるプロセス状態、注文滞留、リスク監視、Kill Switch
- 研究・ファクター計算、特徴量探索モジュール（DuckDB ベース）
- ニュース NLP やレジーム判定などの AI 補助機能（OpenAI を利用）
- ペーパートレード検証レポート生成ツール

バージョン: 0.1.0（src/kabusys/__init__.py）

## 主な機能一覧
- Execution
  - ExecutionEngine：ブローカークライアントを介した注文管理（paper_trading では MockBroker を使用）
  - OrderRepository / OrderManager / RiskManager / Reconciler
- Monitoring
  - SystemMonitor：CPU・メモリ・ディスク・データ鮮度・PID 生存チェック
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine / KillSwitch / AlertManager（通知連携）
  - 永続化：SQLite ベース（monitoring_db）
- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索、IC 計算、統計サマリ
  - ポートフォリオ構築（候補選定、配分、セクター制限、ポジションサイズ計算）
- AI
  - news_nlp：OpenAI を使ったニュースセンチメント集約 → ai_scores へ書込み
  - regime_detector：ETF ma200 とマクロニュースの LLM スコアから市場レジーム判定
- Tools
  - paper_verification_report：ペーパートレード DB を解析して PASS/FAIL レポートを生成
- 設定ユーティリティ
  - config_setup：.env の対話式作成
  - validate_config：設定・ファイル整合性チェック

## 前提 / 必要環境
- Python 3.10 以上（型注釈・PEP 604 表現などを使用）
- システム依存パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（config 検証を厳密に行う場合、任意）
- SQLite（標準ライブラリに含む）
- ネットワークアクセス（本番で外部 API を使う場合）

例: 必要パッケージのインストール（仮想環境推奨）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt があればそちらを利用してください）

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境作成・依存パッケージをインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意（ただし本番で通知を使う場合は設定が必要）:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV の値:
     - development / paper_trading / live
     - paper_trading: MockBrokerClient を使い、デフォルトで data/paper_trading.db を利用（本番 DB と分離）
4. 設定検証（任意／起動前推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```
5. data ディレクトリや DB の初期化は各プロセスが起動時に必要に応じて自動作成・マイグレーションを行います。事前に data ディレクトリの作成や権限確認をしてください。

## 使い方（主要な実行コマンド）

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパー取引（KABUSYS_ENV=paper_trading）の場合、MockBrokerClient が使われ、デフォルトで data/paper_trading.db に記録されます。
  - 停止: プロセスは data/stop_requested.flag を検知すると終了します（外部から停止したい場合にこのファイルを作成）。
  - エンジンの PID は data/execution.pid に保存されることがあります。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - Monitoring は常に本番用 sqlite_path を使用して監視ログを記録します（KABUSYS_ENV にかかわらず）。
  - 停止: data/stop_requested.flag の検出でループを終了します。

- 設定ウィザード（.env 作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  ```
  オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数で指定可能）

- AI 関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY（または api_key 引数）が必要

## 重要な環境変数と挙動（抜粋）
- KABUSYS_ENV: execution の動作モード（development / paper_trading / live）
  - paper_trading: MockBroker を使い DB を分離（PAPER_TRADING_SQLITE_PATH）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能の API キー
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 認証に必須
- KILL_FLAG_*:
  - KillSwitch は問題検出時に設定された flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine 等に停止を促します
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアする（本番では 0 推奨）

## 停止方法 / Kill Switch
- 手動停止（監視プロセスやエンジン）:
  - 一時停止用: data/stop_requested.flag を作成 → run_execution / run_monitoring はこのファイルを検知して安全終了します。
  - Kill Switch: monitoring が検出した重大リスク（例: ドローダウン閾値超過）により data/kill.flag に理由を書き込み、ExecutionEngine 側でそれを検出して停止する仕組みがあります（KillSwitch と Settings.kill_flag_path）。
- PID 管理: execution 起動時に data/execution.pid を使うことがあります。stale PID の検出・クリーンアップは SystemMonitor が行います。

## DB / マイグレーション
- monitoring_db.init_monitoring_db() は複数テーブルを作成し、既存 DB に対する簡単なマイグレーション（カラム追加）を行います。常に冪等に走ります。
- DuckDB は分析・研究用データを保持。prices_daily / raw_financials / raw_news 等のテーブルを参照します。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要なモジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注関連（OrderRepository 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

（上記は主要ファイルの抜粋です。細かな実装は該当ファイルを参照してください）

## 開発 / テストに関する注意
- .env は絶対にバージョン管理に含めないでください（config_setup のヘッダにも注意書きあり）。
- PyYAML が無い場合、validate_config は YAML の詳細検証をスキップします（警告）。
- OpenAI を用いる機能は API 制限・課金が発生します。キー管理と利用ポリシーに注意してください。
- ペーパートレードモードでは本番 DB と分離するため、誤発注リスクは低くなりますが、設定ミスに注意してください（KABUSYS_ENV の値を厳密に確認）。

## トラブルシューティング（よくある点）
- 「必須環境変数が未設定」のエラーが出る → .env を作成して必要キーを設定、または環境変数を直接エクスポートしてください。
- Monitoring が起動するが Execution が起動しない → data/stop_requested.flag の存在や kill.flag の有無、execution.pid の状態を確認してください。
- AI 関連が動かない → OPENAI_API_KEY の設定と openai パッケージのインストールを確認してください。
- DuckDB / SQLite への接続エラー → ファイルパス（DUCKDB_PATH / SQLITE_PATH）とディレクトリの権限を確認してください。

---

詳細な API ドキュメントやアーキテクチャ（例：PortfolioConstruction.md、StrategyModel.md 等）は別途ドキュメントを参照してください（リポジトリ内に存在する想定）。実運用前には validate_config によるチェックを必ず行い、KABUSYS_ENV=live 設定時は通知設定や Kill Switch の設定を慎重に確認してください。