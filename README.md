# KabuSys — 日本株自動売買システム

これは日本株自動売買（Kabuステーション / J-Quants 等を利用）を目的とした管理/実行/監視ツール群のコードベースです。  
本リポジトリは取引エンジンの起動スクリプト、監視コンポーネント、ポートフォリオ構築ロジック、研究用ファクター計算、AI（ニュース NLP / レジーム判定）連携ユーティリティなどを含みます。

バージョン: 0.1.0

## 主な機能
- ExecutionEngine（発注実行）  
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（実口座 or Mock）
  - リスク管理（ポジション上限、ドローダウン等）
  - PID ファイル管理・停止フラグ検出
- Monitoring（監視）  
  - システム稼働監視（CPU / メモリ / ディスク / データ鮮度）
  - 発注/約定ログ・リスクログの永続化（SQLite）
  - Kill Switch（閾値超過時に実行エンジン停止フラグを出力）
  - アラート送信の仕組み（LINE などへ拡張可能）
- ポートフォリオ構築ユーティリティ（純粋関数）
  - 候補選定、重み計算（等ウェイト / スコア加重）
  - セクターキャップ、レジーム乗数
  - 発注株数決定（ロット丸め・リスクベース / ウェイトベース）
- 研究（Research）モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI連携
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA 乖離から市場レジーム判定（bull/neutral/bear）
- ツール
  - Paper Trading の検証レポート生成スクリプト（期間指定で集計出力）
- 設定管理
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 動作要件（想定）
- Python 3.10+
- 必須（例）
  - duckdb
  - psutil
  - openai
- あると便利（YAML 検証や追加機能）
  - PyYAML

（実際は requirements.txt をプロジェクトに追加して pip install -r requirements.txt をお使いください。）

---

## セットアップ手順（簡易）
1. リポジトリをクローンしてルートに移動
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （PyYAML を使う場合）pip install pyyaml
4. .env 作成（対話式）
   - python -m kabusys.config_setup
     - 対話で J-Quants トークン / Kabu API パスワード 等を入力し .env を生成します。
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

---

## 環境変数（主要）
config_setup が生成する主なキー（.env に保存）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用途）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト60秒）

注意:
- KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を用い、data/paper_trading.db に記録します（本番 DB と分離）。
- モニタリングは KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計の箇所があるため、運用時は注意してください（run_monitoring の docstring を参照）。

---

## 使い方（主要スクリプト / コマンド例）

- 設定ウィザード（.env の初期作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper Trading DB に記録します。
    - 起動時に data/stop_requested.flag が既に存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID が書かれる仕様（settings.pid_file_path）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を変更可能（秒、デフォルト 60）。
    - 停止フラグファイル（data/stop_requested.flag）を検出するとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も可）。

- AI（ニュース NLP / レジーム判定）
  - これらはモジュール関数として提供されています。OpenAI API キーが必要です。
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 直接の CLI ラッパーは含まれていません（実行はスケジューラや呼び出し元スクリプトから行う想定）。

---

## 運用上のファイル / フラグ
- data/kill.flag — Kill Switch による ExecutionEngine 停止シグナル（存在すれば停止）
- data/stop_requested.flag — 手動停止（run_* スクリプトはこれを見て終了する）
- data/execution.pid — ExecutionEngine の PID（起動スクリプトで使用）
- logs/ — ログファイル出力先（デフォルト）
- DuckDB / SQLite ファイルはデフォルトで data/ 下に作成されます

---

## ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン情報）
  - config.py — 環境変数 / 設定の読み取り・検証ロジック（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース記事を LLM でスコアリングして ai_scores に保存
    - regime_detector.py — マクロ + ETF MA 乖離で市場レジーム判定し DB に保存
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル初期化含む）
    - system_monitor.py — システム & データ鮮度監視
    - trade_monitor.py — （取引監視ロジック、リストに含まれるが詳細はコード参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（フラグファイル書き込み）
    - monitoring_engine.py — 監視コンポーネントを束ねるエンジン
    - alert_manager.py — アラート送信管理（実装に応じて LINE 等へ送信）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出・制限・丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ローテート）
    - process_priority.py — プロセス優先度・CPU affinity 設定ラッパー
  - monitoring/monitoring_db.py — 監視用 DB スキーマ定義 + MonitoringDB クラス

（注）上記はコードベースの抜粋に基づく主要構成です。実際のリポジトリでは追加ファイルやサブモジュールが存在する場合があります。

---

## 開発・運用上の注意
- .env は機密情報を含むため絶対に Git にコミットしないこと。
- KABUSYS_ENV を live に設定する前に validate_config によるチェックを必ず行ってください。
- OpenAI API を用いる機能は API 利用料が発生します。API キーの管理・制限に注意してください。
- run_monitoring は監視用 DB に本番 sqlite_path を使用し得る箇所があるため、テスト時は設定やパスに注意してください（paper_trading 用 DB と混同しない）。
- ログディレクトリの作成に失敗するとファイルハンドラが無効化され、コンソール出力のみになります（logging_setup の挙動）。

---

## 参考コマンドまとめ（例）
- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README に「依存パッケージの正確な一覧（requirements.txt）」や「運用手順（systemd / cron / Supervisor での起動例）」「DB スキーマの詳細」などを追加します。どの情報を優先して追記しますか？