# KabuSys — 日本株自動売買システム (README)

本リポジトリは日本株の自動売買・リサーチ・監視を行うための Python コード群です。  
ここではプロジェクトの概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

なお、本 README はコードベースのソース（src/kabusys/*.py）を参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム／研究ツール群です。  
主な目的は次のとおりです。

- シグナル生成・銘柄選定・ポジションサイジング（ポートフォリオ構築）
- ExecutionEngine による注文発行（本番・ペーパートレード対応）
- モニタリング（プロセス、生存率、滞留注文、リスクイベント等）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI（LLM）を使ったニュースセンチメントの評価・市場レジーム判定
- ペーパートレード検証レポート生成

設計方針としては「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「外部 API 呼び出しは明示的でフェイルセーフ」などが採用されています。

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV による mode 切替：development / paper_trading / live
  - paper_trading 時は MockBrokerClient を使用し、専用 SQLite DB に記録

- 監視関連
  - SystemMonitor：CPU/Memory/Disk、データ鮮度、Execution プロセス生存確認
  - TradeMonitor：滞留注文、約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限検知、ダッシュボード更新
  - KillSwitch：リスク条件で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine / run_monitoring スクリプトによるポーリング実行（MONITOR_POLL_INTERVAL 環境変数で間隔指定可能）

- ポートフォリオ構築
  - 候補選定（score に基づくソート）
  - 等金額・スコア重み配分
  - セクター集中制限、レジーム乗数
  - ポジションサイジング（ロット丸め、リスクベース等）

- リサーチ
  - ファクター算出（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI（LLM）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に格納
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM 評価を合成して日次レジーム判定

- ツール
  - 環境ウィザード（python -m kabusys.config_setup）で .env を対話生成
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ペーパートレード検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

以下は最低限の手順例です。環境に合わせて調整してください。

1. Python 仮想環境を作成・有効化（推奨: venv / pyenv 等）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合、代表的な依存は次の通りです:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証で使用、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに .env ファイルを作成
   - 対話ウィザードを使用する:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（代表例）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、default: data/paper_trading.db)
     - OPENAI_API_KEY (AI モジュール利用時必須)
     - LOG_LEVEL

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリ作成
   - data/ ディレクトリ等が必要です。スクリプト起動時に自動作成されることもあるが、権限等で失敗する場合は手動で作成してください。

注意:
- AI 機能を使う場合は OpenAI API キーが必要です（OPENAI_API_KEY）。
- プロセス優先度設定等は OS 権限に依存します。psutil による nice/priority 設定が権限不足で失敗することがあります（警告ログのみ）。

---

## 使い方（主要コマンド）

各モジュールは Python モジュール実行方式で起動できます。プロジェクト root で実行してください。

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告も FAIL）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（注文処理）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で制御
    - paper_trading: MockBrokerClient を使い paper_trading DB に記録（PAPER_TRADING_SQLITE_PATH）
    - live: 実ブローカークライアントを使用（KABU_API_PASSWORD 等が必要）
  - 停止制御:
    - data/stop_requested.flag（実行スレッドが存在する場合は検知して停止）
    - data/kill.flag（KillSwitch により作成されると起動・継続を妨げる）

- Monitoring 起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書き: MONITOR_POLL_INTERVAL 環境変数（秒、デフォルト 60）
  - 監視は常に settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依らない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーは引数か環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError を送出します。

---

## 重要な挙動メモ / 安全上の注意

- データベース
  - デフォルトの DuckDB: data/kabusys.duckdb
  - デフォルトの SQLite (監視): data/monitoring.db
  - Paper Trading 用 SQLite は settings.is_paper の場合に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と分離

- Kill Switch / Stop フラグ
  - data/kill.flag: KillSwitch により書き込まれ、ExecutionEngine に停止指示を出す（ファイル存在で検出）
  - data/stop_requested.flag: run_execution/run_monitoring の外部停止フラグ（これを置くとループを抜ける）
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定するとリスク（自動クリア）になるため注意

- 環境自動ロード
  - config.Settings はプロジェクトルートの .env/.env.local を自動ロードする機能を持ちます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

- AI（OpenAI）に関する注意
  - API 呼び出しはネットワークエラーや 429/5xx を考慮してリトライ実装がありますが、API キー未設定は即時エラーとなります
  - レスポンスのバリデーションを厳密に行いますが、LLM の出力不正時はスキップ動作となるため一部データが欠落することがあります

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュール構成（本コードベースから抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings 管理（.env ロード）
    - config_setup.py              — .env 対話ウィザード
    - validate_config.py           — 起動前設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート
    - ai/
      - __init__.py
      - news_nlp.py                — ニュースを LLM でスコアリングして ai_scores に書込
      - regime_detector.py         — 市場レジーム判定（MA + LLM）
    - research/
      - __init__.py
      - factor_research.py         — モメンタム/バリュー/ボラティリティ等
      - feature_exploration.py     — IC / 将来リターン / 統計サマリー
    - portfolio/
      - __init__.py
      - portfolio_builder.py       — 候補選定・重み算出
      - risk_adjustment.py         — セクターキャップ・レジーム乗数
      - position_sizing.py         — 発注株数計算・上限・ロット丸め
    - monitoring/
      - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs 等）
      - system_monitor.py          — CPU/MEM/DISK/データ鮮度/プロセス監視
      - trade_monitor.py           — 滞留注文・約定異常監視
      - risk_monitor.py            — ドローダウン/ポジション上限監視
      - monitoring_engine.py       — 各モニタ束ねてポーリング
      - kill_switch.py             — kill.flag 書込ロジック
      - alert_manager.py           — （未表示: アラート送信ロジック）
    - execution/                    — Execution 系（OrderManager 等; 一部ファイルは省略）
    - data/                         — データ関連ユーティリティ（pipeline, stats 等; 一部省略）
    - utils/
      - __init__.py
      - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ

（実際のリポジトリには上記以外にも多くの補助モジュールや実装ファイルがあります）

---

## トラブルシューティング / よくある問題

- 「必須環境変数が未設定」エラー
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など必須値が .env に設定されているか確認してください。
  - python -m kabusys.config_setup で対話的に設定できます。

- OpenAI 関連のエラー
  - OPENAI_API_KEY が設定されていないと AI モジュールの関数は ValueError を送出します。
  - API の RateLimit / 接続障害はログに WARN/INFO が出力され、リトライ後失敗すると該当処理がスキップされます。

- psutil 関連の権限エラー
  - set_process_priority() の実行は OS と権限に依存します。権限不足の場合は警告ログが出て処理は継続します。

- DB ファイルの場所・権限
  - data/ 配下の DB ファイル（デフォルト）に書き込み権限があるか確認してください。パスは環境変数で上書き可能です。

---

## 最後に

この README はコードベースの主要機能・運用フローを簡潔にまとめたものです。  
個々のモジュールやクラスの詳細な使い方はソース内の docstring / コメントを参照してください。README にない運用ケースや拡張はソースを読み、必要に応じてテスト環境で十分に検証してください。

ご不明点があれば、どの部分について知りたいかを教えてください。追加で詳しい使用例やデプロイ手順を作成できます。