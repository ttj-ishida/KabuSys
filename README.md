# KabuSys

日本株向け自動売買システムのコアライブラリ（プロトタイプ）。  
本リポジトリは取引実行、モニタリング、ポートフォリオ構築、リサーチ、AI を用いたニュース解析等の機能を含みます。

> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームの主要コンポーネント群を提供します。主な目的は以下です。

- ExecutionEngine による発注・注文管理・リスク管理
- Monitoring コンポーネントによる稼働・取引・リスク監視、アラート送信（LINE）
- Portfolio Construction（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- Research（ファクター計算、特徴量探索、IC 計算）
- AI モジュールによるニュースのセンチメント集計・市場レジーム判定（OpenAI API利用）
- Paper Trading（本番 DB と分離した模擬取引環境）および検証レポート生成ツール
- Streamlit を使った監視ダッシュボード

---

## 主な機能一覧

- Execution
  - 起動スクリプト: run_execution.py（KABUSYS_ENV に応じて paper_trading モードを分離）
  - BrokerClientFactory による本番/モックの切替
  - OrderManager / Reconciler による注文状態管理と再同期間合
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在・データ鮮度の監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視および kill.flag 出力
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - MonitoringEngine: 各 Monitor をまとめたポーリングループ
  - Streamlit ダッシュボード（read-only 表示）
- Portfolio
  - 候補選定（スコア順）、等金額 / スコア重み付け、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数
- Research
  - Momentum / Volatility / Value といったファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - news_nlp: raw_news を OpenAI に送って銘柄別センチメントを ai_scores に書込
  - regime_detector: ETF（1321）の MA 乖離＋マクロニュースから日次レジームを判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成

---

## セットアップ手順（開発 / ローカル実行向け）

前提: Python 3.9+（typing の一部機能に対応したバージョンを推奨）、pip が利用可能。

1. リポジトリをクローン / ワーキングディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   requirements.txt が無い場合は、主要依存を手動でインストールしてください（抜粋）:
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   ※ 実行環境に応じて追加の依存がある場合があります。

4. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。自動ロードは .git または pyproject.toml が存在するディレクトリをプロジェクトルートとして探索します。

   重要な環境変数（代表例）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - PAPER_FILL_MODE: paper trade の約定モード（instant|partial|never|reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: Paper 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

   例（.env）
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   PAPER_FILL_MODE=instant
   ```

5. データディレクトリを作成
   ```
   mkdir -p data
   ```

---

## 使い方（起動/実行例）

全てのスクリプトはパッケージモジュールとして実行できます（プロジェクトルートが PYTHONPATH に含まれることが前提）。

- Monitoring をポーリング実行（デフォルト 60 秒間隔。MONITOR_POLL_INTERVAL で上書き可）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL=<秒> を環境変数で与えることで間隔を変更できます。
  - Monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依存しません）。

- ExecutionEngine の起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは `data/paper_trading.db` に記録されます（本番 DB と完全に分離）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  ```
  日付範囲指定:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パス指定:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- Streamlit 監視ダッシュボード（読み取り専用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  起動時に読み取り専用で SQLite を開きます。DB が存在しない場合は MonitoringEngine を先に起動してください。

- ライブラリ API（モジュールとして利用）
  - AI: kabusys.ai.score_news(...) を呼んでニューススコアの集計と ai_scores への書き込みが可能
  - Regime: kabusys.ai.regime_detector.score_regime(...)
  - Research: kabusys.research.calc_momentum / calc_volatility / calc_value 等
  - Portfolio: kabusys.portfolio.* の純粋関数群（テスト容易）

---

## 注意事項 / 運用上のポイント

- 環境自動ロード:
  - config モジュールはプロジェクトルートを .git または pyproject.toml を基準に自動検出し、`.env` と `.env.local` をロードします。
  - OS 環境変数はデフォルトで保護され .env に上書きされません（ただし .env.local は override=True で上書き可能）。
  - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると発注のブローカークライアントがモックに切替わり、DB も paper_trading 用に分離されます（data/paper_trading.db）。

- プロセス優先度:
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼びます。psutil が必要で、OS によっては権限不足で設定できない場合があります（警告ログでスキップされます）。

- OpenAI API:
  - news_nlp / regime_detector は OpenAI（gpt-4o-mini）を利用するため OPENAI_API_KEY が必要です。
  - API 呼び出しは 429 やタイムアウト、5xx に対してリトライを実装していますが、運用時はレート管理を検討してください。

- DB マイグレーション:
  - init_monitoring_db() は安全に何度でも呼べる（冪等）よう実装されています。既存 DB に対して必要なカラムを追加する軽微なマイグレーションも行います。

- kill.flag:
  - KillSwitch は data/kill.flag ファイルに理由を書き込むことで ExecutionEngine に停止シグナルを与えます。ExecutionEngine 側はこのフラグの存在を検知してシャットダウンする設計を想定しています。

---

## ディレクトリ構成（主要ファイル）

(抜粋: src/kabusys 配下)

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / Settings 管理
  - run_monitoring.py               -- SystemMonitor ポーリング起動スクリプト
  - run_execution.py                -- ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  -- Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py              -- SQLite 永続化層（monitoring DB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py         -- Streamlit ダッシュボード（readonly）
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（broker_factory 等の実装を含む）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

上記はコードベースの主要なモジュール構成です。実際のリポジトリにはさらに細分化されたファイル（broker, order_repository, data.pipeline 等）が含まれます。

---

## 開発・拡張のヒント

- 多くの関数は副作用を最小化した純粋関数（特に portfolio / research）として書かれているため、単体テストが容易です。
- DuckDB を使う設計により SQL ベースでの大規模データ操作が高速に行えます。テーブルスキーマに注意してクエリを書いてください。
- AI 関連は外部 API に依存するため、ユニットテスト時は _call_openai_api をモックしてください（モジュール内で置換するためパッチ可能です）。
- 実運用ではログ収集・監視（プロメテウス / Grafana など）やバックアップ・DB ローテーションを検討してください。

---

必要であれば、README に以下を追加で記載できます:
- .env.example のテンプレート
- CI / テスト実行方法（pytest 等）
- 依存パッケージの正確な requirements.txt

追加の要望があれば教えてください。