# KabuSys — 日本株自動売買システム（README）

このリポジトリは、日本株自動売買システム「KabuSys」のコアユーティリティ群を含みます。戦略・発注・監視・研究・AI ニュース解析などのコンポーネントがモジュール化されています。本 README はローカル環境でのセットアップ、主要機能、実行方法、ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能
- 前提 / 依存関係
- セットアップ手順
- 環境変数（.env）と主要設定
- 使い方（起動・ツール）
- モニタリング・停止方法（Kill Switch / Stop フラグ）
- ディレクトリ構成（主要ファイル説明）
- 補足 / 注意点

---

## プロジェクト概要
KabuSys は、日本株自動売買のためのライブラリ群および実行ユーティリティです。主な役割は次の通りです。
- マーケットデータを用いたファクター計算・研究（DuckDB ベース）
- ポートフォリオ構築とポジションサイジング（純粋関数群）
- 発注エンジンの起動（実口座 / ペーパートレード分離）
- システム稼働監視（プロセス生存 / データ鮮度 / 注文滞留 / リスク監視）
- ニュースの NLP によるセンチメント集計（OpenAI）
- 監視ログの永続化（SQLite）

---

## 主な機能（一部）
- config_setup: 対話式 .env ウィザード（初期設定支援）
- validate_config: 環境変数および config/*.yaml の静的検証
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading を分離）
- run_monitoring: SystemMonitor ポーリングループの起動
- monitoring_engine: 複数のモニタを束ねるエンジン（アラート送信・Kill Switch 連携）
- monitoring_db: SQLite を用いた監視ログテーブル／CRUD
- tools/paper_verification_report: ペーパートレード結果の検証レポート生成
- research/*: ファクター計算（momentum/value/volatility 等）・IC / 統計ユーティリティ
- ai/news_nlp, ai/regime_detector: OpenAI を使ったニューススコアリング / レジーム判定
- portfolio/*: 候補選定、重み計算、リスク制限、ポジション数量算出
- utils/process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## 前提 / 依存関係
※実行には Python 3.10+ を推奨（型ヒントに `X | Y` 構文を使用しています）。

主な Python パッケージ（最低限）:
- duckdb
- psutil
- openai
- requests
- PyYAML（config YAML の検証を行う場合に必要）
- （標準ライブラリ: sqlite3 等は標準で利用）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests pyyaml
```
（requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順（簡易）
1. リポジトリをクローン / コピー
2. 仮想環境を作成して依存パッケージをインストール
3. .env を作成
   - 対話式ウィザードを推奨: python -m kabusys.config_setup
4. 設定検証:
   - python -m kabusys.validate_config
   - 問題があれば指摘に従って .env / config/*.yaml を修正
5. データディレクトリを作成（必要に応じて）:
   - data/（SQLite / PID / flag ファイルがここに置かれることを想定）
   - 例: mkdir -p data

---

## 環境変数（.env）と主要設定
主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 環境時に使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant|partial|never|reject）

自動読み込み:
- プロジェクトルートに .env / .env.local がある場合、起動時に自動ロードされます（OS 環境変数を上書きしない挙動）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（よく使うコマンド）

基本: 仮想環境を有効化した上で実行してください。

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い
  ```

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 実行前に data/execution.pid が作成され、プロセス生存チェックに利用されます（PID ファイルパスは Settings で設定可能）。

- 監視ループ起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite（Settings.sqlite_path）を使います。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（ライブラリ関数として利用）
  - ニューススコアリング:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 11), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,11), api_key="YOUR_OPENAI_KEY")
    ```

---

## モニタリングと停止（Kill Switch / Stop フラグ）
- Stop フラグ（手動停止）
  - run_execution / run_monitoring はプロジェクトの data/stop_requested.flag（親ディレクトリに `data`）の存在を監視してループを停止します。
  - 起動中のプロセスを優雅に止めるためにはこのファイルを作成します（例: touch data/stop_requested.flag）。

- Kill Switch（自動停止トリガ）
  - リスク監視（drawdown 超過、ポジション数上限等）により `data/kill.flag` が書き込まれると、ExecutionEngine の起動時 / 実行中に停止シグナルとして評価されます。
  - Settings.kill_flag_clear_on_start=1 に設定すると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。

- PID ファイル
  - ExecutionEngine は PID ファイル（デフォルト data/execution.pid）を作成して自身の生存を示します。SystemMonitor はこの PID を使ってプロセスが生きているかチェックします。

---

## ディレクトリ構成（主要ファイルの説明）
以下は src/kabusys 内の主なモジュールと役割です（抜粋）。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス、自動 .env ロードロジック
  - config_setup.py — 対話式 .env 生成ウィザード（CLI）
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- kabusys/monitoring/
  - monitoring_db.py — SQLite テーブル定義・ラッパー（監視ログ）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留 / 約定価格異常検出
  - risk_monitor.py — ドローダウン / ポジション上限のチェック
  - kill_switch.py — フラグ書き込みで Execution 停止シグナルを生成
  - monitoring_engine.py — 複数 Monitor を束ねてポーリング・アラート発行
  - alert_manager.py — LINE への通知（クールダウン管理）

- kabusys/execution/  (発注周り)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など（コードベース参照）

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 株数計算、ロット丸め、集約キャップ
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー

- kabusys/ai/
  - news_nlp.py — raw_news を集約して OpenAI で銘柄ごとセンチメントを算出し ai_scores に保存
  - regime_detector.py — ETF 等の ma200 と LLM マクロセンチメントを合成して market_regime に書き込み

- kabusys/tools/
  - paper_verification_report.py — ペーパートレードの品質指標（稼働率・成功率・レイテンシ等）を集計してレポートを出力

- kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 補足 / 注意点
- paper_trading モードは発注処理をペーパートレード用 DB に完全分離します（実口座とデータが混ざらない設計）。
- run_monitoring は監視用 DB（sqlite_path）を常に使用します（KABUSYS_ENV に依存しません）。
- AI 機能（news_nlp, regime_detector）は OpenAI API キーが必要です。API 呼び出しは失敗時にフォールバックする実装が多く、致命的な停止は行わない設計です。
- config/*.yaml の存在とパースは validate_config.py でチェックします（PyYAML が必要）。
- DuckDB を使った分析処理は DuckDB 接続を受け取り SQL で処理する設計です。データベーススキーマ（prices_daily, raw_financials 等）が前提になります。
- ローカル開発時は KABUSYS_ENV=development を用い、KILL_FLAG_CLEAR_ON_START を 1 にすることで kill.flag 自動クリアを有効にできます。ただし本番 (live) では 0 を強く推奨します。

---

必要であれば、README をプロジェクトの実際のリポジトリ構成・CI・デプロイ手順に合わせてカスタマイズできます。追加で「実行ログのサンプル」や「トラブルシューティング（よくあるエラー）」の節を追加することも可能です。どの情報を優先して追加しますか？