# KabuSys

KabuSys は日本株向けの自動売買システムのコードベースです。戦略の実行・注文管理・リスク監視・監視ダッシュボード・リサーチ用ファクター計算・ニュース NLP（LLM）によるセンチメント評価など、運用に必要なコンポーネントを含みます。

---

## プロジェクト概要

- 言語: Python
- 目的: 日本株自動売買の実行基盤（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）を提供する。
- DB:
  - SQLite: 監視ログ / 注文ログ（ローカル永続化）
  - DuckDB: 履歴株価やファイナンスデータ等のリサーチ用集計
- 環境分離:
  - KABUSYS_ENV により `development` / `paper_trading` / `live` を切り替え可能
  - `paper_trading` では MockBroker を利用し、本番 DB と分離された paper_trading 用 SQLite を使用

---

## 主な機能一覧

- Execution
  - 注文作成・送信、OrderState 管理（OrderManager）
  - リスクチェック（RiskManager）
  - 起動時のリコンシリエーション（Reconciler）
  - Paper trading モード（MockBroker）と本番モードの分離
- Monitoring
  - システム状態監視（CPU/Memory/Disk、プロセス生存確認、データ鮮度）
  - 注文滞留・約定異常価格検出
  - ドローダウン・ポジション上限監視（KillSwitch トリガー可能）
  - LINE へのアラート送信（AlertManager）
  - Streamlit ダッシュボード（read-only）
- Portfolio
  - 候補選定・重み付け（等配分 / スコア配分）
  - セクター制限適用、レジームに応じた乗数
  - 株数算出（単元丸め・利用可能資金に基づくスケール）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン・IC（Information Coefficient）・統計サマリ
- AI
  - ニュース記事の LLM によるセンチメントスコア付与（ai.news_nlp）
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（コードは typing / new style 機能を使用）
- Git を使ってリポジトリを取得

1. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージのインストール（例）
   必要最小限のパッケージ（プロジェクト状況により追加が必要）
   ```
   pip install duckdb psutil requests streamlit openai
   ```
   - duckdb: リサーチ用集計
   - psutil: プロセス優先度 / システム情報
   - requests: LINE API
   - streamlit: ダッシュボード
   - openai: LLM 呼び出し
   SQLite は標準ライブラリで利用可能です。

3. データディレクトリ作成
   ```
   mkdir -p data
   ```
   デフォルト DB パス:
   - monitoring DB: data/monitoring.db
   - paper trading DB: data/paper_trading.db
   - duckdb: data/kabusys.duckdb

4. 環境変数配置
   プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   主要な環境変数（例・説明）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
   - PAPER_FILL_MODE: paper_trading の約定動作（instant|partial|never|reject、デフォルト: instant）
   - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   .env.example がある場合はそれを参考にしてください。（config モジュールは値が未設定だと明示的に例外を投げます）

5. DB 初期化
   実行時に monitoring 用テーブルは自動作成（init_monitoring_db）が走るため、通常は手動初期化不要ですが、data ディレクトリを作った上で実行してください。

---

## 使い方

以下は主要コンポーネントの起動例です。src 配下をそのまま実行する前提です。

1. ExecutionEngine を起動（プロセス優先度を上げ、データベース/ブローカーを接続）
   - 通常実行:
     ```
     python -m kabusys.run_execution
     ```
   - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading 用 SQLite に記録されます。
   - 停止手段:
     - プロジェクトルートの data/stop_requested.flag を作成すると、run_execution のループが検知して安全に停止します。
     - KillSwitch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で停止処理を行う設計になっています（Settings.kill_flag_path でパス指定可能）。

2. Monitoring を起動（SystemMonitor のポーリングループ）
   ```
   python -m kabusys.run_monitoring
   ```
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
   - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（settings.sqlite_path）を使用して監視ログを記録します。
   - 停止: data/stop_requested.flag を作成するとループが終了します。

3. Streamlit ダッシュボード（監視ビュー）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - 監視 DB を read-only で開き、ダッシュボードを表示します。

