# KabuSys

日本株自動売買システムのモジュール群 (抜粋)。  
この README は与えられたコードベースの使い方・構成を日本語でまとめたものです。

---

## プロジェクト概要
KabuSys は日本株向けの自動売買基盤を想定したモジュールセットです。  
主に以下の機能群を含みます。

- 注文発行・管理・再同期 (Execution)
- 監視（プロセス・資源・注文滞留・リスク）およびアラート送信 (Monitoring)
- ポートフォリオ構築・ポジションサイズ計算 (Portfolio)
- 研究用ファクター計算・特徴量解析 (Research)
- ニュースに基づく NLP スコアリング・レジーム判定（OpenAI API を利用）(AI)
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

設計方針としては、DB（SQLite / DuckDB）でデータを扱い、AI 関連は外部 API（OpenAI）を利用するがフェイルセーフ化している点、Paper Trading 環境は本番 DB と明確に分離される点などが特徴です。

---

## 主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントファクトリ（実運用 / モック切替）
  - OrderManager / OrderRepository / Reconciler による自動復旧
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/PID 監視
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・保有数上限監視
  - KillSwitch / AlertManager: 条件に応じて停止フラグ作成・LINE 通知
  - MonitoringEngine: 全モニタを束ねるポーリングループ
  - Streamlit ダッシュボード（data/monitoring.db を参照）
- Portfolio
  - 銘柄選定・重み計算・ポジションサイズ算出・セクター上限適用
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC 計算・統計サマリ
- AI
  - ニュース NLP による銘柄センチメント集計（OpenAI）
  - 市場レジーム判定（ma200 + マクロニュースセンチメント合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## システム要件 / 依存ライブラリ（主なもの）
- Python 3.9+（型ヒント使用）
- duckdb
- psutil
- requests
- openai (OpenAI SDK)
- streamlit（ダッシュボード起動時）
- sqlite3（標準ライブラリ）

（プロジェクトに requirements.txt は含まれていません。下記のようにインストールしてください）

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、プロジェクトルートに移動する。
2. 仮想環境を作成・有効化（例: python -m venv .venv）。
3. 必要パッケージをインストール。
   - 例: pip install duckdb psutil requests openai streamlit
4. 環境変数を設定（.env をプロジェクトルートに置くことで自動読み込みされます）。
   - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. data ディレクトリを作成（実行時に自動作成される場合もありますが手動作成しておくと良い）。
   - mkdir -p data

重要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants API トークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- OPENAI_API_KEY         : OpenAI API キー（AI 機能利用時に必須）
- KABUSYS_ENV            : 実行環境（development | paper_trading | live） (デフォルト: development)
- PAPER_FILL_MODE        : paper_trading 時の約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite (デフォルト: data/paper_trading.db)
- SQLITE_PATH            : 監視用 SQLite (デフォルト: data/monitoring.db)
- DUCKDB_PATH            : DuckDB ファイルパス (デフォルト: data/kabusys.duckdb)
- LOG_LEVEL              : ログレベル（DEBUG, INFO, ...）
- MONITOR_POLL_INTERVAL  : run_monitoring のポーリング間隔（秒、デフォルト 60）

.env の読み込み
- プロジェクトルートの .env を自動読み込みします（.env.local は .env を上書き）。
- OS 環境変数が優先されます。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## 主な使い方 / 実行方法

以下はプロジェクトルート（src の親）で実行することを想定しています。Python モジュールとして実行可能です。

1) 監視ループ（SystemMonitor ベース）起動
- コマンド:
  python -m kabusys.run_monitoring
- 説明:
  - 標準ではポーリング間隔 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒単位、1 以上）。
  - 監視は Settings.sqlite_path（data/monitoring.db がデフォルト）を使用します（KABUSYS_ENV に関わらず本番 sqlite_path を参照）。
  - 停止はプロジェクトルート/data/stop_requested.flag ファイルを作成することで検知して終了します。
  - プロセス優先度を "high" に設定しようとします（権限によっては警告）。

2) 実行エンジン（ExecutionEngine）起動
- コマンド:
  python -m kabusys.run_execution
- 説明:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と分離された PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - Engine は別スレッドで動作し、stop は data/stop_requested.flag を作成することで検知して停止します。
  - 起動時に kill.flag の存在を検出した場合、起動を行いません（安全のため）。

