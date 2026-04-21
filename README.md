# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
リサーチ（ファクター計算・特徴量探索）、ポートフォリオ構築、ポジションサイズ決定、発注実行（本番／ペーパー分離）、監視・アラート、LLM を使ったニュース NLP / レジーム判定などのコンポーネント群を含みます。

バージョン: 0.1.0

---

## 主な機能

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- ポートフォリオ構築
  - シグナル選別（スコア順）
  - 等加重 / スコア加重のウェイト算出
  - セクター集中制限の適用
  - レジーム乗数の適用
- ポジションサイズ計算
  - risk_based / equal / score 方式
  - 単元株（lot）丸め、aggregate cap のスケーリング
- 発注実行（ExecutionEngine）
  - 実口座（kabuステーション API）とペーパートレード（MockBrokerClient）を分離
  - ペーパー時は専用 SQLite（data/paper_trading.db）に記録
  - リスク管理（ポジション上限・ドローダウン等）を統合
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）・データ鮮度の監視
  - 発注ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（条件成立時に data/kill.flag を書く → Execution を停止）
  - 監視ループ用スクリプト（MONITOR_POLL_INTERVAL で間隔指定可能）
- AI 周り
  - ニュースを LLM（OpenAI）でスコアリングし ai_scores に書き込み
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定
  - OpenAI 呼び出しは堅牢なリトライ・バリデーション実装
- ツール
  - Paper Trading の検証レポート生成スクリプト（注文成功率、レイテンシ、稼働率判定など）
- 共通ユーティリティ
  - 統一的なログ設定（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 対話式ウィザード、設定検証 CLI

---

## 動作要件（概略）

- Python 3.9+（型注釈や一部モジュールの仕様に合わせて）
- 必須 Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config YAML 検証を行う場合)
- 標準で SQLite を使用（組み込み）
- ネットワークアクセスが必要（kabuステーション API / OpenAI 等）

（実際の requirements はプロジェクトの requirements.txt を参照してください。存在しない場合は上記パッケージを個別にインストールしてください。）

例:
```bash
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / 展開
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt  # 要件ファイルがある場合
   # ない場合は最低限:
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数（.env）を作成
   - 対話式ウィザードを推奨:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは `.env` を生成/更新します。生成後は必ず `python -m kabusys.validate_config` で検証してください。
   - 自動 .env ロードはデフォルトで有効（プロジェクトルートに .env/.env.local があれば読み込み）。テスト等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY（AI 機能を使用する場合）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - その他（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_LEVEL 等）

---

## 主要コマンド（使い方）

- 設定ウィザード（.env 作成・更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（エラー・警告表示）
  ```bash
  python -m kabusys.validate_config
  # 警告も fail にする場合:
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（発注エンジン）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 起動時はプロセス優先度が "high" に設定されます。
  - 実行中に停止させるには Kill Switch（data/kill.flag）や stop flag を利用します。

- Monitoring（SystemMonitor のポーリング）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書きできます（整数、1 秒以上）。
  - 監視 DB（SQLite）は環境にかかわらず本番用 sqlite_path を使用します（monitoring の履歴は同じ DB）。
  - 実行中にプロジェクトルート下 `data/stop_requested.flag` が作られるとループを終了します。

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコアリング / レジーム判定）
  - コード内の public API を呼ぶかスクリプトを作成して実行します。
  - 必要に応じて環境変数 `OPENAI_API_KEY` を設定してください。
  - 例: ニューススコアを生成する関数 `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼ぶ（DuckDB 接続が必要）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development / paper_trading / live（既定: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

---

## ファイル・フラグの意味

- data/kill.flag: Kill Switch が発動したときに書き込まれるファイル。ExecutionEngine はこれを検出して停止します。
- data/stop_requested.flag: run_* スクリプトの外部停止トリガ（存在を検出すると監視ループやエンジン起動を中止）。
- data/execution.pid: Execution の PID ファイル（ExecutionEngine が生成）。
- data/monitoring.db: 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard 等）。
- data/paper_trading.db: ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時に利用）。

---

## ロギング

- ログは標準出力（stdout）に出力されるほか、`logs/<app_name>.log` に日次ローテーションで保存されます（30 日分保持）。
- `kabusys.utils.logging_setup.setup_logging(app_name="...")` を起動スクリプトから呼び出して統一したログ設定を行います。

---

## ディレクトリ構成（概要）

以下は src/kabusys 以下の主なモジュールと目的（プロジェクトルートは省略）:

- kabusys/
  - __init__.py
  - config.py
    - .env 自動ロード、Settings クラス（環境変数ラッパ）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポートツール
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在、コード省略部分あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（上記は主要モジュールの抜粋です。実際のファイル一覧はリポジトリを参照してください。）

---

## 運用上の注意事項 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0` にして、自動で Kill Switch を消さないようにしてください。
- 本番用の API キーやトークンは .env に直接置かないか、厳重に管理してください（.env を Git にコミットしないこと）。
- Paper Trading と本番 DB は分離されています。ペーパートレードは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。
- AI 機能（OpenAI）はレート制限や課金に注意してください。API キーは環境変数で提供します。
- ログディレクトリに書き込み権限がない場合、ファイルハンドラは無効化されコンソール出力のみとなります（警告が出ます）。
- process_priority の設定はプラットフォーム依存です（権限不足で失敗する場合は警告に留まります）。

---

## 開発者向けメモ

- DuckDB 接続を渡して純粋関数（研究系）を実行する設計になっています。テスト容易性を考慮して datetime.today()/date.today() を直接参照しない実装が多く採用されています（外部から日付を注入可能）。
- OpenAI 呼び出しはリトライやレスポンスバリデーションを実装しており、失敗時はフォールバックして処理継続する方針です。
- 監視・発注周りの永続層は監視 DB（SQLite）を用いたシンプルな CRUD レイヤーになっています。

---

README ではプロジェクトの全貌を簡潔にまとめました。追加で以下のような情報が必要であれば教えてください。

- 依存パッケージの正確な requirements.txt を作成してほしい
- デプロイ / systemd / cron での運用手順テンプレート
- 各テーブル・カラムの詳細ドキュメント（ER 図風）