# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / ツール）
- 環境変数（主な設定項目）
- ディレクトリ構成と主なモジュール説明
- 注意事項 / 運用メモ

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。  
本リポジトリには、注文実行（Execution Engine）、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、AI を用いたニュース/レジーム判定などのモジュールが含まれます。  
データ永続化には SQLite（監視ログ等）と DuckDB（時系列・リサーチ用）を使用します。

設計方針の一部：
- 各モジュールは可能な限り純粋関数または副作用を限定した設計（テスト容易性重視）
- 本番 / paper_trading（モック）を環境変数 `KABUSYS_ENV` で切替
- LLM（OpenAI）連携は明示的に API キーを渡すか環境変数 `OPENAI_API_KEY` を使用

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine による発注フロー（ブローカー抽象化）
  - 起動時のリコンシリエーション（Reconciler）で再開・同期処理
  - paper_trading モードでは MockBrokerClient を使用して本番 DB から分離

- Monitoring
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文や約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch / AlertManager: アラート送信（LINE）や停止フラグの出力
  - MonitoringEngine: 各 Monitor の統合ポーリングループ
  - Streamlit ダッシュボード（read-only）で監視情報を可視化

- Portfolio Construction
  - 候補選定、等重/スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap スケーリング）

- Research / Factors
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン・IC（Information Coefficient）計測、統計サマリー

- AI
  - news_nlp: LLM（gpt-4o-mini）を使ったニュースセンチメントスコアリング（ai_scores へ書込）
  - regime_detector: マクロセンチメント + ETF MA200 乖離を合成して市場レジームを判定

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率 / 成功率 / レイテンシ 等）

---

## セットアップ手順（概略）

※ 実際の依存パッケージやバージョンはリポジトリの requirements ファイル等を参照してください（ここでは一般的な準備手順を示します）。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （開発時）pip install -e .

   ※ requirements.txt がない場合は、DuckDB、psutil、requests、streamlit、openai 等を手動でインストールしてください。

4. 環境変数 (.env) の準備
   - プロジェクトルートに .env / .env.local を配置できます。
   - 自動ロード機能は有効（既定）で、OS 環境変数 > .env.local > .env の順に読み込まれます。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データディレクトリの準備
   - デフォルトの DB パス: data/monitoring.db（SQLite）, data/kabusys.duckdb（DuckDB）, data/paper_trading.db（paper_trading）
   - 必要に応じてディレクトリを作成: mkdir -p data

---

## 使い方（実行例）

前提: パッケージをインストール済み、または `PYTHONPATH=src` を設定してモジュールが import できる状態。

- Execution Engine を起動（本番 or paper_trading は KABUSYS_ENV による）
  - python -m kabusys.run_execution
  - paper_trading モードで起動する場合：
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - paper_trading では MockBrokerClient が使われ、デフォルトで data/paper_trading.db を使用します。

- Monitoring のポーリングループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔をカスタムにする:
    - export MONITOR_POLL_INTERVAL=30  （秒）
  - Monitoring は常に本番用の sqlite_path を使って監視ログを書きます（KABUSYS_ENV に依存しません）。

- Streamlit 監視ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

## 環境変数（主な設定項目）

- 決済 / API / 認証
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY (AI 機能利用時に必要)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (AlertManager による LINE 通知)

- 実行環境 / モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使用、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - live: 本番モード
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用: デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
  - PID_FILE_PATH (Execution PID を書くファイル、デフォルト data/execution.pid)
  - KILL_FLAG_PATH (KillSwitch のフラグパス、デフォルト data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (ExecutionEngine 起動時に kill.flag をクリアするか。 "1" で true)

- モニタリング関連
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒、デフォルト 60)
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト "instant"）

※ Settings クラスは `.env` ファイルのパース挙動や自動ロードの詳細を内部実装で提供しています。必須値が未設定の場合は ValueError を投げます。

---

## ディレクトリ構成（抜粋）と主なファイル

ルート: src/kabusys/ 以下を想定

- kabusys/
  - __init__.py          - パッケージエントリ（__version__）
  - config.py            - 環境変数ロードと Settings クラス
  - run_execution.py     - ExecutionEngine 起動スクリプト
  - run_monitoring.py    - SystemMonitor ポーリング起動スクリプト

  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (存在する想定)
    - broker_factory.py / broker_api.py (抽象化・実装分岐)

  - monitoring/
    - monitoring_db.py        - SQLite スキーマ初期化 + DB ラッパー
    - system_monitor.py       - CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py        - 注文滞留 / 約定異常監視
    - risk_monitor.py         - ドローダウン・ポジション上限チェック
    - kill_switch.py          - 停止フラグ管理
    - alert_manager.py        - LINE 通知（クールダウン管理）
    - monitoring_engine.py    - 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py  - Streamlit ベースの監視ダッシュボード

  - portfolio/
    - portfolio_builder.py    - 候補選定・重み計算
    - risk_adjustment.py      - セクターキャップ・レジーム乗数
    - position_sizing.py      - 発注株数計算（lot 単位、aggregate cap）

  - research/
    - factor_research.py      - Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py  - 将来リターン / IC / 統計サマリー

  - ai/
    - news_nlp.py             - ニュースをまとめて OpenAI に投げ、ai_scores を更新
    - regime_detector.py      - ETF MA200 とマクロセンチメントを合成してレジーム判定

  - data/                    - データファイル（デフォルト）
    - monitoring.db         (SQLite, 監視ログ)
    - kabusys.duckdb        (DuckDB, 時系列/リサーチ用)
    - paper_trading.db      (paper_trading 用 SQLite)

  - tools/
    - paper_verification_report.py - Paper Trading の検証レポート生成 CLI

- その他ユーティリティ
  - utils/process_priority.py    - プロセス優先度 / CPU affinity 設定（psutil 利用）

---

## 注意事項 / 運用メモ

- .env のパースは多少独自実装を含み、クォート処理やコメントの扱いが仕様化されています。OS 環境変数は .env より優先され、.env.local は .env を上書きします。
- Monitoring の DB 初期化は `init_monitoring_db()` により自動で行われます（冪等）。テーブル追加時の簡易マイグレーション（列追加）も実装されています。
- AI 機能（news_nlp, regime_detector）は OpenAI API キーが必要です。API 呼び出しはリトライ戦略やパース保護を備えていますが、呼び出し失敗時は安全側のフォールバック（例: スコア 0.0）で継続します。
- paper_trading モードは本番 DB と完全に分離することを意図しています（デフォルトで別 DB を使用）。実行前に PAPER_TRADING_SQLITE_PATH の確認を推奨します。
- Execution / Monitoring を実際に運用する際は、PID 管理 / kill.flag の取り扱い、ログ設定、LINE トークンの保護（権限の管理）に注意してください。
- streamlit ダッシュボードは読み取り専用で SQLite を read-only モードで開くことを推奨します（起動コマンド例参照）。

---

必要であれば、この README をプロジェクトの実際の requirements（依存関係）、詳細なデプロイ手順（systemd / supervisor / Dockerfile 例）、もしくは各モジュールの API ドキュメント（関数引数・戻り値の詳細）に合わせて拡張します。どの部分を詳しくしたいか教えてください。