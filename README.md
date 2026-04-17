# KabuSys

KabuSys は日本株向けの自動売買・研究・監視フレームワークです。本リポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI を使ったニュース解析などのコンポーネントを含みます。

---

## プロジェクト概要

- 日次・リアルタイムの発注処理（ExecutionEngine）
- システム健全性や注文の異常検知を行う監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ファクター計算・特徴量探索（Research）
- OpenAI を利用したニュースセンチメント解析（AI）
- Paper Trading（本番 DB と分離された専用 DB）と検証レポート生成ツール
- Streamlit による監視ダッシュボード

設計方針の一部：
- DB（SQLite / DuckDB）によりデータ永続化
- 本番と Paper Trading を明確に分離
- 監視は環境に関係なく本番の monitoring DB を使用
- 自動環境変数読み込み（.env / .env.local）をサポート

---

## 主な機能一覧

- execution
  - 起動時の自動リコンサイル（Reconciler）
  - OrderManager / OrderRepository による注文管理と永続化
  - Paper Trading 用 MockBroker のサポート（KABUSYS_ENV=paper_trading）
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセスPID・データ鮮度監視
  - TradeMonitor：滞留注文／約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とログ記録
  - KillSwitch：条件により ExecutionEngine を停止するフラグの出力
  - AlertManager：LINE Push による通知（クールダウンあり）
  - Streamlit ダッシュボード（監視用）
- portfolio
  - 候補選定、等配分／スコア加重配分、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、資金制約対応）
- research
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- ai
  - news_nlp.score_news：ニュース記事を LLM でスコア化して ai_scores に格納
  - regime_detector.score_regime：ETF MA とマクロセンチメントを合成して市場レジーム判定
- tools
  - paper_verification_report：Paper Trading DB から検証レポートを生成

---

## セットアップ手順

前提：Python 3.9+（typing の一部にて 3.9 の構文が使われています）。pip を利用。

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 必要に応じて他の標準的なパッケージを追加してください
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは OS 環境変数より低優先、.env.local は上書き可）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（抜粋）：
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- PAPER_FILL_MODE: paper trading の約定振る舞い（instant|partial|never|reject、デフォルト "instant"）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH など（監視／停止制御に使用）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

例（.env の最小例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
MONITOR_POLL_INTERVAL=60
```

---

## 使い方（起動／コマンド）

- 実行（ExecutionEngine）
  - 本番／開発モードに応じて KABUSYS_ENV を設定してから起動します。
  - python -m kabusys.run_execution
  - 起動前に data/kill.flag をクリアしたい場合は Settings.kill_flag_clear_on_start を確認するか手動で削除してください。
  - Paper Trading（KABUSYS_ENV=paper_trading）の場合、発注は MockBroker を使い、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

- 監視（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を変更できます（デフォルト 60 秒）。
  - 監視は常に（KABUSYS_ENV に関係なく）Settings.sqlite_path（デフォルト data/monitoring.db）を使って記録します。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成して実行プロセスに知らせます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db` で SQLite ファイルパスを指定できます。
  - デフォルト DB: data/paper_trading.db

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取りモードで開きます。MonitoringEngine を先に起動してください。

- AI モジュール（プログラムから呼ぶ）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  → 書き込んだ銘柄数を返す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")  → 1 が返る（成功）

- Kill / Stop フラグ
  - ExecutionEngine の停止シグナルは data/kill.flag に理由を書き込むことで送れます（KillSwitch が書く）。
  - 監視側を優雅に止める際は data/stop_requested.flag を置きます（run_monitoring / run_execution が確認）。

---

## 実装上の注意点 / 運用メモ

- 監視 DB 初期化は冪等：init_monitoring_db() によりテーブル作成と簡単なマイグレーションを行います。
- Execution 起動時はプロセス優先度を "high" に設定する試みを行います（権限不足等で失敗することがあります）。
- run_execution は停止フラグ（data/stop_requested.flag）や data/execution.pid を使ってプロセス存在確認を行います。stale PID 検出時は削除しアラートを出します。
- Paper Trading と本番 DB は分離：`KABUSYS_ENV=paper_trading` の場合実行は paper_sqlite_path を使用します。
- OpenAI 呼び出しはリトライ・バックオフ実装あり。API キーは必ず設定してください（ai モジュールで ValueError が出ます）。
- streamlit ダッシュボードは DB を read-only で開くため、MonitoringEngine が DB をロックしている場合でも閲覧可能なことが多いです（ただし環境依存）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env の自動読み込みロジック含む）
  - run_monitoring.py          — SystemMonitor ポーリングスクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py           — ExecutionEngine 起動スクリプト（Paper Trading 分離）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py       — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル定義・MonitoringDB クラス
    - system_monitor.py        — CPU/メモリ/ディスク・PID・データ鮮度チェック
    - trade_monitor.py         — 注文滞留 / 約定異常チェック
    - risk_monitor.py          — ドローダウン / ポジション上限の監視
    - kill_switch.py           — kill.flag の書込みロジック
    - alert_manager.py         — LINE Push 通知のラッパー
    - monitoring_engine.py     — 各 monitor を束ねるエンジン
    - streamlit_dashboard.py   — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ...                      — 発注ロジックやブローカーファクトリ等（発注周り）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - data/                      — 実行時に使うファイル（デフォルトパス）
    - monitoring.db (default SQLITE_PATH)
    - kabusys.duckdb (default DUCKDB_PATH)
    - paper_trading.db (default PAPER_TRADING_SQLITE_PATH)
    - execution.pid
    - kill.flag
    - stop_requested.flag

（注）実際のリポジトリにはさらに細かな実装ファイルやモジュールが含まれます。上は主要な構成の抜粋です。

---

## トラブルシュート

- 環境変数が不足していると Settings のプロパティで ValueError が発生します。エラーメッセージを確認して .env を整備してください。
- OpenAI API 呼び出しで多量のリトライや失敗が出る場合は API キーやネットワークを確認してください。AI モジュールは失敗時にフェイルセーフでゼロやスキップを返す設計です。
- Monitor が PID の stale を検出した場合、PID ファイルを削除して再起動してください。監視は stale PID 検出時にリスクログを出力します。
- DB スキーマ変更があった場合、monitoring_db.py に簡単なマイグレーション処理が書かれていますが、手動でのバックアップを推奨します。

---

必要であれば README にコマンドの具体例（systemd ユニット例、Docker 起動例、CI 用スクリプト）や .env.example の完全テンプレートを追加できます。どの情報を追記しますか？