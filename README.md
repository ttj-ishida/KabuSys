# KabuSys

日本株向け自動売買／リサーチ基盤のサブコンポーネント群。  
このリポジトリは、注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュース解析などのユーティリティを含みます。

---

## プロジェクト概要

- 自動売買の実行制御（ExecutionEngine / OrderManager / Reconciler）
- システム稼働監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- ポートフォリオ選定・配分・ポジションサイズ計算（portfolio パッケージ）
- リサーチ用ファクター計算・特徴量解析（research パッケージ）
- ニュースセンチメント解析・市場レジーム判定（AI モジュール：news_nlp / regime_detector）
- Paper Trading 用の検証・集計ツール（tools.paper_verification_report）
- Streamlit を使った監視ダッシュボード

主要設計方針の例:
- DuckDB / SQLite をデータ層に使用（prices_daily 等は DuckDB）
- 本番と Paper Trading を明確に分離（PAPER_TRADING_SQLITE_PATH）
- 外部 API（OpenAI 等）はフェイルセーフなリトライやフォールバックを実装
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない設計の箇所あり）

---

## 主な機能一覧

- SystemMonitor: CPU/メモリ/ディスク/プロセス PID/データ鮮度を監視して SQLite に記録
- TradeMonitor: 滞留注文や約定価格の異常を検出してリスクログへ記録
- RiskMonitor: ドローダウン・ポジション数上限を監視し、必要時にリスクイベントをログ
- KillSwitch: リスク条件で data/kill.flag を書き込み、ExecutionEngine の停止をトリガ
- AlertManager: LINE Messaging API への通知（クールダウン管理あり）
- MonitoringEngine: 上記モニタをまとめてポーリング・アラート発行
- ExecutionEngine 起動スクリプト（run_execution.py）: ブローカークライアント選択、OrderManager / RiskManager 等を組み立てて実行
- run_monitoring.py: SystemMonitor のポーリングループを起動
- portfolio モジュール: 候補選定・重み計算・ポジションサイズ計算・セクター上限適用
- research モジュール: モメンタム / ボラティリティ / バリュー等のファクター計算、IC や統計サマリ
- AI モジュール: raw_news を LLM でスコアリングして ai_scores へ保存（news_nlp）、市場レジーム算出（regime_detector）
- tools.paper_verification_report: Paper Trading DB から検証レポートを生成
- streamlit_dashboard: 監視 DB を可視化する Streamlit アプリ

---

## 必要環境 / 依存パッケージ

推奨: Python 3.9+（ソースは型ヒントで modern Python を想定）

主要依存（requirements.txt が無い場合は手動でインストール）:
- duckdb
- psutil
- requests
- openai
- streamlit

例:
pip install duckdb psutil requests openai streamlit

※ SQLite は標準ライブラリで利用可能です。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt  （存在する場合）
   - または個別に: pip install duckdb psutil requests openai streamlit
4. .env ファイルをプロジェクトルート（.git または pyproject.toml があるディレクトリ）に配置
   - 自動で .env / .env.local が読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. data ディレクトリを作成（初期 DB 等をここに置く想定）
   - mkdir -p data

必須・推奨の環境変数（Settings 内参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- PAPER_TRADING_SQLITE_PATH — (paper_trading 時) SQLite DB パス（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の fill 挙動（instant/partial/never/reject）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（空なら送られない）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

.env の例（.env.example を参考に作成してください）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
PAPER_FILL_MODE=instant

---

## 使い方（実行例）

注意: ソースは src/kabusys 以下にあるため、プロジェクトルートからモジュールとして実行するか、PYTHONPATH を設定して実行してください。以下はプロジェクトルートからの実行を想定します。

1. SystemMonitor（監視）を起動
   - デフォルトのポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL で変更可能（秒）。
   - 実行:
     - python -m kabusys.run_monitoring
   - 挙動:
     - Settings に従って監視用 SQLite（settings.sqlite_path）および DuckDB に接続
     - data/stop_requested.flag が存在するとループを終了します
     - プロセス優先度を "high" に設定（可能な場合）

2. ExecutionEngine（注文実行）を起動
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用の DB に記録（本番 DB とは分離）
   - 実行:
     - python -m kabusys.run_execution
   - 挙動:
     - settings.is_paper の場合は settings.paper_sqlite_path を使用
     - 起動時に data/stop_requested.flag を検出すると起動せず終了
     - 実行中に data/stop_requested.flag が作成されると安全に停止する

3. Streamlit ダッシュボード
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 読み取り専用で monitoring DB を開き、Overview / Positions / Orders / System を表示

4. Paper Trading 検証レポート生成
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連（ニューススコア／レジーム判定）
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、api_key を渡して呼び出します。
   - 実行時は OPENAI_API_KEY を環境変数か関数引数で渡す必要があります。

6. 強制停止・停止フラグ
   - ExecutionEngine の停止トリガ:
     - KillSwitch が条件を満たすと data/kill.flag に理由を書き込みます（Execution 側は kill.flag を見て停止します）
   - 手動でプロセスを止めたい場合:
     - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します
   - PID ファイル:
     - Execution は data/execution.pid を使用（Settings.pid_file_path）

---

## 動作のポイント・注意事項

- run_monitoring は監視ログ用 SQLite（settings.sqlite_path）を利用します。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視は常に本番対象の想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用の SQLite を使い、本番 DB と分離します。
- .env 自動読み込み:
  - .env（プロジェクトルート）を自動で読み込みます。既存の OS 環境変数は保護され .env.local は上書き可能（ただし OS 環境変数は保護されます）。
  - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- AI（OpenAI）呼び出しはリトライ・バックオフ・レスポンス検証を行い、失敗時は安全なフォールバック（スコア 0.0 など）で継続する設計です。
- process_priority の設定: 起動時に set_process_priority("high") を試みますが、権限不足／未対応 OS の場合は警告を出してスキップします。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込み（Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - data/ (実行時に使う想定: monitoring.db, paper_trading.db, kabusys.duckdb など)
  - monitoring/
    - monitoring_db.py — SQLite のテーブル初期化と簡易永続化 API（MonitoringDB）
    - system_monitor.py — システム／データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注ロジックの外向け API
    - reconciler.py — 起動時の同期・リコンシリエーション
    - その他（broker_factory 等、ブローカー関連モジュール）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等の計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM でスコアリングして ai_scores に書き込み
    - regime_detector.py — ETF MA とマクロニュースを合成してレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

---

## 追加情報 / 運用メモ

- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、既存 DB にカラム追加（peak_value, latency_ms）を行います。
- エラーハンドリング: 各コンポーネントは外部 API エラーや DB エラー時にフェイルセーフ（警告ログ・部分スキップ）する設計です。
- テスト: 各モジュールは純粋関数（portfolio 等）や外部呼び出しを抽象化している箇所があり、単体テストがしやすい構成になっています。

---

必要であれば、README に含める具体的な .env.example、requirements.txt の推奨内容、起動スクリプトの systemd / supervisor 用ユニット例なども作成します。どの情報を追加しますか？