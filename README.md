# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

バージョン: 0.1.0

---

このリポジトリは、戦略の研究（ファクター計算・特徴量解析）〜 ポートフォリオ構築 〜 発注エンジン（ExecutionEngine）〜 監視（Monitoring）までを含む日本株自動売買システムのコア実装群を提供します。DuckDB / SQLite をデータ層に、kabuステーション等のブローカークライアント経由で発注を行う設計です。Paper Trading（モックブローカー）モードや OpenAI を使ったニュース NLP / レジーム判定などの補助機能も含みます。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 環境変数 / 設定
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意

---

## プロジェクト概要

- コア機能は Python パッケージ `kabusys` 内に実装されています（src/kabusys）。
- データベース:
  - 分析用: DuckDB（デフォルト: `data/kabusys.duckdb`）
  - 監視・発注ログ: SQLite（デフォルト: `data/monitoring.db`）
  - Paper Trading 用 SQLite（分離）: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）
- 起動スクリプト:
  - 実際の発注エンジン起動: `run_execution.py`
  - 監視ループ起動: `run_monitoring.py`
- 設定管理:
  - `.env` を読み込む自動ローダー（プロジェクトルートを自動検出）
  - 対話式ウィザード: `kabusys.config_setup`
  - 起動前検証: `kabusys.validate_config`
- 研究用モジュール（DuckDB 経由）やポートフォリオ構築ロジック、AI（OpenAI）連携モジュールを含む。

---

## 機能一覧

- 環境設定ウィザード（.env の生成 / 更新）
- 起動前設定検証（必須環境変数 / ファイルパス / YAML 構文チェック）
- ExecutionEngine（発注エンジン）起動 / Paper Trading モード対応（MockBrokerClient）
- Monitoring（システム状態監視・トレード監視・リスク監視）と Kill Switch（フラグファイルによる停止）
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出・セクター制限）
- 研究用モジュール（ファクター計算、IC計算、将来リターン）
- AI モジュール:
  - ニュース NLP による銘柄ごとのセンチメント（OpenAI）
  - 市場レジーム判定（MA + マクロニュースの LLM センチメント合成）
- ユーティリティ:
  - Paper Trading 検証レポート生成スクリプト（orders/monitoring の集計）
  - プロセス優先度 / CPU affinity 設定補助

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 必要なパッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - pyyaml (config の YAML 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を推奨）
3. プロジェクトルートに移動（pyproject.toml / .git があるディレクトリ）
4. 対話式で `.env` を作成（推奨）
   - python -m kabusys.config_setup
   - 必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか
5. 起動前に設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）
6. デフォルトでは以下のディレクトリ / ファイルが使用されます（自動作成されることが多い）
   - data/（SQLite / PID / フラグファイル等）
   - logs/（ログファイル）
   - DuckDB ファイル（data/kabusys.duckdb）

---

## 使い方（主要スクリプト・CLI）

- 環境設定ウィザード（.env の生成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づいて SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading のときは Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用
    - 起動中は `data/execution.pid` に PID が書かれる（設定で変更可能）
    - 停止方法:
      - 監視側や運用者が `data/stop_requested.flag`（プロジェクトルート/data/stop_requested.flag）を作成すると、エンジンはそのフラグを検知して安全に停止します
      - Kill Switch（監視が条件を満たした場合）は `data/kill.flag` を作成し Engine 側の挙動に影響します（設定により挙動変化）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使って監視テーブルにログを残す（環境に関わらず）

- Paper Trading 検証レポート（集計）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI モジュール（プログラムから呼び出す）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY 環境変数または api_key 引数が必要
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要
  - API 呼び出しはリトライやフェイルセーフ実装あり（エラー時は安全側にフォールバック）

---

## 主要な環境変数（抜粋）

- 必須（起動前検証でチェックされる）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行 / ログ / DB
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）

- Execution / Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード。デフォルト: instant）

- Monitoring / Kill Switch
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）

- AI
  - OPENAI_API_KEY（OpenAI を使う機能で必要）

- その他
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動で .env を読み込む処理をスキップ

注意: .env 自動読み込みはプロジェクトルート（.git / pyproject.toml を基準）を検出して実施します。テスト等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 配下の主要モジュール・ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス（環境変数読み出し・自動 .env ロード）
  - config_setup.py — 対話式 .env ウィザード（CLI）
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/utils/
  - logging_setup.py — ロギング設定ユーティリティ（stdout + 日次ファイルローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite を使った監視ログの永続化層（テーブル初期化 / リードライト）
  - system_monitor.py — システム状態監視（CPU/メモリ/ディスク / データ鮮度 / プロセス死活）
  - trade_monitor.py — （トレード監視。※実装参照）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — フラグファイルによる停止判定 / 書き込み
  - monitoring_engine.py — 各モニタを統合するエンジン / 通知

- src/kabusys/execution/
  - execution_engine.py — 発注ロジック / Session 管理（Engine）
  - broker_factory.py — ブローカークライアント生成（Mock / 実ブローカー切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注周りのコンポーネント

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数計算・集約上限スケール処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

- src/kabusys/ai/
  - news_nlp.py — OpenAI を使ったニュースセンチメント集約・ai_scores 更新
  - regime_detector.py — マクロ + MA による日次レジーム判定（LLM 併用）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の稼働・約定評価レポート生成スクリプト

備考:
- monitoring_db.init_monitoring_db() は必要なテーブルを冪等的に作成します。初回起動時に自動的に呼ばれます。
- ログは `logs/<app_name>.log` に日次ローテーション（既定: 30日分保持）で出力されます。ログディレクトリが作成できない場合はコンソール出力のみになります。

---

## 運用上の注意 / トラブルシューティング

- プロセス優先度設定:
  - 高優先度設定は OS により権限が必要な場合があります（Linux で negative nice 値、Windows で権限）。失敗すると警告ログが出てスキップされます。
- Kill Switch / Stop Flag:
  - 運用でエンジンを安全に停止させたい場合はプロジェクトの data/ ディレクトリに `stop_requested.flag` を作成してください（run_execution / run_monitoring はこれを検知して停止します）。
  - 監視側がリスク条件を満たすと `data/kill.flag` を書き込みます。`KILL_FLAG_CLEAR_ON_START` は起動時に自動クリアするかの挙動を制御しますが、本番では `0` を推奨します。
- データベースの分離:
  - Paper Trading モード (`KABUSYS_ENV=paper_trading`) は paper_trading 用 DB を使い、本番 DB と完全分離します。運用ミスで実口座に誤発注しないための安全策です。
- OpenAI 連携:
  - OPENAI_API_KEY が必須です。API 呼び出しはレート制限やネットワークエラーを考慮したリトライ実装がありますが、API キーやコスト管理は運用者の責任です。
- 設定検証:
  - `python -m kabusys.validate_config` を起動前に実行し、必須環境変数やファイルパスなどを確認してください。PyYAML がインストールされていない場合は YAML の検証をスキップしますが、config/*.yaml の存在は警告されます。
- ログディレクトリの権限:
  - `logs/` の作成に失敗するとファイルハンドラを使わずコンソール出力のみになります（警告が出ます）。

---

必要に応じて README を拡張して、CI / デプロイ手順、テスト、より詳細な API ドキュメント（各モジュールの関数仕様例）を追加してください。追加で自動化スクリプト（systemd ユニット、Dockerfile、docker-compose 等）を用意することで運用が楽になります。