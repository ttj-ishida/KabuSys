# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリには、取引エンジン起動・監視・ポートフォリオ構築・研究用ファクター計算・ニュース NLP（OpenAI）連携などの主要機能が実装されています。

以下はこのコードベースの概要、機能、セットアップ・実行方法、ディレクトリ構成の説明です。

## プロジェクト概要
- 自動売買エンジン（ExecutionEngine）とその補助コンポーネント（OrderManager、RiskManager、Reconciler 等）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）とアラート通知（LINE）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制約等）
- 研究用モジュール（ファクター計算、IC計算、特徴量探索）
- AI モジュール（ニュースセンチメント：OpenAI を呼ぶ news_nlp、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 永続化に SQLite（監視ログ）と DuckDB（市場データ・研究用）を使用

設計上のポイント：
- Paper Trading（仮想取引）モードは本番 DB と明確に分離（PAPER_TRADING_SQLITE_PATH を使用）。
- .env 自動読み込み機能（プロジェクトルート検出）を備え、OS 環境変数を保護。
- LLM（OpenAI）呼び出しはリトライやレスポンスバリデーションを行いフェイルセーフ化。

---

## 主な機能一覧
- Execution（発注・オーダー状態管理、リスク管理、再突合せ）
  - Broker クライアントの抽象化（本番/モック切替）
  - OrderManager: オーダー作成/キャンセル/同期
  - Reconciler: 起動時の自動リコンシリエーション
- Monitoring（監視）
  - SystemMonitor: CPU/MEM/DISK、プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch / AlertManager: 停止フラグ生成、LINE 通知
  - Monitoring DB: system_status / trade_logs / risk_logs / positions / dashboard の永続化
- Portfolio construction
  - 候補選定、等重・スコア重み、リスク制約（セクターキャップ）、ポジションサイズ算出（単元丸め等）
- Research
  - calc_momentum / calc_volatility / calc_value：DuckDB を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary 等の解析ユーティリティ
- AI 関連
  - news_nlp.score_news: raw_news を集約して OpenAI でセンチメント評価 -> ai_scores へ書込
  - regime_detector.score_regime: ETF MA200 乖離 + マクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（期間指定可）
  - monitoring.streamlit_dashboard: Streamlit を使った監視ダッシュボード

---

## セットアップ手順（開発 / ローカル実行向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ例:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （requirements.txt がある場合は `pip install -r requirements.txt`）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - .env または環境変数で設定します。自動ロードはデフォルトで有効（プロジェクトルートに .env または pyproject.toml/.git がある場合）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用
   - KABU_API_PASSWORD — kabuステーション API 用
   - OPENAI_API_KEY — news_nlp / regime_detector を使う場合
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を有効にする場合

7. （任意）.env の例（.env.example を参照して作成）
   - KABUSYS_ENV=development
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - OPENAI_API_KEY=...
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...

---

## 使い方（実行例）
※ パッケージ化されていない開発リポジトリ内で実行する場合は、`PYTHONPATH=src` を通すかワークディレクトリを適切に設定してください。簡便にはプロジェクトルートで `python -m kabusys.run_monitoring` のように実行できます。

1. 監視ループを起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 動作:
     - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更可能（デフォルト 60 秒）
     - 常に本番用 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録
     - 停止要求: プロジェクトの data/stop_requested.flag ファイルが存在するとループ終了

2. ExecutionEngine を起動（注文実行）
   - 本番モード:
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution
   - Paper Trading（モックブローカー、DB分離）:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - Paper Trading 時は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録され、本番 DB と完全に分離されます。
   - 停止/終了:
     - 停止フラグ: data/stop_requested.flag を作成すると起動中の run_execution/run_monitoring が検知して終了します。
     - ExecutionEngine 用 PID ファイル: data/execution.pid を利用（SystemMonitor がプロセス生存確認に使用）

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db data/paper_trading.db
   - 出力: 標準出力に PASS/FAIL 判定と各種指標（稼働率・注文成功率・P95 レイテンシ等）

