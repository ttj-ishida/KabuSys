# KabuSys — README

日本株自動売買システムのコードベースの説明書です。  
この README はプロジェクトの概要、主な機能、セットアップ手順、よく使う起動方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な役割は次の通りです。

- シグナル → 注文の発行・管理（ExecutionEngine / OrderManager）
- 発注・約定の監視とアラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、リスク調整）
- 研究用ファクター計算・特徴量探索（DuckDB を利用）
- AI を用いたニュースセンチメント評価・市場レジーム判定（OpenAI API）
- Paper Trading（検証用に本番 DB と分離された専用 DB で動作）
- 各種ツール（検証レポート生成、Streamlit ダッシュボード等）

設計方針のポイント：
- DuckDB / SQLite を用いてデータの永続化と分析を分離
- 本番・PaperTrading のデータ分離
- API 呼び出しのリトライ・フェイルセーフ（LLM 呼び出し等）
- ルックアヘッドバイアスを避ける実装（日時の参照制御）

---

## 機能一覧（抜粋）

- Execution
  - OrderManager / ExecutionEngine：注文作成、送信、ステータス同期、リスク管理
  - Reconciler：再起動時の注文・ポジション照合（自動復旧）
  - BrokerClientFactory：環境に応じたブローカークライアント生成（paper_trading では Mock）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度監視
  - TradeMonitor：滞留注文、約定価格異常の検出
  - RiskMonitor：ドローダウン、ポジション上限監視とダッシュボード更新
  - KillSwitch：重大アラートで ExecutionEngine 停止フラグ（data/kill.flag）を書込
  - AlertManager：LINE Push による通知（クールダウン制御）
  - Streamlit ダッシュボード（監視可視化）
- Portfolio（純粋関数群）
  - 候補選定（select_candidates）
  - 重み計算（等配分／スコア加重）
  - ポジションサイズ算出（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン算出、IC（スピアマン）計算、統計サマリ
- AI
  - news_nlp.score_news：raw_news をまとめて OpenAI へ投げ、銘柄別センチメントを ai_scores へ書込
  - regime_detector.score_regime：ETF MA とマクロニュース LLM スコアを合成して market_regime を更新
- ツール
  - paper_verification_report：Paper Trading DB を解析して合否判定レポートを出力
  - streamlit_dashboard：監視 DB の可視化

---

## 事前準備 / 依存関係

推奨 Python バージョン：3.10〜3.12（型注釈に Path | None 等を使用）  
主な依存パッケージ（requirements 等にまとめてください）:

- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- その他（ローカルでのテストに必要なパッケージがあれば追加）

例（pip）:
pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

Settings クラスにより .env/.env.local または OS 環境変数から読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数とデフォルト：
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、paper 用専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知のため
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB デフォルト）
- PID_FILE_PATH: data/execution.pid（ExecutionEngine PID 保存場所）
- KILL_FLAG_PATH: data/kill.flag（KillSwitch 用フラグ）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

例（.env）:
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
MONITOR_POLL_INTERVAL=60

---

## セットアップ手順（ローカルで動かす場合）

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または個別に: pip install duckdb psutil requests openai streamlit
4. .env をプロジェクトルートに作成（.env.example を参照）
5. DuckDB / SQLite のデータディレクトリを作成
   - mkdir -p data
6. 必要に応じて初期データをロード（prices_daily, raw_financials, raw_news 等）  
   （データロードの実装はここに含まれていません。DuckDB に適切なテーブルを用意してください。）

---

## 使い方（主な起動方法）

注意: 各プロセスは Settings の KABUSYS_ENV を参照して挙動（paper_trading 本番分離等）を切り替えます。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 実行時に Settings.is_paper==True（KABUSYS_ENV=paper_trading）であれば MockBrokerClient を使い、記録先は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）になります。

- Monitoring（ポーリング監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring DB（Settings.sqlite_path）に書き込みます。init_monitoring_db は冪等（マイグレーション含む）なので初回起動でテーブル作成されます。

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を計算し PASS/FAIL を判定します（閾値はスクリプト内定義）。

