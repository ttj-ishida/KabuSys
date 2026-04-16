# KabuSys

日本株向け自動売買システムの軽量実装。ポートフォリオ構築、発注エンジン、監視、研究（ファクター計算）や AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な主要コンポーネントを整理した小規模なフレームワークです。主な責務は次のとおりです。

- 戦略に基づく銘柄選定・配分・株数決定（portfolio）
- 発注管理・ブローカ連携・リコンシリエーション（execution）
- システム稼働・注文状況・リスクの監視・アラート（monitoring）
- DuckDB を用いたファクタ計算やリサーチ用ユーティリティ（research）
- OpenAI を用いたニュースセンチメントおよび市場レジーム評価（ai）
- Paper Trading 用の検証レポート生成ツール（tools）

設計方針として、以下を重視しています：
- 実運用での安全性（DB 分離・フェイルセーフ）
- ルックアヘッドバイアス回避（日時参照の扱いに注意）
- 外部 API 呼び出しは明示的に制御（OpenAI API キー等）

---

## 主な機能一覧

- portfolio
  - 銘柄候補選定（スコア順）
  - 等金額 / スコア加重配分
  - セクター集中制限の適用
  - レジームに応じた乗数調整
  - 株数決定（リスクベース・等配分・スコア配分）、単元丸め、投下資金スケーリング

- execution
  - ブローカーファクトリ経由で本番／模擬ブローカーを切り替え
  - OrderManager による注文状態管理
  - Reconciler による起動時の自動復旧（order / position 照合）
  - RiskManager, OrderRepository 等の補助コンポーネント（※実装一部は別ファイル）

- monitoring
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、Execution プロセス監視
  - TradeMonitor: 滞留注文・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: リスク条件で ExecutionEngine を停止するためのフラグ書き込み
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - MonitoringEngine: 各モニタを束ねたポーリングループ
  - Streamlit ダッシュボード（読み取り専用 URI 経由）

- research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）やファクター統計

- ai
  - news_nlp: raw_news を OpenAI に送り銘柄毎にセンチメントを算出し ai_scores に書込
  - regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントで日次レジーム判定

- tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・成功率・レイテンシ等の検証レポートを出力

---

## セットアップ手順

前提: Python 3.9+（typing の構文などを利用）

1. リポジトリをクローン、プロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   requirements.txt が無い場合は少なくとも以下をインストールしてください:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   代表的な環境変数（例）
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY (ai 機能を使う場合に必須)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - DUCKDB_PATH（DuckDB ファイルパス、デフォルト: data/kabusys.duckdb）
   - PAPER_FILL_MODE: instant | partial | never | reject
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

   サンプル .env:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

5. ディレクトリ下の data/ はプロセス PID やフラグ、DB を格納します。必要に応じて権限を確認してください。

---

## 使い方

重要な実行エントリポイントと利用例を示します。

- 監視ループ（Monitoring）
  - スクリプト: src/kabusys/run_monitoring.py
  - 説明: SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新します。MONITOR_POLL_INTERVAL 環境変数で間隔を秒で指定可（デフォルト 60 秒）。監視は常に本番の sqlite_path を参照します（KABUSYS_ENV に依存しません）。
  - 実行例:
    ```
    python -m kabusys.run_monitoring
    ```
  - 停止方法: プロジェクトルートの data/stop_requested.flag ファイルを作成するとループが検知して終了します。

- 発注エンジン（Execution）
  - スクリプト: src/kabusys/run_execution.py
  - 説明: ExecutionEngine を起動し注文処理を行います。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と完全に分離されます。
  - 実行例:
    ```
    # 本番/開発
    python -m kabusys.run_execution

    # Paper Trading
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 停止方法: data/stop_requested.flag を作成するとエンジン停止処理が走ります。kill.flag（Settings.kill_flag_path）を書き込むと監視側から停止シグナルとして扱われます。

- Streamlit ダッシュボード（読み取り専用）
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 実行例:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 注意: ダッシュボードは SQLite を読取り専用 URI で開きます。監視プロセスが DB を保持している場合でも読むことができます。

- Paper Trading 検証レポート
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 使い方:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10 --db data/paper_trading.db
    ```
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL を判定します。

