# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、アルゴリズムトレーディングに関する主要コンポーネント（信号生成、ポートフォリオ構築、発注エンジン、監視、AI 補助、研究用ユーティリティ）を含むモジュール群です。設計方針として「本番環境とペーパートレードの分離」「ルックアヘッドバイアス回避」「外部 API 呼び出しは明示的制御」「監視・Kill Switch による安全停止」を採用しています。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト / コマンド）
- 環境変数（主なもの）
- ファイル・ディレクトリ構成

---

## プロジェクト概要

- マーケットデータ（DuckDB / prices_daily など）を用いたファクター計算・特徴量探索機能
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ付与、セクターキャップ）
- ExecutionEngine（発注ロジック、リスク管理、注文レポジトリ） — paper_trading モードをサポート
- 監視（System / Trade / Risk Monitor）と Kill Switch による自動停止
- AI（OpenAI）を利用したニュースセンチメント評価・レジーム判定
- 研究用ユーティリティ（IC 計算、フォワードリターン等）
- ペーパートレード検証レポート生成ツール

---

## 機能一覧

- config_setup: 対話式で .env を生成/更新するウィザード
- validate_config: 起動前に .env と config/*.yaml の基本検証を行う CLI
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 切替）
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整可能）
- monitoring: system_status / trade_logs / risk_logs / dashboard 等を管理する永続層（SQLite）
- Kill Switch: 指定閾値を超えた場合に data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
- portfolio: 候補選定、等重 / スコア加重、リスク調整（セクター制限、レジーム乗数）、ポジションサイズ計算
- research: ファクター計算（mom/value/volatility）、特徴量解析（forward returns, IC, summary）
- ai: OpenAI を用いたニュースのスコアリング（news_nlp）と市場レジーム判定（regime_detector）
- tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等を集計）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（typing のユニオン書式などを利用）
- SQLite（標準で同梱）、ローカルに DuckDB を導入する必要あり

推奨インストール（仮想環境内で実行）:

1. 仮想環境作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   必須パッケージ（最低限）:
   - duckdb
   - psutil
   - openai
   - (任意) PyYAML — validate_config で config/*.yaml 検証を行う場合

   例:
   - pip install duckdb psutil openai pyyaml

   ※ 実運用ではさらに依存パッケージ（HTTP クライアント等）やバージョン固定が必要です。
   requirements.txt がない場合はプロジェクトの需要に合わせて作成してください。

3. 初期設定 (.env) を作成
   - python -m kabusys.config_setup
     → 対話式ウィザードで必須変数を設定します（J-Quants トークン、kabu API パスワード等）。

4. 設定検証（任意 / 推奨）
   - python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります。

5. ディレクトリ作成
   - data/ フォルダや logs/ フォルダは自動で作成される場合がありますが、必要に応じて手動で作成してください。
   - 実行ユーザーに対する書き込み権限を確認してください。

---

## 使い方

主要スクリプトは Python モジュールとして起動します。例:

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。
  - ExecutionEngine は paper_trading の場合、デフォルトで data/paper_trading.db を使用します。

- Monitoring（ポーリング監視）を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を参照します（環境に依存しません）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / 研究系関数の利用（ライブラリ呼び出し）
  - Python スクリプト内でインポートして呼び出します。例:
    - from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    - from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    - from kabusys.research import calc_momentum, calc_volatility, calc_value

注意点
- run_execution は起動時に process priority を高に設定します（utils.process_priority）。
- run_monitoring はポーリングループ内で SystemMonitor.check_once() を呼び、stop flag を監視します。
- Kill Switch はリスクアラート（ドローダウン・ポジション上限等）に応じて data/kill.flag を書き込み、ExecutionEngine 側はこれを検出して停止します。

---

## 主な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBrokerClient の約定挙動
  - 有効値: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI を利用する AI モジュールで使用
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（1=yes, 0=no。デフォルト 0）

---

## 停止 / Kill 手順

- 常時監視を止めたい / Execution を止めたい場合:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して安全に停止します（run_execution はスレッドの停止シグナルを送ります）。
- Kill Switch（リスクによる強制停止）:
  - monitoring モジュールが条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は設定された kill_flag_path を参照して停止します。
- kill.flag を手動でクリアしたい場合:
  - 実行中のシステムで clear 操作（KillSwitch.clear()）またはファイルを削除してください。
  - 本番では KILL_FLAG_CLEAR_ON_START の自動クリアを無効にすることを推奨します（デフォルト 0）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋、src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（OpenAI）で ai_scores を生成
    - regime_detector.py    — レジーム判定（MA + マクロ NLP 合成）
  - research/
    - __init__.py
    - factor_research.py    — mom/value/volatility 等のファクター計算
    - feature_exploration.py— forward returns, IC, summary
  - portfolio/
    - __init__.py
    - portfolio_builder.py  — 候補選定・等重/スコア重み
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
    - position_sizing.py    — 株数決定・キャップ適用
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ定義 + MonitoringDB（読み書き層）
    - monitoring_engine.py  — 複数モニターを束ねるエンジン
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （存在）注文ログ・滞留検出など
    - risk_monitor.py       — ドローダウン・ポジション制限監視
    - kill_switch.py        — kill.flag の作成・評価
    - alert_manager.py      — LINE 等へ通知するマネージャ（実装あり）
  - utils/
    - __init__.py
    - logging_setup.py      — ロギング初期化ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - execution/              — 発注エンジン関連（OrderManager, BrokerFactory, ExecutionEngine 等）
  - data/                   — 実行時 DB / flag / pid を配置する想定パス（例: data/*.db, data/kill.flag）

補足:
- monitoring_db.py は監視関連の SQLite テーブルを作成（冪等）します。
- logging_setup.py は stdout の StreamHandler と日次ローテートファイルハンドラ（logs/<app>.log）を設定します。

---

## 注意事項 / 運用上のヒント

- .env は機密情報を含むため Git にコミットしないでください（config_setup でもその旨の警告を出します）。
- KABUSYS_ENV=live の場合は特に注意。validate_config はいくつかのガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認等）を行います。
- Paper Trading 用 DB は本番 DB と分離されています（settings.is_paper の場合 paper_sqlite_path を使用）。
- OpenAI API 呼び出しに関しては、API 失敗時にフェイルセーフ（0.0 やスキップ）で動作するよう設計されていますが、使用量/レート制限には注意してください。
- ログディレクトリの作成に失敗するとコンソール出力のみで継続します。ログ出力先は LOG_DIR で上書きできます。
- プロセス優先度設定はプラットフォーム依存のため失敗する場合があります（例外は警告に変換されます）。

---

この README はコードベースの主要機能と使い方の概要を示したものです。より詳細な設計文書（PortfolioConstruction.md、StrategyModel.md 等）や config/*.yaml のテンプレートがあれば、それらも参照して運用・拡張を行ってください。質問やドキュメントの追加希望があればお知らせください。