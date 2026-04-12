# KabuSys — README

日本株向け自動売買基盤のサンプル実装（ライブラリ + 実行スクリプト群）。

このリポジトリは、発注実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などの主要コンポーネントを含みます。設計は本番運用／Paper Trading（検証）を想定しており、SQLite / DuckDB を用いたローカル永続化や外部 API（kabuステーション、J-Quants、OpenAI、LINE）連携の抽象化がされています。

主な設計方針：
- 環境変数 / .env による設定管理（自動読み込み、無効化可能）
- Paper Trading は本番 DB と分離（別 SQLite）
- モジュールは副作用を避ける設計（純粋関数 / 明確な side-effect 層）
- OpenAI 呼び出しはリトライ・バリデーションありでフェイルセーフ

---

## 機能一覧

- 実行（Execution）関連
  - 注文作成・送信・状態同期（OrderManager / Reconciler）
  - ブローカー抽象化（実ブローカー / MockBroker などの切替）
  - リスク管理（RiskManager 等）

- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク/プロセス）監視（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - kill.flag による停止シグナル（KillSwitch）
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード（監視 UI）

- ポートフォリオ構築
  - 候補抽出・等比率/スコア加重の重み計算
  - セクターキャップ適用、レジーム乗数
  - 位置サイズ計算（単元株丸め、aggregate cap）

- リサーチ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン・IC 計算・統計サマリー

- AI（LLM）連携
  - ニュースを用いた銘柄ごとのセンチメント付与（OpenAI）
  - マクロニュース + ETF MA200 乖離による市場レジーム判定
  - API 呼び出しに対するリトライ、レスポンスバリデーション、部分失敗耐性

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: git clone ... && cd <repo>

2. Python 環境（推奨: 3.10+）を用意し、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必須パッケージ例（プロジェクトに requirements.txt がある場合はそれを使用してください）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

4. 環境変数を設定（.env ファイル推奨）
   - プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な環境変数（主要）
   - 必須（使用する機能により必須となるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（研究機能で必要）
     - KABU_API_PASSWORD — kabuステーション API パスワード（実取引で必要）
   - OpenAI:
     - OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）を使う場合に必要
   - 通知（LINE）:
     - LINE_CHANNEL_ACCESS_TOKEN（任意。未指定なら通知は送られずログのみ）
     - LINE_USER_ID
   - その他の設定（例、オプション、デフォルトあり）:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper トレード時の SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE（instant|partial|never|reject）など

6. データディレクトリを作成
   - mkdir -p data

注意: .env のパースはシェルスタイルをサポート（コメントやクォート処理あり）。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）の起動
  - Paper Trading（モックブローカー、DB 分離）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - Live（実ブローカー）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 補足:
    - run_execution は起動時にプロセス優先度を上げ、適切な SQLite / DuckDB に接続します。
    - Paper Trading の場合、PAPER_TRADING_SQLITE_PATH の DB に記録され本番 DB と分離されます。

- 監視ループ（Monitoring）の起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）。1 以上の整数。デフォルト 60。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用します（意図的）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で開き、positions/trade_logs/system_status/dashboard を表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能の呼び出し（ライブラリ API）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- Kill Switch / フラグファイル
  - KillSwitch は kill.flag（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側は起動時に KILL_FLAG_CLEAR_ON_START を 1 にすると自動で消去できます（設定による）。

---

## 設定（主な環境変数まとめ）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要時）
- KABU_API_PASSWORD: kabu API パスワード（実運用時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（Paper 用）
- DUCKDB_PATH: data/kabusys.duckdb
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング秒（default 60）
- PAPER_FILL_MODE: instant|partial|never|reject（Paper Broker の約定振る舞い）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

例 (.env):
```
KABUSYS_ENV=paper_trading
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
OPENAI_API_KEY=sk-xxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / .env 自動読み込みと Settings クラス（アプリ設定）
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（エントリポイント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースの LLM センチメントスコアリングロジック
    - regime_detector.py — 市場レジーム判定ロジック（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・CRUD ヘルパ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE への通知（プッシュ）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数計算・単元丸め・aggregate cap
  - research/
    - factor_research.py — モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - execution/
    - order_manager.py — 注文生成・送信のオーケストレーション
    - reconciler.py — 起動時の注文・ポジションの再同期（リコンシリエーション）
    - （その他：broker_factory, order_repository, order_record などが想定）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足: 上記は主要ファイルの抜粋です。DuckDB 経由のデータ処理や Execution/Repository 層の詳細は該当モジュールの docstring を参照してください。

---

## 運用上の注意 / ベストプラクティス

- 本番（live）で稼働する際は環境変数を OS 側（systemd など）で安全に管理してください。シークレットは .env に直書きしない運用が望ましい。
- Paper Trading は本番 DB と完全に分離する設計です。検証時は KABUSYS_ENV=paper_trading を利用してください。
- OpenAI 呼び出しはコストとレート制限に注意。news_nlp はバッチ化・トリム・リトライをしているが、API キーと利用量の管理を行ってください。
- Monitoring は定期的にダッシュボードや risk_logs を確認し、kill.flag が書き出されていないか監視してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブル/カラム追加や簡易マイグレーションを行います。複雑なスキーマ変更は別途管理してください。

---

## 参考：よく使うコマンドまとめ

- 実行エンジン（Paper）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視ループ
  - python -m kabusys.run_monitoring
  - 短い間隔で試す: export MONITOR_POLL_INTERVAL=10

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、各コンポーネント（ExecutionEngine、OrderRepository、MockBroker の実装、DB スキーマ詳細）について別途詳しい README（または設計書）を作成します。どの部分を優先してドキュメント化しましょうか？