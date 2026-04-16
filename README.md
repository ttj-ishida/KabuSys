# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買/検証/監視を目的としたモジュール群です。トレーディングエンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュースセンチメント評価などを含みます。

---

## プロジェクト概要

主な目的・設計方針:

- 日本株自動売買システムの基本機能群を提供する（発注、リコンシリエーション、リスク監視、監視ダッシュボード等）。
- 実行系（live）と Paper Trading を分離可能（環境変数 KABUSYS_ENV）。
- DuckDB / SQLite をデータ層として使用（価格データは DuckDB、監視や発注ログは SQLite）。
- AI（OpenAI）を使ったニュースセンチメントや市場レジーム判定モジュールを提供（フェイルセーフ・リトライ実装あり）。
- 外部環境（.env/.env.local / OS 環境変数）から設定を読み込む（自動ロードを無効化可）。

---

## 主な機能一覧

- ExecutionEngine（run_execution.py）
  - ブローカークライアント（実口座／Mock for paper_trading）を用いた発注・注文管理
  - RiskManager、OrderManager、Reconciler による安全運用
  - 起動時の再同期（Reconciler）

- Monitoring（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU/メモリ/Disk/プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - AlertManager: LINE によるプッシュ通知（クールダウン管理）
  - KillSwitch: リスク事象で外部停止フラグを作成（data/kill.flag）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分・スコア配分、セクター上限適用、ポジションサイジング（単元丸め・集約キャップ）

- 研究・ファクター（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI モジュール（kabusys.ai）
  - news_nlp.score_news: ニュース記事を集約して OpenAI でセンチメント評価 → ai_scores へ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM 結果を合成して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（注文成功率、稼働率、レイテンシ等）
  - Streamlit ベースの監視ダッシュボード（monitoring/streamlit_dashboard.py）

---

## セットアップ手順

前提: Python 3.9+（若干の型注釈 / typing に依存）。以下は最低限の手順例です。

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - コード内の import から必要なパッケージ例:
     - duckdb, psutil, requests, openai, streamlit
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   ※ 実際はプロジェクトに requirements.txt があればそちらを利用してください。

4. データディレクトリ作成
   ```
   mkdir -p data
   ```

5. 環境変数設定
   - プロジェクトルートに `.env`（任意）を置くと自動読み込みされます（.env.local を優先して上書き読み込み）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例 (.env):
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=xxxx
   LINE_USER_ID=Uxxxxxxxxxxxx
   ```

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading のときは MockBroker を利用し、Paper DB（data/paper_trading.db）を使います。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用（未設定時は送信をスキップ）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒；デフォルト: 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）

---

## 使い方（主な起動コマンド）

- ExecutionEngine（発注エンジン）起動
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と完全に分離）。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます。プロセスが存在しない stale PID は SystemMonitor が検出・削除します。

- Monitoring（システム監視）起動
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
  - 補足:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを保存します。

- Streamlit ダッシュボード（監視 UI）
  - 実行:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ブラウザでダッシュボードを表示し、ダッシュボード / ポジション / 注文履歴 / システム状態を確認できます。

- Paper Trading 検証レポート（コマンドラインツール）
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```
  - 出力: 稼働率、注文成功率、送信率、レイテンシなどのサマリと PASS/FAIL 判定を標準出力に印字します。

- AI モジュールの利用（Python API）
  - ニュースのスコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    n_written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    n = score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 監視 / 停止フラグ関連

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py のループがこのファイルの存在を検知すると優雅に終了します（運用上の停止フラグ）。
- data/kill.flag
  - KillSwitch がリスク閾値を超えた場合に書き込まれるファイル。ExecutionEngine は起動時にこのフラグを確認し、存在する場合は起動を回避することができます（Settings.kill_flag_clear_on_start を使って起動時クリアの動作を制御）。
- PID ファイル
  - data/execution.pid などに PID を書くことでプロセスの生存確認を行います。stale PID は SystemMonitor が検出して削除します。

---

## ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys）のおもなファイル / ディレクトリです。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / .env ロードと Settings
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - portfolio/
      - __init__.py
      - portfolio_builder.py         — 候補選定・等配分/スコア配分
      - risk_adjustment.py           — セクター制限・レジーム乗数
      - position_sizing.py           — 発注株数計算・集約キャップ
    - research/
      - __init__.py
      - factor_research.py           — momentum/volatility/value
      - feature_exploration.py       — 将来リターン・IC・統計
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py           — 市場レジーム判定（MA + LLM）
    - monitoring/
      - __init__.py
      - monitoring_db.py             — SQLite スキーマ / DB 操作ラッパ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py             — LINE 通知
      - monitoring_engine.py         — 各 Monitor を束ねる実行ループ
      - streamlit_dashboard.py       — Streamlit ダッシュボード
    - utils/
      - __init__.py
      - process_priority.py          — プロセス優先度 / cpu affinity 設定
    - execution/                      — (発注関連コアモジュール)
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - ... (broker, order_record 等)
    - data/ (外部データファイル・DB を置く想定)
      - kabusys.duckdb (デフォルト DUCKDB_PATH)
      - monitoring.db (デフォルト SQLITE_PATH)
      - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

---

## 運用上の注意 / ヒント

- 環境分離
  - Paper Trading を使用する場合は KABUSYS_ENV=paper_trading を設定して、発注は MockBroker に切り替えてください。Paper DB は data/paper_trading.db（デフォルト）に保存されます。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対して必要なカラム追加の簡易マイグレーションを実行します。
- OpenAI 使用時
  - API キーは安全に管理してください。AI モジュールは失敗時にフェイルセーフ（0.0 等）で継続するよう実装されていますが、API 利用量には注意してください。
- 権限・優先度
  - set_process_priority は OS に依存します。権限不足や未対応 OS の場合は設定がスキップされます。

---

必要であれば、README に
- requirements.txt の例
- より詳細な .env.example
- デプロイ手順（systemd / Docker 構成例）
などを追加できます。希望があれば教えてください。