4. Streamlit ダッシュボード（監視 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、Positions / Orders / System / Overview を表示

5. AI モジュール（ニューススコア / レジーム判定）
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date, API key を与えてプログラムから呼び出します。
   - 簡易的には各関数を呼ぶスクリプトを作るか、REPL から利用してください。
   - 必須: OPENAI_API_KEY（または api_key 引数）

6. Kill / KillFlag
   - KillSwitch は条件を満たすと data/kill.flag に理由を出力し ExecutionEngine に停止指示を与えます。
   - 手動でクリアする場合:
     - rm data/kill.flag
     - KillSwitch.clear() はプログラム上でのクリーンアップ用に存在

---

## 主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API キー（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（未設定時は送信をスキップ）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB データベース（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE: paper_trading の注文約定振る舞い（instant | partial | never | reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロード無効化

.env の自動ロード順序:
- OS 環境変数（上書き不可） >
- .env.local（.env を上書き） >
- .env

プロジェクトルートは .git または pyproject.toml を起点に検出されます。検出できない場合は自動ロードをスキップします。

---

## ディレクトリ構成（主要ファイルと簡単な説明）
（ソースは src/kabusys 配下）

- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — Settings クラス（環境変数読み込み・検証）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（テーブル作成・CRUD ラッパ）
    - system_monitor.py — CPU/MEM/DISK・プロセス・データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — 停止フラグ書き込みロジック
    - alert_manager.py — LINE 通知実装
    - monitoring_engine.py — 各 Monitor をまとめるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベースのダッシュボード
  - execution/
    - order_manager.py — オーダー外向 API（作成・キャンセル・同期）
    - reconciler.py — 起動時リコンシリエーション
    - (その他: broker_factory, execution_engine, order_repository 等、実行系のコンポーネント)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value の計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
    - __init__.py — 研究用ユーティリティ公開
  - ai/
    - news_nlp.py — raw_news を OpenAI に送り銘柄別センチメントを取得
    - regime_detector.py — マクロ+MA200 を使ったレジーム判定
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLite) — 監視ログ
    - kabusys.duckdb (DuckDB) — 市場データ / 研究データ
    - paper_trading.db — Paper Trading 用 SQLite（paper_trading モード時）
    - execution.pid, kill.flag, stop_requested.flag — 制御ファイル

---

## 運用上の注意
- Paper Trading モードは本番 DB と分離されていますが、設定ミスを避けるため起動前に環境変数とパスを確認してください。
- OpenAI の API 呼び出しはコストが発生します。news_nlp/regime_detector の運用は API キーとコスト管理に注意してください。
- Monitoring はデフォルトで本番 sqlite_path を使用します（KABUSYS_ENV に依らず監視 DB は本番 path を参照する設計の箇所があります）。運用前に監視 DB のパスと権限を確認してください。
- 長時間運用する場合はプロセスマネージャ（systemd 等）で再起動やログ管理を行うことを推奨します。

---

## トラブルシューティング（短記）
- .env が読み込まれない：
  - プロジェクトルートが正しく検出されているか（.git か pyproject.toml があるか）を確認。自動ロードを無効にしているかも確認（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- モジュールが見つからない（python -m 実行時）：
  - プロジェクトルートで実行しているか、PYTHONPATH に src を含めているか確認。
- OpenAI 呼び出しで失敗する：
  - OPENAI_API_KEY を設定。ネットワーク制限・レート制限の可能性あり。retry ログを参照。
- 監視ループを即時停止したい：
  - data/stop_requested.flag を作成（touch data/stop_requested.flag）。実行中の run_monitoring / run_execution は次のポーリング/ループで検知して終了します。

---

もし README のサンプル .env ファイル、requirements.txt、あるいは systemd のユニットファイルの例などが必要でしたら、用途に合わせて追記テンプレートを作成します。どのドキュメントが欲しいか教えてください。