- AI / OpenAI 機能
  - news_nlp.score_news(conn, target_date, api_key=None) — raw_news を集約して ai_scores に書き込みます。OPENAI_API_KEY を環境変数に設定してください。
  - regime_detector.score_regime(conn, target_date, api_key=None) — MA200 とマクロニュースでレジーム判定し market_regime テーブルに書き込みます。

---

## 主要環境変数・設定一覧（要点）

- KABUSYS_ENV: development | paper_trading | live（挙動や DB パスに影響）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB データファイル（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（ai 機能で必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを抑制

---

## トラブルシューティング / 注意点

- Process priority の設定は OS によって権限が必要な場合があります。set_process_priority は失敗した場合に警告を出してスキップします。
- Streamlit から SQLite を開く際は読み取り専用 URI を使用しています。起動に失敗する場合は monitoring DB の存在やパスを確認してください。
- OpenAI 呼び出しはネットワークやレート制限で失敗することがあります。モジュール側でリトライやフェイルセーフ（0.0 でフォールバック）が実装されていますが、API キーとネットワークを確認してください。
- データ鮮度チェックは DuckDB の prices_daily テーブルを参照します。テーブルが空だと data_freshness_ok=False になります。
- stop/kill フラグファイル:
  - data/stop_requested.flag: run_monitoring / run_execution がポーリング中に検知して終了するためのファイル
  - data/kill.flag (Settings.kill_flag_path): KillSwitch により書き込まれる停止指示ファイル（Execution 停止のために使用）

---

## ディレクトリ構成（要約）

リポジトリ内の主要なディレクトリとファイルの概観:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数/設定のロードと Settings クラス
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py             — プロセス優先度/CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
    - position_sizing.py              — 株数決定（リスク制約・単元丸め等）
  - execution/
    - order_manager.py                — 発注状態管理（OrderManager）
    - reconciler.py                   — 起動時リコンシリエーション
    - order_repository.py             — （DBアクセス: 省略箇所あり）
    - ...                             — broker_api 等（別ファイル）
  - monitoring/
    - monitoring_db.py                — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py               — システム監視（CPU / メモリ / データ鮮度 / PID）
    - trade_monitor.py                — 注文滞留・約定異常監視
    - risk_monitor.py                 — ドローダウン・ポジション上限監視
    - kill_switch.py                  — 停止フラグ管理
    - alert_manager.py                — LINE プッシュ通知
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py          — Streamlit ダッシュボード
    - run_monitoring.py               — 入口（プロジェクトルートから参照）
  - research/
    - factor_research.py              — モメンタム/ボラ/バリュー等のファクター算出（DuckDB）
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                     — ニュースから OpenAI によるセンチメント算出
    - regime_detector.py              — レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート生成
  - data/                              — デフォルト DB / PID / フラグの保存先（gitignore で管理推奨）

---

## 開発上の補足

- 自動で .env/.env.local をプロジェクトルートから読み込む仕組みがあります（config.py）。プロジェクトルートは .git または pyproject.toml を基準に探索します。
- DuckDB は分析用途（prices_daily, raw_financials など）に用います。研究モジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて処理します。
- モジュール間で OpenAI 呼び出しロジックは分離されており、テスト用に _call_openai_api をモックすることが容易です。

---

必要であれば、README に次の追加を行えます。
- requirements.txt の自動生成（現在は手動リスト）
- サンプル .env.example の追加
- 実行フロー図（起動順序、フラグファイルのライフサイクル）
- 各機能の API ドキュメント（関数引数/戻り値の詳細）

この README をベースに、運用手順やデプロイ手順（systemd ユニット、Dockerfile 等）を追加することをお勧めします。