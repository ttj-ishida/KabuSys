# KabuSys — README

このリポジトリは日本株向け自動売買システム「KabuSys」の一部実装です。  
以下はコードベース（src/kabusys 配下）を前提とした簡易ドキュメントです。

注意: 実行には外部サービス（kabuステーション API、J-Quants、OpenAI など）やネイティブライブラリが必要です。ここではローカルで機能確認するための設定・起動手順と主な機能をまとめます。

---

## プロジェクト概要
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群を提供します。主な役割は以下。

- 売買実行（ExecutionEngine / OrderManager / BrokerClientFactory 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI 補助（ニュース NLP による銘柄センチメント、レジーム判定）
- ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

設計方針の一例：
- 本番 DB と Paper Trading DB は分離（KABUSYS_ENV により切替）
- ルックアヘッドバイアス対策（date.today() を直接参照しない等）
- フェイルセーフ（API 失敗時はゼロやスキップで続行）
- 多くのコンポーネントは純粋関数または副作用を最小化した実装

---

## 主な機能一覧
- Execution
  - 実際の発注フロー管理（OrderManager / Reconciler）
  - Paper Trading モード（MockBroker、data/paper_trading.db に記録）
- Monitoring
  - システムリソース監視（CPU/Memory/Disk）、プロセス生存チェック
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限監視 → Kill Switch（data/kill.flag）発動
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定、等配分/スコア配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- Research
  - Momentum / Volatility / Value などのファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini 等）でスコアリングし ai_scores に保存
  - マクロニュース + ETF MA200 乖離から日次市場レジーム判定・保存
- Tools
  - paper_verification_report: Paper Trading 結果の検証レポート生成

---

## セットアップ手順（開発 / ローカル確認向け）
1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil requests streamlit openai
   - さらに Execution の実ブローカーを使う場合はその依存を追加

   （requirements.txt がないため上記を参考にインストールしてください。）

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data

4. 環境変数（.env）を用意
   - .env もしくは .env.local に設定します。自動ロード順序は OS 環境変数 > .env.local > .env。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
   - KABU_API_PASSWORD — 必須（kabuステーション API）
   - OPENAI_API_KEY — AI 機能を使う場合に必須
   - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE — paper_trading の約定モード（instant, partial, never, reject。デフォルト: instant）
   - DUCKDB_PATH — デフォルト data/kabusys.duckdb
   - SQLITE_PATH — 監視用デフォルト data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — Paper Trading DB（デフォルト data/paper_trading.db）
   - PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト data/execution.pid）
   - KILL_FLAG_PATH — kill.flag（デフォルト data/kill.flag）
   - LOG_LEVEL — ログレベル（DEBUG, INFO ...）

   簡易 .env 例:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   ```

5. 初回 DB 初期化
   - 監視用 DB 等は起動スクリプトが自動でテーブル作成・マイグレーションを行います（init_monitoring_db）。

---

## 使い方（実行例）
※ 実行はプロジェクトルート（pyproject.toml / .git がある想定）で行ってください。

- 監視ループを起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - または KABUSYS_ENV を指定して実行:
    KABUSYS_ENV=paper_trading python -m kabusys.run_monitoring

  仕様:
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil 使用、権限がなければ警告）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用。

- 実行エンジン（ExecutionEngine）を起動
  - Paper Trading で実行する場合は KABUSYS_ENV=paper_trading を設定（MockBroker を使用）。
  - python -m kabusys.run_execution
  - Paper Trading の DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で接続するため、監視プロセスが動いていないと DB が存在しない旨のエラー表示になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数引数）。
  - プログラム的に呼ぶ例:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    score_news(duckdb_conn, date(2026,4,1))
    score_regime(duckdb_conn, date(2026,4,1))

- 環境変数の変更例
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

---

## 主要コンポーネントの振る舞いメモ
- Settings: .env / 環境変数のラッパー。多くの既定値が定義されている（例: DB パス、Paper fill mode）。
- MonitoringDB: SQLite を使った監視ログの永続化。init_monitoring_db() でテーブル作成・マイグレーションを行う。
- KillSwitch: RiskMonitor の結果などを評価して data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る。
- Reconciler: 起動時に OrderSent 状態をブローカーと突合して同期し、ポジション差分を検出する。
- News / Regime AI: OpenAI を用いてニュースを銘柄別にスコアリング・マクロセンチメントを算出。API の失敗は安全側で処理（0 やスキップ）される設計。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 配下の主要ファイルと役割（本リポジトリのサンプルに基づく抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（Settings）
  - run_monitoring.py — システム監視ポーリングループ起動スクリプト
  - run_execution.py — 実行エンジン起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py — CPU/Memory/Disk/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 操作
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注フロー管理
    - reconciler.py — 起動時リコンシリエーション
    - （その他 broker_factory, execution_engine, order_repository 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC 計算、統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込み
    - regime_detector.py — マクロ+ETF MA200 で市場レジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（実際のリポジトリ全体は上記以外にもモジュールが存在する可能性があります）

---

## トラブルシューティング・注意点
- 権限: psutil による優先度設定や CPU affinity は管理者権限が必要な場合があります。失敗時は警告ログが出力され処理は継続します。
- OpenAI: API キー未設定の場合、AI 機能は動作しません（score_news / score_regime は ValueError を送出）。
- Streamlit: DB を read-only で開くため、監視プロセスが DB を作成していないとエラーになります。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時やパッケージ化後に自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading: KABUSYS_ENV=paper_trading により MockBrokerClient を使用し、本番 DB と完全分離して data/paper_trading.db に記録します。

---

## 開発メモ / 今後の拡張ポイント
- stocks マスタで lot_size を銘柄ごとに持たせる等の拡張がコメントで示されています。
- position sizing や sector cap の価格欠損時のフォールバックロジック（前日終値等）の改善余地あり。
- DuckDB / SQLite 間のバージョン差異（executemany の挙動等）に注意して実装が行われています。

---

必要であれば、実行コマンドのより詳細な例、.env.example の完全テンプレート、依存パッケージの固定バージョン（requirements.txt）をさらに作成します。どの情報を優先して追加しましょうか？