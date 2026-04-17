# KabuSys — README

本リポジトリは日本株自動売買システム KabuSys のコードベースです。ここではプロジェクトの概要、主要機能、セットアップ手順、使い方（主要スクリプトの実行例）、およびディレクトリ構成を日本語でまとめます。

※ 本 README はソースコード（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したモジュール化されたコードベースです。主な目的は以下です。

- 戦略（ファクター計算・特徴量）に基づくポートフォリオ構築ロジック
- 注文の発行・管理・リコンシリエーション（Execution Engine）
- システム・取引・リスクの監視（Monitoring）
- Paper Trading 用の分離された検証インフラ
- ニュースを用いた AI（LLM）ベースのセンチメント評価・レジーム判定
- 検証用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計上の特徴：
- DuckDB / SQLite を用いたデータレイヤ（prices_daily, raw_financials, ai_scores, monitoring.db など）
- 環境ごとの挙動切替（KABUSYS_ENV による: development / paper_trading / live）
- Paper Trading は本番 DB と完全分離（専用 SQLite を使用）
- 自動ロードされる .env / .env.local による設定管理（ただし環境変数優先）

---

## 主な機能一覧

- ポートフォリオ構築
  - シグナルの候補選定（rank/score ベース）
  - 等ウェイト・スコアウェイト・リスクベースのウェイト計算
  - セクター集中制限・レジーム乗数の適用
  - 株数（lot）丸め・投下資金スケーリング

- ファクター計算（research）
  - Momentum / Volatility / Value ファクターの計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- Execution（注文処理）
  - OrderManager / OrderRepository / ExecutionEngine / Reconciler（再起動時の同期機能）
  - Broker クライアントの抽象化（本番 / モックの切替）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常の監視
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボードの更新
  - KillSwitch: リスクトリガーで ExecutionEngine に停止フラグを設定
  - AlertManager: LINE Push による通知（クールダウン機能付）
  - Streamlit ダッシュボード（監視用）

- AI（LLM）連携
  - news_nlp: raw_news をまとめて LLM に投げ、銘柄ごとのセンチメントを ai_scores に書込む（OpenAI）
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM 評価を合成して市場レジームを算出・永続化

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等）
  - Streamlit ダッシュボード表示

---

## セットアップ手順（ローカルでの実行想定）

前提
- Python 3.9+ を想定（ソースは型注釈等で 3.9+ に適合）
- Git で取得し、プロジェクトルートが .git または pyproject.toml を含むこと

1. リポジトリをクローン / 取得
   - 例: git clone ...

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - requirements.txt は付属しない想定のため、主要依存をインストールしてください（少なくとも以下が必要です）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード使用時)
   - 例:
     pip install duckdb psutil requests openai streamlit

4. 環境変数設定
   - プロジェクトルートの .env / .env.local を利用するか、OS 環境変数で設定します。
   - 自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で読み込まれます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須の場面あり）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用の DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60 秒）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（監視/停止制御用）

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

6. DB 初期化
   - Monitoring 関連のテーブルはスクリプト実行時に init_monitoring_db() により冪等で作成されます。
   - 価格データ等は DuckDB の prices_daily 等テーブルを準備してください（研究機能・AI 機能で参照）。

---

## 使い方（主要スクリプト）

以下は主要な起動方法の例です。プロジェクトルートから実行してください。

- Execution Engine（注文処理エンジン）起動
  - 目的: 注文の実行・リスク管理・リコンシリエーション等を行う
  - 実行例:
    python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB と分離します。
    - 実行中の停止は data/stop_requested.flag を作成することで外部から停止できます。
    - PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

- Monitoring（監視ループ）起動
  - 目的: SystemMonitor、TradeMonitor、RiskMonitor 等を周期的に実行して監視ログ・アラートを生成
  - 実行例:
    python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 備考:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照して監視ログを保存します（monitoring 用 DB は Settings.sqlite_path による）。

- Paper Trading 検証レポート生成
  - 目的: paper_trading DB を解析して稼働率・注文成功率・レイテンシ等を出力
  - 実行例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 備考:
    - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能

- Streamlit ダッシュボード起動（監視表示）
  - 実行例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 備考:
    - Monitoring が生成した SQLite DB（読み取り専用で開く）を渡します。

- AI 機能（ニューススコアリング / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を呼ぶことで実行します（DuckDB 接続と target_date を渡す関数 API）。
  - OpenAI API を利用するため OPENAI_API_KEY を設定する必要があります。

---

## 重要な挙動・設定メモ

- .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動で読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットします。

- KABUSYS_ENV の影響
  - development: 開発用（デフォルト）
  - paper_trading: MockBroker を用いて paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録。実際のブローカーへはアクセスしない設計。
  - live: 本番用（本番ブローカー / 本番 DB を利用）

- 停止・キル制御
  - data/stop_requested.flag: run_execution / run_monitoring が監視している「停止要求」フラグ（存在するとループを抜ける）
  - KillSwitch: RiskMonitor 等からのトリガーで data/kill.flag を作成し ExecutionEngine に停止シグナルを送る仕組み
  - PID ファイル: data/execution.pid（既存 PID の存在でプロセス存在チェックを行う）

- Paper Trading の約定モード
  - PAPER_FILL_MODE にて "instant", "partial", "never", "reject" を指定可能（デフォルト: instant）

---

## ディレクトリ構成（抜粋）

以下は主要ファイル / モジュールのツリー（src/kabusys 配下を抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
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
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
      - __init__.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 broker / engine / repository 等の実装)
    - utils/
      - process_priority.py
      - __init__.py
    - research/, portfolio/, ai/, monitoring/ の各モジュール群

（上記以外にも data ディレクトリや DuckDB / SQLite 用のファイルが利用されます）

---

## ロギング / デバッグ

- 各スクリプトは logging.basicConfig(level=logging.INFO) を使うことが多く、LOG_LEVEL 環境変数で調整できます（Settings.log_level）。
- 開発中は KABUSYS_ENV=development とし、必要に応じて LOG_LEVEL=DEBUG を設定してください。

---

## 注意事項・運用上の留意点

- OpenAI API を使う機能（news_nlp, regime_detector）は API キーや外部呼び出しの失敗に対するフォールバックロジックが入っていますが、実運用時はレート制限・コストに注意してください。
- Paper Trading 実行時は本番資金に影響がないよう DB を分離していますが、設定ミスに注意してください（KABUSYS_ENV の切替と DB パスを確認）。
- Process priority / CPU affinity の設定は psutil を利用しています。権限不足や OS によっては警告を出してスキップします。
- DuckDB / SQLite のスキーマはコード内で冪等に初期化・マイグレーションされる部分がありますが、バックアップやバージョン管理を行ってください。

---

必要であれば、用途別の具体例（config の .env 例、実行スクリプトの systemd ユニット例、データ準備手順など）を追加して作成できます。どのトピックを詳しくしたいか教えてください。