- Streamlit 監視ダッシュボードを起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは（モジュールとして） python -m kabusys.monitoring.streamlit_dashboard --db data/monitoring.db

- AI 関連（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — raw_news を評価して ai_scores に書込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime を更新

---

## 重要な運用上の注意

- Paper Trading と本番は SQLite により物理的に分離されています（paper_trading 用 DB は別ファイル）。運用時に誤って本番 DB を上書きしないよう .env を確認してください。
- OpenAI 呼び出しには API キーが必須。未設定時は ValueError が発生します（AI 機能のみ）。
- run_monitoring は監視ログを書き続けます。kill.flag の存在確認や PID 管理を行っています（PID ファイルは Settings.pid_file_path）。
- Monitoring の init は既存 DB スキーマに対して安全なマイグレーション（カラム追加）を行いますが、DB のバックアップを取ってから運用環境で実行することを推奨します。
- set_process_priority/set_cpu_affinity は OS 権限によって失敗することがあります（警告ログが出ますが継続動作します）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — Settings クラス（環境変数 / .env の読み込みロジック）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- order_manager.py — Order 管理ロジック（作成・送信・同期）
- reconciler.py — 再起動時リコンシリエーション（注文・ポジション照合）
- ...（broker_factory, order_repository 等、実装の残りがある想定）

src/kabusys/monitoring/
- monitoring_db.py — SQLite に対する永続化レイヤ（テーブル作成 / CRUD）
- system_monitor.py — システム・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag 管理
- alert_manager.py — LINE 通知
- monitoring_engine.py — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py — Streamlit ベースの監視 UI

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定、重み計算
- position_sizing.py — 株数算出・スケール調整
- risk_adjustment.py — セクターキャップ、レジーム乗数

src/kabusys/research/
- factor_research.py — momentum/value/volatility ファクター計算（DuckDB）
- feature_exploration.py — 将来リターン、IC、統計サマリ
- __init__.py — 研究用 API のエクスポート

src/kabusys/ai/
- news_nlp.py — ニュースの LLM センチメント処理（OpenAI）
- regime_detector.py — マーケットレジーム判定（MA + LLM）
- __init__.py — ai API のエクスポート

src/kabusys/tools/
- paper_verification_report.py — Paper Trading の検証レポート生成

src/kabusys/utils/
- process_priority.py — プロセス優先度、CPU affinity 設定ユーティリティ

data/
- data/kabusys.duckdb — DuckDB（デフォルトパス）
- data/monitoring.db — 監視用 SQLite（デフォルトパス）
- data/paper_trading.db — Paper Trading 用 SQLite（デフォルトパス）
- data/execution.pid — ExecutionEngine PID（デフォルト）
- data/kill.flag — Kill Switch フラグファイル（デフォルト）

---

## 追加情報 / トラブルシュート

- MONITOR_POLL_INTERVAL が 0 か負の値の場合は無効扱いされ、デフォルト 60 秒が使われます。
- .env のパースはシェルの export やクォート、コメント形式（#）に対応するよう独自実装されています。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- OpenAI など外部サービスの呼び出しはリトライロジックを持ちますが、API クォータやネットワーク状態によってはスキップされます。ログ（INFO/WARNING/ERROR）を確認してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くことができます（URI に ?mode=ro を付与）。MonitoringEngine を先に走らせると実データが表示されます。

---

## 開発者向けメモ

- 研究モジュール／ポートフォリオモジュールは純粋関数（副作用なし）として設計されているため、ユニットテストが書きやすいです。
- AI モジュールの API 呼び出し箇所はラップされており、テスト時にはモック化（patch）して振る舞いを差し替えられます（news_nlp._call_openai_api 等）。
- MonitoringDB.init_monitoring_db は既存 DB のカラム追加（マイグレーション）を行います。スキーマ変更時は互換性に注意してください。

---

必要であれば、README に「導入事例」「CI 設定」「ユニットテストの実行方法」や「設定ファイルのテンプレート（.env.example）」を追加できます。どの情報を追加したいか教えてください。