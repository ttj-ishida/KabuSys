# KabuSys

日本株自動売買フレームワークの軽量コアライブラリ（README for code base）

以下はソースツリー（src/kabusys 以下）に基づく利用者向けの README です。起動スクリプト、監視、ペーパートレード検証、AI / リサーチ用ツール等を含みます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコア実装です。  
主な目的は次のとおりです。

- 市場データ（DuckDB）を使ったファクター計算・研究機能
- シグナル → ポートフォリオ構築 → 発注までのロジック（発注エンジン）
- 発注状況・システム状態の監視・アラート
- Paper Trading（モックブローカー）による検証・レポート生成
- OpenAI を用いたニュース NLP（センチメント）やレジーム検出

設計方針として「可観測性」「部分故障に対するフェイルセーフ」「ルックアヘッドバイアスの排除」を重視しています。

---

## 主な機能一覧

- monitoring
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留、約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限検出、ダッシュボード更新、risk_log への記録
  - KillSwitch / AlertManager: 条件に応じた停止フラグ書き込み / LINE へプッシュ通知（設定時）
  - streamlit による監視ダッシュボード表示
- execution
  - ExecutionEngine（起動スクリプト経由）: Broker クライアント、OrderManager、RiskManager、Reconciler などの組み立てと実行
  - Reconciler: 再起動時の注文状態突合・ポジション差分検出
  - OrderManager / OrderRepository: 注文状態マネジメント（SQLite ベース）
- portfolio
  - 銘柄選定、重み計算、ポジションサイズ決定、セクターキャップ、レジーム乗数
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- ai
  - news_nlp: raw_news を LLM（OpenAI）で評価して ai_scores に格納
  - regime_detector: ETF の MA200 とマクロニュースセンチメントを合成して market_regime を生成
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）
- config
  - Settings クラス: .env ファイル / 環境変数の読み込み・検証。自動ロードの仕組みあり

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意
   - 推奨: Python 3.10+（ソースは型注釈等を使用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate もしくは .\.venv\Scripts\activate（Windows）

2. 依存パッケージをインストール
   - requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主な依存 (実行に必要な最小例):
     - duckdb, psutil, requests, openai, streamlit

   （本リポジトリに requirements.txt がない場合は上のパッケージを pip で個別インストールしてください。）

3. 環境変数 / .env
   - プロジェクトルートの .env / .env.local を自動読み込みします（デフォルト）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=... (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（監視アラートに使用、任意）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject）

4. 初期データディレクトリ
   - data/ ディレクトリを作成（DB ファイルやフラグファイルが格納される）
     - mkdir -p data

---

## 使い方（代表的なコマンド）

- 実行用スクリプト（Production/Dev 共通）
  - 監視プロセス起動:
    - python -m kabusys.run_monitoring
    - 補足: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
    - 監視は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 monitoring DB）を使用します
  - ExecutionEngine 起動:
    - python -m kabusys.run_execution
    - 補足: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に分離して記録します
    - 実行中は data/execution.pid が作成され、data/stop_requested.flag の存在で停止します
  - streamlit ダッシュボード:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - レポート生成:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db /path/to/paper_trading.db
    - デフォルト DB: data/paper_trading.db

- AI 機能
  - kabusys.ai.score_news / regime_detector.score_regime を呼んでニューススコア / レジーム判定を行います（OpenAI API キー必須）

- 停止フラグ / キルスイッチ
  - 実行停止を外部からトリガーする場合、プロジェクト data ディレクトリに stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して停止します
  - KillSwitch は内部判断で data/kill.flag を生成し ExecutionEngine を停止する仕組み（しきい値超過時など）

---

## 設定の詳細（Settings）

- Settings クラス（src/kabusys/config.py）が各種環境変数を解決します。自動で .env / .env.local を読み込み、OS 環境変数を上書きしない仕様（.env.local は上書き可）。
- KABUSYS_ENV の有効値: development, paper_trading, live（不正値は例外）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- SQLite / DuckDB の既定パスは data/ 下にあります（必要に応じて環境変数で変更）

---

## ディレクトリ構成（主要ファイル・モジュール）

（src/kabusys をルートとして簡略化した構成）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / .env 読み込み
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite の監視ログ永続化（schema/migrations）
    - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常検出
    - risk_monitor.py        — ドローダウン/ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — LINE プッシュ通知
    - monitoring_engine.py   — モニタ群の統括ループ
    - streamlit_dashboard.py — streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - ... （発注周りの実装）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (ランタイムの DB / PID / flag を置く想定ディレクトリ, 手動で作成)
  - tools/
    - paper_verification_report.py

---

## 運用上の注意 / ヒント

- 監視（run_monitoring）は KABUSYS_ENV に関係なく settings.sqlite_path（監視用 DB）を使用します。監視 DB と発注用 DB が分離されていることに注意してください。
- paper_trading モードでは本番 DB と完全に分離された PAPER_TRADING_SQLITE_PATH を使用する設計です（実際のブローカー呼び出しを模擬）。
- process priority / CPU affinity は psutil を用いて OS に依存せず設定しようとしますが、権限不足で失敗することがあります（ログに警告が出ます）。
- OpenAI API による機能（news_nlp, regime_detector）は API キーが必要。失敗時はフォールバックを行う設計ですが、実運用ではレート制限・コストに注意してください。
- DB スキーマの後方互換性のために簡易マイグレーション処理（カラム追加など）が実装されています。

---

## よくあるコマンドまとめ

- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動（paper_trading モード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば README に以下を追加します：
- requirements.txt の推奨内容（バージョン固定例）
- .env.example の具体例
- CI / テスト実行方法（pytest 等）
- 各モジュールのより細かい API ドキュメント（関数・戻り値の詳細）

どの情報を優先して追加しましょうか？