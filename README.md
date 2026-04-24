# KabuSys

日本株自動売買システム（KabuSys）のコードベースリポジトリ用 README

この README はローカル開発／デプロイを開始するための概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステムです。市場情報の集計・ファクター計算・ポートフォリオ構築・発注エンジン・監視・アラート・ペーパートレード検証・LLM を用いたニュース評価など、取引システムに必要なコンポーネント群を含みます。

主な設計方針：
- 本番 DB とペーパートレード DB を分離できる設計
- DuckDB（分析用） + SQLite（監視・履歴）を併用
- モジュールはユニット的に設計（研究モジュールは DB に対する純粋関数群）
- LLM 呼び出しはフェイルセーフに実装（リトライ・フォールバック）
- 起動スクリプトから統一的にログ設定・プロセス優先度設定を行う

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）
  - `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の事前チェック）
  - `kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）
  - `kabusys.run_execution`
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading DB に記録
- 監視プロセス（System / Trade / Risk monitoring）
  - `kabusys.run_monitoring`
  - Kill Switch（条件を満たすと `data/kill.flag` を書き込み ExecutionEngine を停止）
- 監視 DB 層（SQLite）と永続化 API
  - `kabusys.monitoring.monitoring_db`
- ポートフォリオ構築・リスク調整・ポジションサイズ計算（純粋関数）
  - `kabusys.portfolio`（portfolio_builder, risk_adjustment, position_sizing）
- 研究／ファクター計算モジュール（DuckDB 接続で SQL ベース）
  - `kabusys.research`（momentum, volatility, value 等）
- AI（LLM）統合モジュール
  - ニュース NLP（銘柄別センチメント算出）: `kabusys.ai.news_nlp`
  - 市場レジーム判定: `kabusys.ai.regime_detector`
  - OpenAI を利用（gpt-4o-mini 想定）、呼び出しは堅牢に実装
- ペーパートレード検証レポート生成ツール
  - `kabusys.tools.paper_verification_report`
- ログ設定・プロセス優先度ユーティリティ
  - `kabusys.utils.logging_setup`
  - `kabusys.utils.process_priority`

---

## 前提（依存関係）

最低限の実行環境例：
- Python 3.10+
- pip
- 必須 Python パッケージ（主要なもの）:
  - duckdb
  - psutil
  - openai
