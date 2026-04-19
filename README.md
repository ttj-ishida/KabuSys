# KabuSys

日本株自動売買システム KabuSys のリポジトリ用 README。  
このドキュメントは、リポジトリ内のスクリプト・モジュール構成と基本的なセットアップ／起動手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買フレームワークです。  
主な目的は以下の通りです。

- 戦略（ファクター計算・特徴量探索）やポートフォリオ構築ロジックに基づく発注処理
- 発注実行の分離（本番 / ペーパートレード切替）
- システム監視・アラート、Kill Switch による安全停止
- AI を使ったニュースセンチメント評価や市場レジーム判定（OpenAI）
- Paper Trading の検証用レポート生成

※ 本 README はコードベース（src/kabusys 以下）を参照して作成しています。

---

## 主な機能一覧

- Execution（発注エンジン）
  - 本番（live）/ ペーパートレード（paper_trading）モードの切替
  - Broker クライアントの抽象化（MockBroker を含む）
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）
- Monitoring（監視）
  - CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック
  - Trade / Risk モニタによるリスクイベント記録と Kill Switch 発動
  - ログの永続化（SQLite）と DuckDB 連携
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額／スコア重み、ポジションサイズ計算、セクター抑制、レジーム乗数
- Research（研究用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、特徴量サマリ
- AI（OpenAI 統合）
  - ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - マクロニュース + MA200 を合成して市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## 必要条件 / 推奨環境

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のためオプション）
- 環境に応じた DB ファイル（DuckDB / SQLite）への書き込み権限

依存はプロジェクトに requirements.txt があればそちらを使うか、以下を例としてインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## 設定（.env）

アプリ設定は環境変数またはプロジェクトルートの `.env` に保存します。必須の主要環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時に必要)
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO、DEBUG）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
- その他: LOG_DIR, PID_FILE_PATH など

.env を対話式に生成・更新するには次を実行してください:
python -m kabusys.config_setup

生成後、設定の妥当性をチェック:
python -m kabusys.validate_config
python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

---

## セットアップ手順（概略）

1. リポジトリをクローンしてプロジェクトルートに移動
2. 仮想環境を作成して有効化（推奨）
3. 依存をインストール
   - pip install -r requirements.txt もしくは個別インストール
4. .env を作成（config_setup ウィザードを推奨）
   - python -m kabusys.config_setup
5. 設定検証
   - python -m kabusys.validate_config
6. 必要なディレクトリ（data, logs）を作成（通常は自動作成されますが権限に注意）

---

## 使い方（起動 / 実行例）

主要スクリプトはモジュールとして実行できます。

- 実行エンジン（ExecutionEngine）を起動
  - 本番（live）モード:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（MockBroker, 専用 DB を使用）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID が書かれます。停止は stop flag / kill flag などで制御。

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（本番監視 DB）を常に使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成（存在検出）で行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を参照します（--db 優先）。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
  - ニューススコアリング: kabusys.ai.score_news を呼び出し
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼び出し

- ログ
  - デフォルトで stdout と logs/<app_name>.log（日次ローテート）に出力
  - ログディレクトリは LOG_DIR 環境変数またはデフォルト `logs/`
  - ログレベルは LOG_LEVEL または setup_logging の引数で制御

---

## 停止 / Kill Switch

- Kill Switch は監視コンポーネントがリスク条件を満たした際に `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
- 手動で停止させたい場合は `data/stop_requested.flag` を作成してください（run_execution / run_monitoring が検知して停止します）。
- kill.flag を消すには（管理者が）ファイルを削除してください。起動時に自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番では推奨されません。

---

## ディレクトリ構成（主要ファイル）

リポジトリのソースは `src/kabusys` 配下にまとまっています。主要ファイルと役割は以下。

- src/kabusys/
  - __init__.py — パッケージ定義, __version__
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- src/kabusys/execution/ — 実行エンジン・注文管理等（発注ロジック）
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 発注ログ監視（滞留注文、約定異常等）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の生成 / 管理
  - monitoring_engine.py — 各モニタを束ねるランナー
  - alert_manager.py — （アラート送信用の抽象・実装）
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- src/kabusys/research/
  - factor_research.py, feature_exploration.py — ファクター計算 / 研究用ユーティリティ
- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 統合）
  - regime_detector.py — 市場レジーム判定（MA + マクロLLM）
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
- src/kabusys/utils/
  - logging_setup.py — ログ設定ヘルパ
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発者向けメモ / 実装上の注意点

- Settings は .env を自動ロードします（プロジェクトルートの検出は .git / pyproject.toml ベース）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は Monitoring の DB 接続に常に本番の sqlite_path を使用します（環境に依らず）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、MockBroker を使うことで本番 DB とは完全に分離します。
- OpenAI API 呼び出しは一部リトライ・バックオフを実装しており、API レスポンスのバリデーションも行われます。API キーは環境変数 `OPENAI_API_KEY` で設定してください。
- DuckDB に関して executemany の空リストバインドの制約がある（コード内で回避）ため、DuckDB バージョンに依存する注意があります。

---

## よく使うコマンド一覧

- .env を作成／更新（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution を起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring を起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に

この README はコードベースの主要ポイントをまとめたものです。詳細な仕様やアルゴリズム（PortfolioConstruction.md や StrategyModel.md 等参照）は別ドキュメントで管理されている想定です。  
不明点や環境依存で動作しない箇所があれば、該当モジュールのログや validate_config の出力を確認してください。