3) Streamlit ダッシュボード（監視データ閲覧）
- コマンド（例）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - data/monitoring.db を read-only で開いてダッシュボードを表示します。MonitoringEngine を先に起動してデータを書き出しておく必要があります。

4) Paper Trading 検証レポート生成
- コマンド例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --db PATH で SQLite DB を指定可能（指定がなければ環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を使用）。
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と PASS/FAIL 判定を標準出力に出力します。

5) AI 関連（ニュース NLP / レジーム判定）
- 実行はライブラリ API を通じて行います（例: kabusys.ai.score_news）。CLI のラッパーはありません。
- OpenAI API 利用時は OPENAI_API_KEY を設定してください。API エラーはリトライやフェイルセーフ（フォールバック値）で保護されています。

停止フラグ / kill flag
- 実行停止用のフラグ:
  - stop_requested.flag: run_monitoring / run_execution が監視している停止フラグ（通常プロジェクト data/stop_requested.flag）。
  - kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止指示を送る（Settings.kill_flag_path）。
- KillSwitch は条件（ドローダウン超過やポジション上限超過）で kill.flag を書き、AlertManager を通じて LINE に通知できます。

---

## 主要モジュールの簡単説明
- kabusys.config: 環境変数/.env の読み込みと Settings クラス
- kabusys.execution: 発注ロジック、OrderManager、Reconciler、ExecutionEngine（起動スクリプトあり）
- kabusys.monitoring: システム監視・トレード監視・リスク監視・アラート・モニタリングエンジン
- kabusys.portfolio: 銘柄選定・重み付け・ポジションサイズ計算
- kabusys.research: ファクター計算・特徴量探索
- kabusys.ai: news_nlp（記事から銘柄スコアを取得）・regime_detector（市場レジーム判定）
- kabusys.tools: 運用補助スクリプト（Paper Trading レポート等）
- kabusys.utils: process_priority（プロセス優先度 / CPU affinity）

---

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py                         — 環境変数読み込みと Settings
- run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py                — SQLite 永続化層（テーブル定義・MonitoringDB）
  - system_monitor.py               — システム状態・データ鮮度監視
  - trade_monitor.py                — 注文滞留・約定異常チェック
  - risk_monitor.py                 — ドローダウン・ポジション上限チェック
  - kill_switch.py                  — kill.flag 管理
  - alert_manager.py                — LINE 通知ラッパー
  - monitoring_engine.py            — 全モニタを束ねる実行ループ
  - streamlit_dashboard.py          — Streamlit ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - ...                             — ブローカー API / エンジン周りの実装
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py

data/
- monitoring.db (デフォルト SQLite)
- paper_trading.db (paper_trading 用)
- kabusys.duckdb (DuckDB データ)
- stop_requested.flag, kill.flag, execution.pid, etc.

---

## 開発・運用上の注意
- Monitoring の DB 初期化: init_monitoring_db() は冪等でテーブルを作成します。既存 DB のマイグレーション（カラム追加）も含まれます。
- Monitoring は常に settings.sqlite_path（監視 DB）を参照します。KABUSYS_ENV に関わらず監視 DB は production 相当のパスが使われます。Execution は KABUSYS_ENV に応じて paper_trading 用 DB を使う点に注意してください。
- process priority / cpu affinity の設定は権限によって失敗することがあります（警告ログが出力されます）。
- OpenAI を利用するモジュールは API キーが必須です。429 や 5xx 等はリトライ実装がありますが、レート制限等の管理は利用者側で行ってください。
- kill.flag の取り扱いや PID ファイルの操作は重要な運用ポイントです。手動で操作する場合は稼働中のプロセスに影響が出ないように注意してください。
- Paper Trading は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

---

## トラブルシューティング（よくある事項）
- .env が読み込まれない:
  - プロジェクトルートが .git や pyproject.toml で特定できない場合、自動ロードがスキップされます。手動で環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI 呼び出しでエラーが発生する:
  - OPENAI_API_KEY を確認。リトライやフォールバックにより処理が続行されるケースがあります。
- DB への書き込み権限エラー:
  - data ディレクトリとファイルのパーミッションを確認してください。
- 停止フラグが残っている:
  - data/kill.flag や data/stop_requested.flag を手動で削除すると起動可能になります（KillSwitch.clear() も利用可能）。

---

この README はコードベースの抜粋に基づく概要ドキュメントです。各モジュールや関数の詳細な仕様はソース内の docstring を参照してください。必要であれば、各コンポーネントごとの詳細 README を追加で作成します。