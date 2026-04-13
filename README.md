# KabuSys — README (日本語)

概要
---
KabuSys は日本株の自動売買プラットフォームの核となるライブラリ群です。本リポジトリには以下の主要機能が含まれます：
- 発注・注文ライフサイクル管理（ExecutionEngine / OrderManager 等）
- モニタリング（System / Trade / Risk の監視、アラート、kill フラグ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチ（ファクター計算・特徴量評価）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア）
- 各種ツール（Paper Trading 検証レポート、Streamlit ダッシュボードなど）

主な設計方針
- DuckDB / SQLite を用いたデータ参照・永続化
- 環境変数 / .env による設定管理（自動ロード、プロジェクトルート検出）
- テストしやすい純粋関数設計（多くのロジックは DB 非依存の純粋関数）
- Paper Trading と Live 環境の分離（paper_trading 用 DB を用いる）

機能一覧
---
- Execution
  - 発注作成 → ブローカー送信 → 状態同期 / 再同期（Reconciler）
  - RiskManager によるポジション・資金制限
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働監視、データ鮮度チェック
  - TradeMonitor: 滞留注文／約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - AlertManager: LINE push による通知（クールダウン管理）
  - KillSwitch: kill.flag による ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（監視ダッシュボード）
- Portfolio
  - 候補選定、等金額/スコア加重配分、位置サイズ計算、セクター制限、レジーム乗数
- Research
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント → ai_scores 書き込み
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポート生成
  - streamlit_dashboard: 監視 DB を可視化

動作要件（主だった依存パッケージ）
---
- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード用)
- sqlite3（標準ライブラリ）
実運用ではこれらを requirements.txt にまとめて pip install してください。

セットアップ手順
---
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実運用用の追加パッケージやバージョン固定は requirements.txt を用意してください）

4. 環境変数設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（デフォルトで OS 環境変数優先）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須, kabu ステーション用)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (paper_trading 用: instant | partial | never | reject) — デフォルト: instant
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（解析用 DuckDB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PID_FILE_PATH（Execution 用 pid ファイル、デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（kill.flag、デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）

5. データディレクトリ作成
   - mkdir -p data

実行方法（主要なスクリプト）
---
- ExecutionEngine（売買実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。これにより本番 DB と完全分離されます。
  - 起動時にプロセス優先度を high に設定し、PID ファイル（Settings.pid_file_path）を書きます。

- Monitoring（システム監視・ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用します。Monitoring の DB 初期化は冪等で行われます。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開くため、MonitoringEngine を先に起動してデータを流す想定です。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 主要指標: 稼働率、注文成功率、送信率、P95 レイテンシ などを集計して PASS/FAIL 判定します。

- AI / リサーチの呼び出し（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum / calc_volatility / calc_value など（DuckDB 接続を渡して使用）

設定（主な設定項目の説明）
---
- KABUSYS_ENV
  - development / paper_trading / live
  - paper_trading: 実ブローカーアクセスをモックして data/paper_trading.db を使用
- PAPER_FILL_MODE
  - instant | partial | never | reject（Paper Trading の約定挙動）
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング秒数（1 以上の整数のみ有効。無効値はデフォルト 60 秒にフォールバック）
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
  - 各種データベースファイルのパス（デフォルトは data 以下）

運用メモ・注意点
---
- Monitoring は Settings.env に関係なく（常に）本番 sqlite_path を使用する設計です。Execution の paper_trading モードは paper_sqlite_path を使用して分離します。
- PID ファイル: Execution 側は起動時に pid を file に書きます。SystemMonitor は PID の存在と生存確認を行い、古い PID ファイルを検出したら削除してアラートを記録します。
- kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止指示を与えます。Execution 側は起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合フラグを消すことができます（Settings による）。
- OpenAI API 呼び出しは外部サービス依存のため失敗時はフェイルセーフ（スコア 0 など）で継続する実装になっていますが、API キーは必ず設定してください（AI 機能利用時）。

ディレクトリ構成（抜粋）
---
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env 自動ロードと Settings クラス
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py                   — ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py            — レジーム判定（MA200 + マクロセンチメント）

- monitoring/
  - monitoring_db.py              — SQLite テーブル定義・永続化ヘルパ
  - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py              — 注文滞留・約定異常監視
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — kill.flag 書き込みロジック
  - alert_manager.py              — LINE push 通知ラッパ
  - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py        — Streamlit ベースのダッシュボード
  - __init__.py

- portfolio/
  - portfolio_builder.py          — 候補選定・スコアソート
  - position_sizing.py            — 株数計算・単元丸め・集約キャップ
  - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py            — Momentum/Volatility/Value 計算（DuckDB）
  - feature_exploration.py        — 将来リターン・IC・統計サマリ
  - __init__.py

- execution/
  - order_manager.py              — 発注フローと状態遷移管理
  - reconciler.py                 — 起動時リコンシリエーション（ブローカーとの突合）
  - その他（broker_factory, order_repository, order_record 等）

- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成
  - __init__.py

- utils/
  - process_priority.py           — プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

よくある操作例
---
- 監視プロセスを 30 秒間隔で起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

貢献・ライセンス
---
- この README に記載の内容は実装ファイルのコメント・コードを基に要約しています。ライセンス情報や貢献ガイドラインはリポジトリルートに追加してください（本ファイルには含まれていません）。

補足
---
- ソース内の docstring や関数コメントに詳細設計・制約が豊富に書かれています。実装の深い部分（例えばポジション推定ロジックや DB マイグレーション方針、LLM へのリクエスト・リトライ仕様など）は該当ファイルを参照してください。
- 不明点があれば、どの機能の README を拡張したいかを教えてください。追加でコマンドサンプルや環境変数テンプレート（.env.example 形式）も作成できます。