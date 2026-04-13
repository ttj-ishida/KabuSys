# KabuSys

日本株向けの自動売買システム（プロトタイプ）。  
本リポジトリはトレーディング実行ロジック、監視・アラート、ポートフォリオ構築、ファクター研究、ニュースNLP（OpenAI）などを含むモジュール群で構成されています。

主な設計方針
- 本番・検証（Paper Trading）を分離する設計（KABUSYS_ENV により切替）
- DuckDB を使った履歴・ファクター計算、SQLite を使った監視ログ
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / レジーム判定（フェイルセーフ実装）
- サービス監視（ポーリング監視、LINE 通知、kill flag による安全停止）

---

## 機能一覧
- 実行（ExecutionEngine）
  - ブローカークライアント抽象化（live / paper_trading の切替）
  - リスク管理（利用率、ポジション制限、ドローダウン等）
  - 注文状態管理・再同期（Reconciler）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill flag 発行
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等ウェイト / スコア加重、リスク調整、単元株丸め、ポジションサイズ計算
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計測、統計サマリ
- AI モジュール
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: MA200 とマクロニュースの LLM 評価を合成して market_regime を判定
  - リトライ・検証・部分書き込み等、頑健性対策あり
- 開発用ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順（例）
前提: Python 3.10+（typing の一部表記に依存しているため）を想定します。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（代表的なもの）
   ```
   pip install duckdb psutil requests streamlit openai
   ```
   - SQLite は標準ライブラリで提供されます。
   - 実際の requirements.txt がある場合はそちらを使用してください。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 必須（最低限）:
     - JQUANTS_REFRESH_TOKEN — （J-Quants 経由のデータ用途）
     - KABU_API_PASSWORD — kabuステーション API パスワード（ブローカー接続）
   - OpenAI／LINE 等は機能利用時に必要:
     - OPENAI_API_KEY — ニュース NLP / レジーム判定を使う場合
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート送信に使用（任意）
   - その他（主な例）:
     - KABUSYS_ENV (development | paper_trading | live) — 環境切替
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（paper_trading の場合使用）
     - SQLITE_PATH, DUCKDB_PATH — デフォルト: data/monitoring.db, data/kabusys.duckdb
     - PID_FILE_PATH, KILL_FLAG_PATH — pid / kill flag のパス
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

   例 `.env`（最小）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   OPENAI_API_KEY=sk-...
   ```

---

## 使い方（主要スクリプト・コマンド）
- 実行プロセス（ExecutionEngine）起動
  - 本番 / 開発を問わずプロセス優先度を高く設定して起動します。
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）に書き込みます。

- 監視プロセス起動（SystemMonitor 単体）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は実行環境にかかわらず本番の sqlite_path を使用してログを残します。

- Streamlit ダッシュボード（監視確認）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール呼び出し（ライブラリ API として）
  - ニューススコア付与:
    ```py
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

注意点:
- process priority / CPU affinity の設定は OS に依存し、権限不足で失敗する場合は警告ログでスキップされます。
- OpenAI 呼び出しはレート制限・ネットワーク問題に対するリトライやフォールバック（score=0 等）を実装していますが、APIキー／課金設定は各自で行ってください。
- Paper Trading は本番 DB と分離する設計になっています（settings.is_paper を参照）。

---

## ディレクトリ構成（抜粋）
（src/kabusys 以下を中心に記載）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - order_manager.py — 注文作成 / 送信 / 同期ロジック（OrderManager）
    - order_repository.py — 注文永続化（SQLite）
    - reconciler.py — 起動時の注文・ポジション再同期
    - execution_engine.py — 実行エンジン本体（EngineConfig / run_session）
    - broker_factory.py — BrokerClient の生成（live / mock 切替）
    - ...（その他 execution 関連モデル）
  - monitoring/
    - monitoring_db.py — SQLite 監視テーブル定義と CRUD（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag ファイル操作
    - alert_manager.py — LINE Push 実装
    - monitoring_engine.py — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — raw_news → OpenAI → ai_scores 書き込み
    - regime_detector.py — MA200 + マクロニュースでレジーム判定
  - data/  (想定配置）
    - kabusys.duckdb (DuckDB path default: data/kabusys.duckdb)
    - monitoring.db  (SQLite default: data/monitoring.db)
    - paper_trading.db (Paper Trading 用 SQLite default: data/paper_trading.db)
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 主要設定 / パス
- DuckDB: DUCKDB_PATH (default: data/kabusys.duckdb)
- Monitoring SQLite: SQLITE_PATH (default: data/monitoring.db)
- Paper Trading SQLite: PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID ファイル: PID_FILE_PATH (default: data/execution.pid)
- kill flag: KILL_FLAG_PATH (default: data/kill.flag)
- 環境種別: KABUSYS_ENV ∈ {development, paper_trading, live}

---

## 運用上の注意
- データベースマイグレーションは monitoring_db.init_monitoring_db() で簡易対応（カラム追加など）。
- OpenAI を使用する処理は API キーがない場合や API 失敗時にフォールバックするよう実装されていますが、APIコストは考慮してください。
- プロセス優先度 / CPU affinity の設定は権限に依存します（sudo 等が必要な場合あり）。
- kill.flag による停止は ExecutionEngine 側で確認・終了する設計です。kill.flag の存在は ExecutionEngine に停止を促します（冪等でファイルを書きます）。

---

README に記載されていない細かい実装・使い方はソース内 docstring / 関数コメントを参照してください。追加の使い方（サンプル実行、CI、デプロイ手順等）を希望する場合は用途に応じて追記します。