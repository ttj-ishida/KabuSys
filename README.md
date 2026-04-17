# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム KabuSys のコアモジュール群です。  
ここに含まれるコードは、戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、研究用ファクター計算、AI を使ったニュース解析などのコンポーネントから構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

- 自動売買ロジック（シグナル生成やポートフォリオ構築）と、実際の発注を担う ExecutionEngine を含む。
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）でシステム・注文・リスクを常時チェックし、必要時に Kill Switch を作動させられる。
- Paper Trading（模擬発注）モードをサポートし、本番 DB と分離された専用 SQLite を利用する。
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB に使用。
- OpenAI（gpt-4o-mini）を利用したニュース NLP / レジーム判定機能を持つ（APIキーが必要）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（注文管理・発注・リスク管理・照合）
  - Broker クライアント抽象化（本番/モックを切り替え可能）
  - Paper Trading モード（実DBとは分離して data/paper_trading.db を利用）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・Executionプロセスの監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウンやポジション上限の監視とログ化
  - MonitoringEngine：上記モニタのポーリング統括、Kill Switch の判定とアラート発行
  - kill.flag による Execution 停止（Kill Switch）
- Portfolio
  - 候補選定、重み計算（等配分／スコア加重）
  - セクター制限・レジーム乗数適用
  - 発注株数決定（リスクベース、lot 単位丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム／バリュー／ボラティリティ）
  - 将来リターン計算、IC（スピアマン）などの統計ツール
- AI
  - ニュースセンチメント（OpenAI を用いた銘柄別スコア化）
  - 市場レジーム判定（MA200 とマクロニュースの LLM 評価を合成）
- ツール
  - 設定ウィザード（.env の対話式作成）
  - 設定検証 CLI（.env と config/*.yaml の検証）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型記法などを使用）
- SQLite（標準ライブラリ）、その他一部ライブラリは pip で追加

推奨手順:

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - 設定検証で YAML をチェックしたい場合: pip install PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. .env の準備
   - 対話式ウィザードで生成（推奨）:
     - python -m kabusys.config_setup
   - または .env.example を参照して手動で .env を作成
   - 自動ロード: コードはプロジェクトルート（.git または pyproject.toml を探索）にある .env/.env.local を自動で読み込みます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（最低限設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/...
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

注意:
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番用 SQLite を使わず PAPER_TRADING_SQLITE_PATH を使用します（本番データと分離）。
- 監視（run_monitoring）は KABUSYS_ENV に関わらず本番 sqlite_path（settings.sqlite_path）を参照して監視テーブルを扱います。

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml の検証）
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - Paper Trading の場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading モードでは MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録されます。
  - 実行中に停止するにはプロセスを終了するか、プロジェクトルート/data/stop_requested.flag を作成してください（run_execution はこのフラグを監視して安全に終了します）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring も同様に data/stop_requested.flag によってループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで explicit に DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（ニューススコアやレジーム判定）は OpenAI API キーが必要:
  - 環境変数 OPENAI_API_KEY を設定するか、呼び出し API に直接キーを渡す設計。

プロセス優先度:
- 起動スクリプト（run_execution/run_monitoring）は起動直後にプロセス優先度を "high" に設定しようとします（psutil が必要）。権限がない場合は警告を出してスキップします。

Kill Switch と停止フラグ:
- KillSwitch は設定された flag_path（デフォルト data/kill.flag）を作成して ExecutionEngine 停止を要求します。Monitoring の評価で Kill Switch がトリガーされた場合、kill.flag が書き込まれ、ExecutionEngine が起動時や定期チェックでこれを検出して安全に停止する設計です。
- run_execution/run_monitoring は data/stop_requested.flag を検出して即時終了します（外部運用で手動停止に使えます）。

ログ:
- 標準出力に INFO レベルで出力されます（LOG_LEVEL で上書き可能）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・パッケージと役割の簡単な一覧（src/kabusys 配下）:

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定の読み取り・検証・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/ (発注関連: Engine, OrderManager, RiskManager 等) — （実装ファイルは本リポジトリ全体に存在）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 層（init / CRUD）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン等の監視
    - monitoring_engine.py — 各モニタ統括ポーリング
    - kill_switch.py — Kill Switch 実装（kill.flag 書き込み）
    - alert_manager.py — アラート通知管理（未表示）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・制約処理
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄別スコアを作成
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

data/ 以下（実行時に作られる想定）
- data/kabusys.duckdb（DuckDB のデフォルトパス）
- data/monitoring.db（監視用 SQLite）
- data/paper_trading.db（Paper Trading 用 SQLite）
- data/execution.pid（ExecutionEngine の PID ファイル）
- data/kill.flag（Kill Switch 用フラグ）
- data/stop_requested.flag（スクリプト強制停止用フラグ）

---

## 注意点・トラブルシューティング

- 必須環境変数が未設定だと起動時に ValueError を投げます。まずは config_setup による .env の準備 → validate_config の実行を推奨します。
- validate_config は PyYAML が未インストールだと config/*.yaml の中身チェックをスキップして警告を出します。YAML 検証が必要なら PyYAML をインストールしてください。
- OpenAI 関連機能は API キー（OPENAI_API_KEY）が必須です。キー未設定だと関数が ValueError を投げます。
- run_monitoring は MONITOR_POLL_INTERVAL によるポーリング間隔変更をサポートします。無効な値がセットされるとデフォルトの 60 秒にフォールバックします。
- Paper Trading モードは本番 DB と分離されますが、設定ミスで本番 DB を上書きしないよう .env や環境変数を必ず確認してください（KABUSYS_ENV の設定が重要）。
- プロセス優先度や CPU affinity の設定は OS の権限に依存します。権限不足だと設定に失敗して警告が出ますが処理自体は継続します。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に対して足りないカラムを追加する簡易マイグレーションを行います。

---

もし README に追加したい情報（詳細な API 使用例、設定ファイルテンプレート、運用手順、デプロイ手順など）があれば教えてください。必要に応じてサンプル .env テンプレートや systemd ユニットの例も作成できます。