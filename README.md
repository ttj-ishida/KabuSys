# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ツール群をまとめた小さなプロジェクトです。本リポジトリには取引実行エンジン、監視サブシステム、ポートフォリオ構築ロジック、ファクター計算、LLM を用いたニュース NLP などが含まれます。

---

## プロジェクト概要

- 自動売買の ExecutionEngine：ブローカーとの発注・状態管理・リコンシリエーション（再起動後の同期）を担います。
- Monitoring：システム状態・注文状態・リスク（ドローダウンやポジション上限）を定期的にチェックしてログ保存、アラート送信、必要時に停止フラグを発行します。
- Portfolio（銘柄選定・配分・ポジションサイズ算出）：等配分 / スコア加重 / リスクベースのアルゴリズムを提供します。
- Research（ファクター計算・特徴量解析）：DuckDB 上の時系列データからモメンタム / ボラティリティ / バリュー等のファクターを計算します。
- AI（ニュース NLP / レジーム判定）：OpenAI を使ってニュースをセンチメント化し、銘柄別スコアや市場レジームを算出します。
- Tools：Paper Trading の検証レポート生成スクリプトなど運用支援ツールを提供します。

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（本番 / MockBroker）
  - 注文作成・送信・同期・キャンセル
  - 再起動時のリコンシリエーション
- Monitoring
  - CPU / メモリ / ディスク使用率、プロセス監視
  - 注文滞留（stale order）や約定異常価格の検出
  - ドローダウン監視・ポジション上限監視（KillSwitch による停止フラグ生成）
  - ログ永続化（SQLite）と簡易ダッシュボード（Streamlit）
  - LINE Push によるアラート（AlertManager）
- Portfolio
  - 候補選定（score 降順）
  - 等金額 / スコア加重 / リスクベース配分
  - セクターキャップ適用・レジーム乗数
- Research
  - DuckDB を用いたファクター計算（mom, vol, value 等）
  - 将来リターン、IC 計算、統計サマリ
- AI
  - ニュースを LLM でスコア化して ai_scores に格納
  - マクロニュース＋ETF MA200 による市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成（過去期間の稼働率、注文成功率、レイテンシ等）

---

## 必要条件（概略）

Python 3.9+（型ヒント等の記法に依存）

推奨ライブラリ（少なくとも以下が必要）:
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード使用時）
- sqlite3（標準ライブラリ）

実行環境により追加の OS 権限（プロセス優先度変更など）が必要になる場合があります。

（プロジェクトの requirements.txt がある場合はそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば pip install -r requirements.txt）
4. data ディレクトリを作成
   - mkdir -p data
5. 環境変数を設定（.env をプロジェクトルートに置くことを推奨）
   - 自動的に .env / .env.local が読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 例: .env に以下を記載（必要に応じて）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings にて必須チェックがあります（利用機能による）

6. DB 初期化
   - 監視 DB（monitoring.db）は run_monitoring / run_execution 実行時に自動でテーブルが作成されます（init_monitoring_db が実行されます）。
   - DuckDB ファイルは duckdb.connect() により自動作成されます。

---

## 使い方（よく使うコマンド例）

- 監視ループを起動（ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き（例: MONITOR_POLL_INTERVAL=30）
  - 停止方法: data/stop_requested.flag ファイルを作成するとループが検知して終了します（または Ctrl-C）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計です。

- ExecutionEngine（注文実行）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、デフォルトで data/paper_trading.db を用いる（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 停止方法: data/stop_requested.flag を作成するとエンジンが検出して安全停止します。
  - 実行時、data/execution.pid に PID を書き込む（実装上の pid_file）。

- Streamlit ダッシュボード（監視ビュー）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - あるいは streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db <path>

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。別パスを使う場合は --db オプションか環境変数 PAPER_TRADING_SQLITE_PATH を指定。

- AI / レジーム判定 / ニューススコア
  - ライブラリ関数をインポートして使います（例）
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは OpenAI API キー（OPENAI_API_KEY）を参照します。引数でキーを明示的に渡すことも可能。

- 開発／テスト用の一回実行（MonitoringEngine）
  - import として MonitoringEngine を組み合わせ、run_once() を呼んで単発チェックを行えます（テスト用インターフェース）。

---

## 主要ファイル・挙動の補足

- .env 読み込み
  - config.Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し .env / .env.local を自動読込します。OS 環境変数が優先され、.env.local は上書き可能です。
  - 自動読込を無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading モード
  - KABUSYS_ENV=paper_trading のとき、実行エンジンは MockBrokerClient を使用して発注をローカル DB (PAPER_TRADING_SQLITE_PATH) に記録します。本番 DB を汚さない分離が行われます。

- 停止フラグと Kill Switch
  - data/stop_requested.flag: run_monitoring / run_execution が定期的に存在をチェックし、見つかれば安全に終了します（運用停止用）。
  - data/kill.flag: Monitoring の KillSwitch が重大リスク（ドローダウン超過など）を検知した際に書き込む。存在すると ExecutionEngine 起動時に検出して起動を行わない/停止をかける運用となっています。
  - PID ファイル: data/execution.pid（デフォルト）にプロセス ID を書き込み、SystemMonitor が生存チェックを行います。stale PID の検出時にはリスクイベントがログ化されます。

- ログ出力レベル
  - LOG_LEVEL 環境変数で検査されます（DEBUG/INFO/...）。run_* スクリプトは basicConfig(level=logging.INFO) を使用しています。

---

## ディレクトリ構成（抜粋と説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数 / Settings 管理（.env 読込、検証、パス等）
  - run_monitoring.py — SystemMonitor のポーリングループ開始スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 分離対応）
  - /monitoring
    - monitoring_db.py — SQLite に対する永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定価格異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込ロジック
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor の統合ランナー
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - /execution
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, ... — 発注・同期・復旧ロジック（一部実装あり）
  - /portfolio
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・丸め・制約処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - /research
    - factor_research.py — モメンタム/ボラティリティ/バリューの計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - /ai
    - news_nlp.py — ニュースを LLM で銘柄別にスコア化して ai_scores に書き込む
    - regime_detector.py — マクロセンチメント + ETF MA200 でレジーム判定
  - /utils
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ
  - /tools
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

（上記は現行コードベースの主要ファイルを抜粋したものです）

---

## 運用上の注意 / ベストプラクティス

- 環境分離
  - paper_trading モードを利用することで本番 DB に影響を与えずに検証できます。デフォルトの PAPER_TRADING_SQLITE_PATH を適切に切り替えてください。
- シークレット管理
  - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY などは .env やシステム環境変数で管理してください。リポジトリに含めないでください。
- フラグファイル
  - stop_requested.flag や kill.flag の存在は運用側のインタラクションに依存します。自動化システムからはこれらファイルを作成／削除することでプロセス制御を行えます。
- 権限
  - プロセス優先度変更（set_process_priority）は OS やユーザー権限により失敗する場合があります（警告ログにより無害にフォールバックします）。
- テスト
  - OpenAI 呼び出し等は外部依存があるため、ユニットテスト時は該当関数をモックする想定です（コード中にも patch を想定した記述あり）。

---

## よくあるコマンドまとめ

- 監視開始:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- エンジン開始:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要に応じて README を拡張して、開発用のテスト手順、CI 設定、より詳細な環境変数一覧（例: 各パラメータの上限/下限）、およびパッケージング手順を追加できます。追加で載せたい情報があれば教えてください。