- 任意（機能により必要）:
  - PyYAML（config/*.yaml の検証に利用）
- SQLite は標準ライブラリで利用可能

（requirements.txt はリポジトリに含まれていないため、実行環境に合わせて必要なパッケージをインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開
   - ソースルートに `src/` 以下が存在することを想定しています。

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージのインストール
   - pip install duckdb psutil openai PyYAML

4. ディレクトリ作成
   - デフォルトで使用するディレクトリ（data, logs）を作成しておくとよい:
     - mkdir -p data logs

5. 環境変数（.env）作成
   - 対話式ウィザードで生成:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` を作成（例: `.env.example` を参考に）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要環境変数（代表例）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB; 例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; 例: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY（AI機能を使う場合）
     - MONITOR_POLL_INTERVAL（監視プロセスのポーリング間隔秒数; デフォルト 60）

6. 設定の検証
   - python -m kabusys.validate_config
   - 警告を厳密に FAIL とする場合:
     - python -m kabusys.validate_config --strict

7. DB 初期化
   - 監視用 SQLite は起動スクリプト内で必要テーブルを作成（init_monitoring_db）するため、特別な初期化は不要です。
   - DuckDB のスキーマは運用側スクリプトで作成するか、事前にデータ投入してください。

---

## 使い方（起動・運用）

以下は主要な実行コマンド例です。実行はプロジェクトルートで行ってください（.env 自動ロードが有効な場合）。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中に同フラグを作成するとエンジンは停止します（停止方法は下記参照）。

- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト: 60秒）。
  - 監視プロセスは Settings に指定された sqlite_path（監視 DB）を利用します。※監視は環境にかかわらず本番 sqlite_path を使用します。
  - 監視ループの停止は `data/stop_requested.flag` を作成することで行えます（または Ctrl+C）。

- 停止・Kill Switch
  - リスク条件などで自動的に停止させるためのファイル: `data/kill.flag`
    - KillSwitch が該当条件を検出すると `data/kill.flag` に理由を書き込む（存在チェックで冪等）。
    - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていない限り `kill.flag` の存在を検知すると起動せずに終了する運用が推奨されます。
  - 管理的に停止を要求する場合は `data/stop_requested.flag` を作成してください（起動スクリプトはこのファイルを見て終了します）。
  - `kill.flag` の削除は `KillSwitch.clear()` を呼ぶか手動でファイルを削除してください。
    - 環境変数 KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能の利用（Python API）
  - ニューススコアリング（例）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # conn は DuckDB 接続
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

---

## 環境変数の主な一覧（代表）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB; デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB; デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (デフォルト: logs/)
- OPENAI_API_KEY (AI 機能)
- PAPER_FILL_MODE (paper_trading 時の約定挙動: instant|partial|never|reject)
- MONITOR_POLL_INTERVAL (監視プロセスのポーリング秒数、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1)

設定の自動ロード:
- プロジェクトルートにある `.env` および `.env.local` が自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイルと概要）

リポジトリの `src/kabusys` 配下（抜粋）:

- __init__.py
  - パッケージ初期化・バージョン

- run_execution.py
  - ExecutionEngine 起動スクリプト（pid ファイル管理、stop flag チェック、paper mode 対応）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL により間隔変更可）

- config.py
  - 環境変数読み込み・Settings クラス（アプリケーション設定）

- config_setup.py
  - .env 生成・更新の対話式ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- utils/
  - logging_setup.py : ログ設定ユーティリティ（stdout + 日次ローテーション）
  - process_priority.py : プロセス優先度・CPU affinity 設定ユーティリティ
  - など

- monitoring/
  - monitoring_db.py : SQLite テーブル作成・読み書き API
  - system_monitor.py : システム状態・データ鮮度監視
  - trade_monitor.py : 発注状況監視（滞留注文・約定異常等）
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : kill.flag 書き込み管理
  - monitoring_engine.py : モニタ群を束ねる実行エンジン
  - alert_manager.py : （存在する場合）外部通知管理

- execution/
  - execution_engine.py : 発注セッションを実行するエンジン
  - broker_factory.py : ブローカークライアント生成（本番 / Mock 切替）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py : 発注・リスク管理関連

- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 発注株数計算（単元丸め・リスク制限）
  - risk_adjustment.py : セクター制限・レジーム乗数

- research/
  - factor_research.py : momentum / volatility / value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py : 将来リターン・IC 計算・統計サマリー

- ai/
  - news_nlp.py : ニュースセンチメント算出（OpenAI）
  - regime_detector.py : マクロ + ma200 によるレジーム判定（OpenAI オプション）

- tools/
  - paper_verification_report.py : ペーパートレード検証レポートを生成

---

## 運用上の注意・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します（誤って Kill Switch をクリアすることを防ぐ）。
- `.env` は絶対に Git にコミットしないでください。
- OpenAI API キーやブローカーパスワード等のシークレットは OS 環境変数か .env を利用して安全に管理してください。
- ログはデフォルト `logs/` に日別でローテーションされます。ログディレクトリの権限・ディスク容量に注意してください。
- 監視プロセスは `SQLITE_PATH` に対して直接ログを書き込むため、バックアップやローテーションを考慮してください。
- AI 呼び出しは外部APIへ依存するため、API障害時のフォールバック（0.0等）設定がなされていますが、コスト・レート制限に注意してください。

---

この README はコードベースの要点をまとめたものです。実装の詳細や追加の運用手順は各モジュールのドキュメント／ソース内の docstring を参照してください。必要であれば、README に含める追加情報（デプロイ手順、systemd ユニット例、Dockerfile 例 等）を教えてください。