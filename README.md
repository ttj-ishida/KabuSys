# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システムのコアライブラリ群です。戦略研究用のファクター計算、ポートフォリオ構築、発注エンジン、監視（モニタリング）や運用補助ツール（ペーパートレード検証・AI を使ったニューススコアリング等）を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のコンポーネントで構成されます。

- execution: 発注エンジン（ExecutionEngine）およびブローカークライアントの抽象化。  
  KABUSYS_ENV によって paper_trading（モックブローカー）/ live（実口座）を切り替え可能。
- monitoring: システムの稼働監視・データ鮮度・取引状態・リスク監視・Kill Switch（停止用フラグ）管理。
- research: DuckDB を使ったファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）。
- portfolio: 候補選定、重みづけ、ポジションサイズ決定、セクター制限、レジーム補正など。
- ai: OpenAI を利用したニュースの NLP スコアリング（ニュース→センチメント）と市場レジーム判定。
- tools: レポート作成ツール等の補助スクリプト。

設定は環境変数（.env）で管理し、データはデフォルトで `data/` 以下の SQLite / DuckDB に格納します。

---

## 主な機能

- system_monitor: CPU/メモリ/ディスク使用率、発注プロセスの生存確認、データ鮮度検査（DuckDB）。
- trade_monitor: 発注ログの監視（滞留注文、約定異常など）。
- risk_monitor: ドローダウン検知、ポジション数上限の検出・ログ。
- Kill Switch: 条件に応じて `data/kill.flag` を作成し ExecutionEngine に停止指示を出す。
- ExecutionEngine: ブローカークライアント経由の発注・注文管理（paper_trading 対応）。
- portfolio モジュール: 候補選出、重み計算、株数決定（lot 単位丸め、aggregate cap）。
- research モジュール: DuckDB からファクター/将来リターン/IC の算出。
- ai.news_nlp: OpenAI を用いたニュースセンチメント集約と ai_scores テーブルへの書き込み。
- ユーティリティ: ログセットアップ、プロセス優先度設定、設定ウィザード、設定検証 CLI。

---

## 必要条件 / 依存

（このリポジトリに requirements.txt が無い場合、最低限の依存を手動でインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config file 検証を使う場合）
- （必要に応じて）その他ライブラリ

例（pip）:
pip install duckdb psutil openai PyYAML

注意: OpenAI クライアントは v1 API のインターフェースを利用します。利用する環境に合わせて適切な SDK バージョンを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール
   pip install duckdb psutil openai PyYAML
4. data / logs ディレクトリを作成（自動で作られる場合もありますが明示的に作ると安全です）
   mkdir -p data logs
5. .env の作成（対話式ウィザード推奨）
   python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード等の設定を支援します。
6. 設定の検証
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか: 0/1）

例 (.env 抜粋):
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視プロセス起動（ポーリングループ）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は data/monitoring.db（Settings.sqlite_path）にログを残します。
  - 停止させるにはプロセスを SIGINT（Ctrl+C） するか、プロジェクトルートの data/stop_requested.flag を作成。

- 発注エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker（paper） を使い data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が既に存在すると起動しません。
  - 実行中に data/stop_requested.flag を作るとエンジン停止を促します。
  - ExecutionEngine の PID はデフォルトで data/execution.pid に書き込まれます。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング（プログラムから呼ぶ）
  from kabusys.ai import score_news
  # DuckDB 接続を作成して score_news(conn, target_date, api_key=...)
  - OPENAI_API_KEY を環境変数に設定するか、api_key を渡します。

- 市場レジーム判定（プログラムから呼ぶ）
  from kabusys.ai.regime_detector import score_regime
  # DuckDB 接続と target_date を渡して実行

---

## ロギング

- デフォルトでは logs/ ディレクトリにアプリケーション名ごとの日次ローテートログを書きます（例: logs/execution.log）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を起動スクリプトで呼び出して統一しています。

---

## Kill Switch / 停止フラグ

- KillSwitch は条件が満たされると `data/kill.flag` を書き込み、ExecutionEngine に停止を促します（ExecutionEngine は kill.flag を監視し、存在すれば停止する挙動を実装してください）。
- 手動でエンジン停止を指示したい場合は `data/kill.flag` を書くことで停止させることができます（または `data/stop_requested.flag`）。

注意: 本番（KABUSYS_ENV=live）の場合、KILL_FLAG_CLEAR_ON_START=1 の設定は危険です（起動時に自動で kill.flag が消されるため）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                   — 環境変数 / 設定読み込みロジック（.env 対応）
- config_setup.py             — .env 作成ウィザード（対話式）
- validate_config.py          — 設定検証 CLI
- run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py            — ExecutionEngine 起動スクリプト

src/kabusys/ai/
- news_nlp.py                 — ニュースを OpenAI でスコアリングして ai_scores に書込み
- regime_detector.py          — マクロ + ETF MA による市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py            — SQLite 監視ログ DB（テーブル定義・ラッパー）
- system_monitor.py           — CPU/メモリ/ディスク・データ鮮度・プロセス監視
- trade_monitor.py            — (取引ログ監視) ※実装参照
- risk_monitor.py             — ドローダウン・ポジション上限監視
- monitoring_engine.py        — 複数モニタを束ねるエンジン
- kill_switch.py              — Kill Switch（flag 書き込み）ロジック
- alert_manager.py            — (外部通知) ※実装参照

src/kabusys/execution/
- execution_engine.py         — 発注エンジン（EngineConfig 等）
- broker_factory.py           — BrokerClient の生成（実ブローカ / Mock 切替）
- order_manager.py            — 注文管理
- order_repository.py         — 注文履歴の永続化
- reconciler.py               — 注文照合処理
- risk_manager.py             — 実行時リスク制御

src/kabusys/research/
- factor_research.py          — Momentum / Value / Volatility 等の計算（DuckDB）
- feature_exploration.py      — 将来リターン / IC / 統計サマリー

src/kabusys/portfolio/
- portfolio_builder.py        — 候補選定・重み計算
- position_sizing.py          — 株数計算（リスクベース・等分配など）
- risk_adjustment.py          — セクターキャップ・レジーム乗数

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポート生成ツール

src/kabusys/utils/
- logging_setup.py            — ログ初期化ユーティリティ
- process_priority.py         — プロセス優先度 / CPU affinity

その他:
- config/*.yaml               — 各種設定テンプレート（generate_config.py 等で生成を想定）
- data/                       — データファイル置き場（SQLite/DuckDB、フラグファイル）
- logs/                       — ログ出力先

---

## 開発上の注意・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では設定内容を十分にレビューしてください。validate_config の警告を確認のこと。
- .env は Git 管理しない（README 内にも注意書きあり）。
- OpenAI を利用する処理は API 呼び出しで失敗した場合フェイルセーフ（0やスキップ）で継続する設計ですが、API キー漏洩に注意してください。
- paper_trading モードは実口座と DB を分離（PAPER_TRADING_SQLITE_PATH）します。運用時の混同に注意。
- ログディレクトリ作成に失敗した場合はコンソールログのみになります。権限等を確認してください。

---

## よく使うコマンド一覧（まとめ）

- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 発注エンジン起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要な利用方法と構造を簡潔にまとめたものです。追加のスクリプトや詳細な設計（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクトに含まれている場合はそちらも参照してください。必要であれば README を英語版に翻訳したり、実行例やトラブルシュートの節を追加します。