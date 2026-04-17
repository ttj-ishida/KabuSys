# KabuSys

日本株自動売買システムの参照実装（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ツールを含むモジュール群を提供します。軽量なローカル実行およびペーパートレードと本番（live）運用を想定した設計になっています。

## プロジェクト概要

- 主な目的：日本株アルゴリズムの研究・検証と、（オプションで）kabuステーション等を使った自動発注を行うための基盤コード。
- モード：
  - development：ローカル開発（発注を伴わない想定）
  - paper_trading：ペーパートレード（モックブローカーを使用し、本番 DB と分離）
  - live：本番運用（実際に発注を行う）
- 永続化：
  - SQLite（監視・注文ログ等、デフォルト：data/monitoring.db / data/paper_trading.db）
  - DuckDB（分析・ファクター計算用データベース、デフォルト：data/kabusys.duckdb）

## 主な機能一覧

- 実行スクリプト
  - run_execution.py：ExecutionEngine を起動（実際の発注処理）
  - run_monitoring.py：SystemMonitor のポーリングループを起動（CPU / メモリ / データ鮮度 等の監視）
- 設定管理 / CLI
  - config_setup.py：.env 初期作成・対話ウィザード
  - validate_config.py：環境変数と config/*.yaml の事前検証ツール
- 監視（monitoring）
  - SystemMonitor：プロセス生存・データ鮮度・リソース監視
  - TradeMonitor：滞留注文 / 約定異常価格の検知
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch / AlertManager：条件による停止フラグの書込み & LINE 通知（オプション）
  - MonitoringEngine：各 Monitor を束ねるエンジン
- 発注周辺（execution）
  - OrderRepository / OrderManager / ExecutionEngine / RiskManager / Reconciler（発注・リスク制御）
  - ブローカーファクトリ（paper_trading 時は Mock ブローカーを使用）
- ポートフォリオ構築（portfolio）
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数 等
- 研究・ファクター計算（research）
  - Momentum / Volatility / Value ファクター、将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI 経由の NLP）
  - news_nlp：ニュースを LLM でセンチメント評価 → ai_scores に格納
  - regime_detector：ETF とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - tools.paper_verification_report：Paper Trading の検証レポートを生成

## 前提（環境・依存）

- Python 3.10 以上（型記法に `X | None` を使用しているため）
- 推奨ライブラリ（プロジェクトに requirements.txt がない場合は手動インストール）:
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（config の YAML 検証を行う場合）
- 標準ライブラリ：sqlite3, threading, logging, datetime など

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests pyyaml
```

（実環境ではバージョン固定した requirements.txt を用意することを推奨します）

## セットアップ手順

1. リポジトリをクローン
   - git clone … && cd <repo>

2. 仮想環境作成 & パッケージインストール（上記参照）

3. .env の作成（対話ウィザード推奨）
   - 対話式で .env を作成/更新:
     ```bash
     python -m kabusys.config_setup
     ```
   - またはテンプレートを参考に環境変数を設定してください。最低必要な環境変数：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
     - DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（任意、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）

4. 設定検証（起動前に実行推奨）
   - 簡易検証:
     ```bash
     python -m kabusys.validate_config
     ```
   - 警告を厳格に扱う場合は `--strict` を付けて、警告でも exit(1) にすることができます。

5. DB 初期化
   - run_execution/run_monitoring の起動時に監視テーブルは自動で作成されます（init_monitoring_db を実行）。

## 使い方（主要コマンド）

- ExecutionEngine を起動（発注エンジン）
  - 本番（または設定に従う）:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作概要:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と完全に分離）。
    - 停止は `data/stop_requested.flag` を作成するとスレッドが検知して停止します。
    - 起動時に PID ファイルを data/execution.pid 等に書きます（Settings.pid_file_path）。

- Monitoring を起動（ポーリング監視）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト: 60）
  - 監視ループは `data/stop_requested.flag` の存在を検知して終了します
  - 監視は常に（Settings.env に関わらず）本番 sqlite_path を使用してログを残します

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH（なければ data/paper_trading.db）

- AI 機能（プログラム的に利用）
  - 例：ニューススコアリング（Python 内から）
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    # target_date は datetime.date オブジェクト
    n_written = score_news(conn, target_date, api_key="sk-...")
    ```
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数でも可）

- 設定の自動クリア/kill flag
  - KillSwitch は条件に応じて `data/kill.flag` を書き込み（ExecutionEngine 停止トリガー）。
  - Settings には kill_flag_clear_on_start（起動時に自動クリアするか）設定があり、本番では 0 推奨。

## 停止・制御方法

- 実行中の監視/エンジンを安全に停止する方法：
  - 監視ループ / 実行スレッドは `data/stop_requested.flag` の存在を定期チェックします。停止したいときはこのファイルを作成してください（空ファイルで可）。
  - KillSwitch による停止（リスク閾値を超えた場合）は `data/kill.flag` を書き込みます。ExecutionEngine はこのファイルを見て挙動を切り替えます。

## 設定項目の主要説明（Settings）

- JQUANTS_REFRESH_TOKEN：J-Quants API 用トークン（必須）
- KABU_API_PASSWORD：kabuステーション API パスワード（必須）
- OPENAI_API_KEY：OpenAI を使う機能で必要
- KABUSYS_ENV：実行環境（development / paper_trading / live）
- DUCKDB_PATH：DuckDB ファイルパス（分析データ）
- SQLITE_PATH：監視 DB（monitoring.db）
- PAPER_TRADING_SQLITE_PATH：paper_trading 専用 SQLite（本番と分離）
- PID_FILE_PATH：ExecutionEngine の PID ファイルパス
- KILL_FLAG_PATH：kill.flag のパス
- MONITOR_POLL_INTERVAL：run_monitoring のポーリング間隔（秒、環境変数で指定）
- PAPER_FILL_MODE：paper_trading の約定挙動（instant / partial / never / reject）

## ディレクトリ構成

（src/kabusys をルートにした主要ファイル・階層）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - execution/                — 発注エンジン関連（OrderRepository 等）
    - (OrderManager, ExecutionEngine, BrokerFactory, Reconciler, RiskManager など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF）
    - __init__.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ヘルパ
    - __init__.py

※ 実際の execution/ 以下のファイル群は本 README の要約では全て列挙していません。詳細はソースコードを参照してください。

## 運用上の注意 / ベストプラクティス

- 本番運用時（KABUSYS_ENV=live）は環境変数と設定を慎重に確認してください。validate_config.py の warns は本番で致命的になり得ます。
- paper_trading モードでは発注先が完全に分離された専用 DB を使用します。実 DB に上書きされるリスクは基本的にありませんが、環境変数は必ず確認してください。
- OpenAI を使う機能は API 料金が発生します。API 呼び出しのリトライや失敗時のフォールバックは実装されていますが、コスト管理を行ってください。
- PID / flag / DB ファイルのパスは Settings で制御できます。システムの監視・再起動スクリプトと組み合わせる際はこれらを整合させてください。
- process priority / cpu affinity の設定は psutil を利用しますが、権限不足で失敗することがあるためエラーハンドリングしてスキップする実装になっています。

---

さらに詳しい内部設計（アルゴリズムの方針や数式、DB スキーマなど）は各ソースファイル内の docstring / コメントを参照してください。使い方で不明な点や追加ドキュメントが必要であれば、どの機能について詳しく知りたいか教えてください。