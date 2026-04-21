# KabuSys

日本株自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、マーケットデータ集計・ファクター計算・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせた自動売買プラットフォームの一部です。各モジュールは可能な限り副作用を避ける設計（純関数や明示的な DB 接続受け渡し）になっており、ローカル開発・ペーパートレード・本番（live）での実行を想定しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動コマンド）
- 開発用ユーティリティ
- ディレクトリ構成（主要ファイル説明）
- 注意事項 / 運用メモ

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な役割は次の通りです。

- 市場データを用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ候補選定・配分計算・ポジションサイズ計算（等分配・スコア加重・リスクベース）
- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper_trading では MockBroker）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor）と KillSwitch による安全停止機構
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定） — OpenAI API を利用
- ロギング設定、プロセス優先度設定など、運用に便利なユーティリティ

設計指針として、ルックアヘッドバイアスを避けるために日付参照を直接呼び出さない実装や、DB 書き込みでの冪等性（重複実行に耐える）に配慮しています。

---

## 主な機能一覧

- kabusys.research
  - calc_momentum, calc_volatility, calc_value: DuckDB 上でファクター算出
  - calc_forward_returns, calc_ic, factor_summary: 研究用の指標・統計
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（等分配・スコア・リスクベース）
  - apply_sector_cap, calc_regime_multiplier（リスク制御）
- kabusys.ai
  - news_nlp.score_news: raw_news を LLM でスコア化して ai_scores に書き込み
  - regime_detector.score_regime: MA やマクロニュースを合成して市場レジームを判定
- kabusys.execution (発注周りの主要コンポーネント群。起動スクリプトで利用)
- kabusys.monitoring
  - monitoring_db: 監視ログ用 SQLite テーブル作成／API
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - run_monitoring.py: 監視ポーリングループ起動スクリプト
- 起動・設定用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト（paper_trading は DB 分離）
  - config_setup.py: .env 対話型ウィザード
  - validate_config.py: 設定の事前検証 CLI
- ユーティリティ
  - logging_setup: 統一ロギング（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な依存パッケージ（pip インストールが必要）
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に必要）
- （標準ライブラリ）sqlite3, logging, argparse, datetime など

インストール例（仮）:
pip install duckdb psutil openai pyyaml

※ 実運用では requirements.txt / poetry 等でバージョン固定してください。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt もしくは個別インストール（duckdb, psutil, openai, pyyaml）
4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env.example を参考に .env を手動作成
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります
6. データディレクトリの準備
   - デフォルトでは data/ 以下に DB や PID/フラグを置きます。必要に応じて環境変数で上書きしてください。
   - 例: mkdir -p data logs

---

## 環境変数（主なもの）

必須
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

重要（デフォルトあり）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時必須）

監視・運用関連
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: 実行エンジンの PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill スイッチファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか ("1" = true、開発用。デフォルト "0")

その他
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）

※ 詳細は `kabusys.config.Settings` を参照してください。

---

## 使い方（起動コマンド）

主要なエントリポイントはモジュールとして実行できます。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使用して監視ログを記録します（環境に依らず）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラムからの呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行するには OPENAI_API_KEY を環境変数か引数で渡す必要があります。

停止 / Kill スイッチ
- 管理者が ExecutionEngine を安全に止めたい場合、`KILL_FLAG_PATH`（デフォルト data/kill.flag）に文字列を書き込むことで KillSwitch を発火させられます。KillSwitch は条件により自動で書き込まれることもあります。

ログ
- ログは標準で stdout に出力され、logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリは LOG_DIR 環境変数で変更可能。

---

## 開発用ユーティリティ

- ロギング設定: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- プロセス優先度: kabusys.utils.process_priority.set_process_priority("high")
- DB マイグレーションやテーブル作成は monitoring_db.init_monitoring_db を通して行われます（冪等）。

---

## ディレクトリ構成（抜粋）

以下は主要なパッケージ・ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数の読み込み・Settings クラス（.env 自動ロード機構含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI を使った銘柄別センチメント）
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py — ファクター計算（momentum／value／volatility）
    - feature_exploration.py — 研究用の統計・IC 計算
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（risk_based 等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成と読み書き API
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — （trade ロジック：滞留注文等の検出）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねる実行器
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定

data/ と logs/ はランタイムに使用するディレクトリ（デフォルト）。
- data/monitoring.db（監視ログ SQLite）
- data/paper_trading.db（ペーパートレード用 SQLite、KABUSYS_ENV=paper_trading 時）
- data/kabusys.duckdb（DuckDB）
- data/execution.pid（ExecutionEngine の PID）
- data/kill.flag（KillSwitch 用フラグ）

---

## 注意事項 / 運用メモ

- KABUSYS_ENV の設定により動作モードが変わります。`live` モードは実際に発注が行われるため運用時は設定に注意してください。
- `.env` は機密情報（API キー等）を含むため、絶対にリポジトリにコミットしないでください。
- OpenAI API を使用する機能は API キーと利用料金が必要です。レート制限や API エラーに対してはリトライ・フェイルセーフ処理を行っていますが、運用環境ではモニタリングを強化してください。
- run_monitoring と run_execution は外部からフラグファイル（data/stop_requested.flag 等）を検出して停止できます（スクリプト内で参照）。
- DB マイグレーションは簡易な ALTER TABLE を用いた互換性維持処理を行っていますが、大掛かりな変更がある場合は注意してください。

---

この README はコードベース（src/kabusys 以下）を元に作成した概要です。各機能の詳細（パラメータやアルゴリズムの仕様）は該当ソースコードやドキュメント（存在する場合）を参照してください。質問や補足が必要であればお知らせください。