4. Paper Trading 検証レポート
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。
   - 出力は標準出力にレポートを表示します（稼働率 / 注文成功率 / レイテンシ等の判定を行う）。

5. AI（ニューススコアリング / レジーム判定）
   - プログラムから呼び出す形（例: Python スクリプトやジョブ）:
     ```python
     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     written = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
     ```
     - OPENAI_API_KEY 環境変数も利用可能。
   - レジームスコア:
     ```python
     from kabusys.ai.regime_detector import score_regime
     written = score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
     ```

6. ログ・監視
   - run_* スクリプトは標準出力に INFO レベルのログを出します。必要に応じて LOG_LEVEL を設定してください（Settings.log_level を参照する箇所があるため）。

---

## 停止・強制停止・フラグファイルについて

- data/stop_requested.flag
  - run_execution / run_monitoring がループ中に定期的にチェックしているファイル。存在すると安全に終了する（外部からのシャットダウン要求に使用）。
- data/kill.flag
  - KillSwitch が条件を満たすと書き込むフラグ（ExecutionEngine を停止させる意図）。KillSwitch は RiskMonitor の結果などを評価して書き込みます。
- 実行中に PID ファイル（data/execution.pid）を使って実プロセスの生存を判定するロジックがあります。PID ファイルが古く不正な場合は Monitoring が検知して削除します。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下を中心に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / .env の読み込み・Settings
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - execution/
      - execution_engine.py          — 実行エンジン（EngineConfig など）
      - order_manager.py             — 注文管理（OrderManager）
      - order_repository.py          — 注文永続化（SQLite）
      - reconciler.py                — 起動時リコンシリエーション
      - broker_factory.py            — ブローカークライアント生成（Mock含む）
      - ... (その他関連モジュール)
    - monitoring/
      - monitoring_db.py             — monitoring DB スキーマ / CRUD
      - system_monitor.py            — システム状態チェック
      - trade_monitor.py             — 注文滞留 / 約定異常チェック
      - risk_monitor.py              — ドローダウン / ポジション数監視
      - kill_switch.py               — kill.flag 管理
      - alert_manager.py             — LINE 通知ラッパ
      - monitoring_engine.py         — 各モニタを束ねる
      - streamlit_dashboard.py       — Streamlit ダッシュボード
    - portfolio/
      - portfolio_builder.py         — 候補選定 / 重み付け
      - position_sizing.py           — 株数決定・スケーリング
      - risk_adjustment.py           — セクター上限・レジーム乗数
    - research/
      - factor_research.py           — ファクター計算（momentum/value/volatility）
      - feature_exploration.py       — IC・将来リターン等
    - ai/
      - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py           — 市場レジーム判定（MA200 + LLM）
    - data/                           — 実行時生成想定（DB・flag・pid）
    - utils/
      - process_priority.py          — プロセス優先度 / CPU affinity
    - ... その他

---

## 実装上の注意 / 補足

- Monitoring の init_monitoring_db は冪等的（必要なテーブル・カラムが存在しなければ追加）に動作します。既存 DB への軽微なマイグレーションを含みます（例: latency_ms, peak_value カラムの追加）。
- paper_trading モードは実際のブローカー API を呼ばず、検証用に挙動を変更します（DB は paper_trading 専用ファイルへ書き込み）。
- LLM を利用する機能（news_nlp / regime_detector）は API 呼び出しのリトライ・フォールバック処理を備え、API 失敗時は「安全側の既定値」で継続する方針です（例: macro_sentiment=0.0）。
- セキュリティ: .env に API キー等を平文で置く場合はアクセス管理に注意してください。
- テスト: config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。LLM 呼び出し部分は容易にモックできる設計になっています（関数単位で差し替え可能）。

---

もし README をプロジェクトの README.md としてさらに整備（例: requirements.txt の具体化、CI やデプロイ手順、サンプル .env.example の作成、各モジュールの API 仕様ドキュメント）する必要があれば、目的に合わせて追記案を作成します。必要な項目を教えてください。