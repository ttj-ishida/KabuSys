# KabuSys

日本株の自動売買（バックテスト／ペーパートレード／実運用）を想定した小規模フレームワークです。  
このリポジトリは、データ処理（DuckDB）、ポートフォリオ構築、発注実行、監視（監視ログ、Kill Switch）、AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 株価データ・財務データからファクターを算出するリサーチ機能（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine（発注・注文管理・リスク管理） — 本番とペーパーを分離
- 監視機能（System / Trade / Risk モニタ）と Kill Switch（危険時に発注エンジン停止）
- AI（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証など）
- 解析用ツール（Paper Trading 検証レポート生成）

設計上の特徴：
- DuckDB を分析向け DB として利用
- 監視データ等は SQLite に永続化
- .env による環境変数管理と対話式ウィザード（config_setup）
- OpenAI を利用する処理は API キーが必要（環境変数または引数で指定）

---

## 機能一覧

主要な機能・スクリプト（抜粋）:

- 設定関連
  - `kabusys.config_setup` : .env を対話式に作成・更新するウィザード
  - `kabusys.validate_config` : .env と config/*.yaml の事前検証（--strict オプション有）

- 実行系スクリプト
  - `run_execution.py` : ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使い DB を分離（`data/paper_trading.db` 等）
  - `run_monitoring.py` : SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔調整）

- 監視・アラート
  - system / trade / risk の監視モジュール（DB へログ persist）
  - Kill Switch: ドローダウンやポジション上限等で `data/kill.flag` を書き込み ExecutionEngine を停止可能

- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数

- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）関係
  - `kabusys.ai.news_nlp.score_news` : ニュースを LLM でスコアリングして `ai_scores` に書き込み
  - `kabusys.ai.regime_detector.score_regime` : ma200 乖離と LLM マクロセンチメントを合成して市場レジームを判定・永続化

- ツール
  - `kabusys.tools.paper_verification_report` : Paper Trading の検証レポートを生成

- ユーティリティ
  - ログ設定（Console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（プラットフォーム差分吸収）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（コード内で Python の新しい型構文を使用）
- SQLite は標準ライブラリで問題なし
- システムによっては psutil の権限（プロセス優先度や affinity）が必要

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - requirements.txt が用意されていれば:
     - pip install -r requirements.txt
   - 本リポジトリのコードで必要となる主要パッケージ:
     - duckdb, psutil, openai, PyYAML (オプション: config YAML 検証用)
     - 例: pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザード実行後、`.env` がプロジェクトルートに保存されます。
   - 主要な環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (デフォルト: INFO)
     - OPENAI_API_KEY（AI 機能を使う場合に必要）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）

   - 自動ロード: 起動時に .env が自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - .env は絶対に VCS にコミットしないでください。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も厳密にチェックしたい場合: python -m kabusys.validate_config --strict

---

## 使い方

### 監視（Monitoring）を起動
- デフォルトでは 60 秒間隔でポーリングします（環境変数で上書き可）。
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 停止方法:
  - スクリプトはプロジェクトルート配下の `data/stop_requested.flag` を検知するとループを抜けます（または Ctrl+C）。

注意:
- Monitoring は KABUSYS_ENV に関わらず本番 SQLite（Settings.sqlite_path）を使用して監視データを格納します。

### ExecutionEngine を起動
- python -m kabusys.run_execution
- KABUSYS_ENV による動作:
  - `paper_trading` の場合は MockBrokerClient を使い、paper 用 SQLite（Settings.paper_sqlite_path）に記録して本番 DB と完全分離します。
  - `live` の場合は実際のブローカークライアントを使って発注します（実装による）。
- 停止方法:
  - プロジェクトルートの `data/stop_requested.flag` を作ると起動中エンジンは検知して停止します。
  - Kill Switch（リスク発動）は `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側は起動時に kill.flag をクリアするオプション設定があります）。

### Paper Trading 検証レポートを生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を直接指定:
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

### AI（ニュースセンチメント / レジーム判定）
- OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に `api_key` 引数を渡してください。
- 例（スクリプト経由ではなくプログラムから）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="sk-...")

失敗対策:
- API が失敗した場合はリトライやフォールバックを行う設計ですが、APIキーの未設定は ValueError を投げます。

---

## 主要な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — デフォルト: development. 値: development | paper_trading | live
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- OPENAI_API_KEY — AI 機能使用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring 用ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant|partial|never|reject）

（詳しい説明は `kabusys.config.Settings` クラス内に記載されています）

---

## よく使うコマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視開始:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- （開発）モジュールの関数を Python から直接利用:
  - python -c "from kabusys.research import calc_momentum; print('ok')"

---

## トラブルシューティング / 運用メモ

- ログ:
  - デフォルト出力先は `logs/` ディレクトリに日次ローテートされます。権限問題で作成に失敗した場合は標準出力のみで動作します。
- psutil によるプロセス優先度設定は管理者権限が必要な場合があります。失敗した場合は警告をログに出して継続します。
- DuckDB / SQLite のファイルパスの親ディレクトリが存在しない場合は警告が出ます。起動スクリプト側でディレクトリを作成することを推奨します（`data/` 等）。
- Kill Switch / stop flag:
  - 手動停止や緊急停止用に `data/kill.flag` / `data/stop_requested.flag` を利用します。フラグファイルの存在チェックや書き込みは冪等に実装されています。
- OpenAI 使用時の注意:
  - レート制限やネットワーク障害に対するエクスポネンシャルバックオフが実装されていますが、APIキーの管理やコストには注意してください。

---

## ディレクトリ構成

（重要なファイル・モジュールのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込みロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite スキーマ & 永続化層
    - system_monitor.py — CPU/Mem/Disk/データ鮮度監視
    - trade_monitor.py — 注文状態監視（ファイルには同梱）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - kill_switch.py — Kill Switch 書き込みユーティリティ
    - alert_manager.py — （アラート送信の抽象）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・集計キャップ
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング
    - regime_detector.py — 市場レジーム判定（ma200 + LLM）
  - monitoring/ など（上記参照）

- data/ (デフォルト)
  - monitoring.db (SQLite)
  - paper_trading.db (ペーパートレード用 DB)
  - kill.flag, stop_requested.flag, execution.pid などの制御ファイル

- logs/ (デフォルト)
  - execution.log, monitoring.log, ...（日次ローテート）

---

## ライセンス・貢献

このリポジトリのライセンス情報やコントリビュート方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合はメンテナに問い合わせてください）。

---

README は以上です。必要であれば以下を追加で生成します：
- requirements.txt の推定内容
- .env.example のテンプレート
- 起動 / デプロイの systemd / supervisor サンプルユニット

どれが必要か教えてください。