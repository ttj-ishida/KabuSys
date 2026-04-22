# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群を収めたパッケージです。  
以下はリポジトリの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要
KabuSys は以下の主要コンポーネントを備えたシステムです。

- ExecutionEngine：発注・注文管理・リスク制御を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文状態・リスクの継続監視とアラート発行
- Portfolio construction：候補選定・重み付け・株数算出などのポートフォリオ構築ロジック（純粋関数）
- Research：ファクター計算・特徴量探索・IC計算等のリサーチ機能（DuckDB 経由）
- AI モジュール：ニュースを LLM で解析してセンチメントや市場レジームを評価（OpenAI）
- ユーティリティ：ログ設定、プロセス優先度、設定ウィザード、設定検証ツール 等

設計上のポイント：
- 設定は環境変数 / .env で管理。実行前にウィザード/検証ツールで確認可能。
- DuckDB（分析用）と SQLite（監視・発注ログ等）を併用。
- Paper trading（KABUSYS_ENV=paper_trading）をサポートし、本番 DB と明確に分離。
- 外部 API（OpenAI 等）は明示的に API キーを渡すか環境変数で設定。

---

## 主な機能一覧
- 実行（ExecutionEngine）
  - ブローカークライアント抽象化（本番 / Mock）
  - 注文管理・リスク管理（上限・ドローダウン等）
  - 発注履歴 / 監視情報の永続化（SQLite）
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス監視
  - 注文滞留・約定異常・リスクイベントの検知とログ化
  - Kill Switch（条件に応じて data/kill.flag を書いて Execution を止める）
- ポートフォリオ関連
  - 候補選定（スコア降順・上位 N）
  - 重み計算（等分 / スコア加重）
  - 株数決定（リスクベース、上限、lot 単位で丸め）
  - セクター上限適用・レジームに応じた乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC（Spearman）、統計サマリ
- AI
  - ニュースセンチメントスコア（OpenAI API）
  - 市場レジーム判定（ETF MA とマクロニュースの LLM 評価）
- ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート出力ツール（paper_verification_report）

---

## 必要な依存（代表）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定 YAML の内容検証を行う場合、任意）

パッケージは環境に応じて pip 等でインストールしてください。

---

## セットアップ手順（開発・初回導入向け）
1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化し依存をインストール
   - 例: python -m venv .venv && source .venv/bin/activate
   - 例: pip install -r requirements.txt （ファイルがあれば）
   - 必要に応じて duckdb, psutil, openai, PyYAML をインストール
3. 環境変数設定
   - .env を作成するには対話式ウィザードを利用できます（推奨）:
     - python -m kabusys.config_setup
   - ウィザードで作成/更新した .env はプロジェクトルートに保存されます（.env は Git にコミットしないでください）
   - 自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で読み込み（既定）
     - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. 設定検証（起動前に必ず実行してください）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict
5. データディレクトリ等
   - デフォルトでは以下のファイルパスを使用します（必要に応じて .env で上書き）
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - ログ設定ユーティリティは起動時に logs ディレクトリを作成します（作成失敗時はコンソール出力のみ）

---

## 主要な環境変数（代表）
- 必須（実行前に設定）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
    - paper_trading 設定時は MockBroker を利用し paper DB（PAPER_TRADING_SQLITE_PATH）に記録する
- DBパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- ログ・プロセス
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR — ログ格納先（デフォルト: logs/）
  - PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- モニタリング
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- ペーパートレード挙動
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）
- AI
  - OPENAI_API_KEY — OpenAI を使う場合は設定（score_news / score_regime が利用）
- その他
  - KILL_FLAG_PATH — Kill Switch の flag パス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）

---

## 実行方法（例）
- 対話式 .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定します（set_process_priority）
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に書き込まれます
    - data/stop_requested.flag が存在すると起動を回避 / 停止します
- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
    - 監視モジュールは KABUSYS_ENV に関わらず本番の sqlite_path を使用するよう設計されています（監視データは単一 DB に集約）
    - data/stop_requested.flag を検出するとループを終了します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI 関連（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給

---

## ログと永続化
- ログ
  - setup_logging() により stdout と日次ローテーション（logs/<app_name>.log）に出力
  - デフォルト 30 日分を保持
- 永続化
  - 監視・注文履歴等は SQLite（設定可能）へ保存（monitoring_db モジュール）
  - 分析用データは DuckDB（DUCKDB_PATH）を利用

---

## Kill / Stop の仕組み
- 停止フラグ
  - data/stop_requested.flag：run_execution / run_monitoring がチェックし、存在すると停止または起動抑止する（内部的に使用）
  - data/kill.flag：Kill Switch により書き込まれ、ExecutionEngine の停止トリガに使われる（KillSwitch）
- ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START が 1 なら kill.flag を削除できます（設定に注意）

---

## 主要ファイル・ディレクトリ構成（抜粋）
以下はパッケージ内の主要モジュールと簡単な説明です。ソースは src/kabusys 以下にあります。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス（環境変数 / .env 自動ロード・検証）
  - config_setup.py — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 起動前の設定検証ツール（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py — SystemMonitor ポーリングループ起動（python -m kabusys.run_monitoring）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と読み書きユーティリティ
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — （注文関連の監視・検出。実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch ロジック（flag ファイル書込）
    - monitoring_engine.py — 監視要素を束ねるエンジン
    - alert_manager.py — 通知管理（LINE 等、実装に依存）
  - execution/
    - execution_engine.py — 実行ロジック（EngineConfig, run_session 等）
    - broker_factory.py — ブローカークライアント生成（Mock / 実 API）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注関連
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・上限 / aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value などのファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントスコア（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 用の検証レポート生成スクリプト
  - utils/
    - logging_setup.py — ロギング初期化（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定

（実際のファイルはリポジトリに合わせて確認してください）

---

## 運用上の注意・推奨
- .env は機密情報を含むため Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）での起動前に必ず validate_config を実行して警告/エラーを確認してください。
- KillSwitch や KILL_FLAG_CLEAR_ON_START の設定には注意。特に本番で自動クリアは危険です（デフォルト 0 を推奨）。
- Paper trading を用いる場合でも、実行ロジックの一部は本番 DB と同じスキーマを参照するため、DB パスの設定を慎重に行ってください（paper_trading は paper_sqlite_path を利用）。
- OpenAI API を利用する処理は外部ネットワーク依存・課金対象なので、API キーの管理と呼び出し頻度に注意してください。

---

## よく使うコマンド一覧（まとめ）
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

必要があれば、各モジュール（ExecutionEngine・Monitoring・AI・ポートフォリオロジック等）の詳細な設計ドキュメントや運用手順（systemd / Supervisor 用のユニット例、バックアップ方針、メトリクス収集方法など）も作成します。どの情報がさらに欲しいか教えてください。