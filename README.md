# KabuSys

日本株向け自動売買プラットフォーム（プロトタイプ）。

このリポジトリは、発注実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター研究、ニュースNLP（OpenAI）によるスコアリング等の主要コンポーネントを含みます。SQLite / DuckDB を用いたローカル永続化と、ブローカー API（実装は抽象化）を組み合わせて動作します。

---

## 機能一覧

- ExecutionEngine
  - 注文作成／送信、状態管理、リスク管理、リコンシリエーション（再起動時自動復旧）
  - Paper Trading モード（ブローカーは Mock、DBは本番と分離）
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（価格テーブル）
  - 注文滞留・約定異常価格検出
  - ドローダウン／ポジション上限監視と Kill Switch（停止フラグ出力）
  - LINE による通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio Construction
  - 候補選定、等重・スコア加重配分、ポジションサイズ計算、セクター制約、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - ニュースを LLM でセンチメント評価し銘柄ごとにスコア化（ai_scores）
  - マクロニュース + 指数 MA200 乖離で市場レジーム判定（bull / neutral / bear）
- ツール
  - Paper Trading の検証レポート生成スクリプト

---

## 必要条件 / 推奨環境

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 開発環境では仮想環境を推奨: python -m venv .venv && source .venv/bin/activate

インストール例:
- requirements.txt がない場合:
  - pip install duckdb psutil requests openai streamlit

---

## 設定（環境変数）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（CWDに依存せず __file__ を起点に .git / pyproject.toml を探してルートを特定します）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI を使う機能で必須（ai モジュール）
- KABUSYS_ENV — 環境。`development` | `paper_trading` | `live`（デフォルト: `development`）
  - `paper_trading` の場合、Paper Trading 用 DB を使用（設定: PAPER_TRADING_SQLITE_PATH）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定振る舞い（`instant` | `partial` | `never` | `reject`／デフォルト: `instant`）
- PID_FILE_PATH, KILL_FLAG_PATH — ファイルパスの上書き
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒／run_monitoring 用。デフォルト 60）

Settings クラスで値の検証・デフォルトが行われます。必須項目が未設定の場合は起動時にエラーになります。

例（.env）:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jq_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. .env を作成（.env.example があれば参照）
5. 実行

DB テーブルは起動時に自動作成（init_monitoring_db を使用）されるため、手動マイグレーションは不要です。paper_trading モードでは別 DB（PAPER_TRADING_SQLITE_PATH）を使用します。

---

## 使い方

※ ここではパッケージを Python モジュールとして実行する例を示します。プロジェクトルートは src/ の親が基準になる想定です。

- 監視プロセスを起動（SystemMonitor の単体起動含む）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - Paper Trading モードで起動する例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。停止は kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）か stop_requested.flag（data/stop_requested.flag）で制御します（スクリプトは stop フラグの存在を監視します）。

- Streamlit ダッシュボード起動（監視 DB を読み取り専用で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- AI（ニューススコアリング / レジーム検出）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - プログラムから呼ぶ:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")
    - または kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key="sk-...")

- 停止方法（手動）
  - ExecutionEngine を優雅に停止させるにはプロジェクトルートの data/stop_requested.flag を作成するか、KillSwitch で data/kill.flag を書き込む方法があります。
  - 例: touch data/stop_requested.flag

---

## 重要なファイル・挙動メモ

- .env 自動ロード順序:
  - OS 環境変数 > .env.local > .env
  - ただし OS 側の既存変数は保護され、.env.local の override が保護されます。
- Settings クラスは起動時に env の妥当性をチェック（KABUSYS_ENV や PAPER_FILL_MODE 等）
- MonitoringDB.init_monitoring_db は冪等でテーブル・インデックスを作成し、既存 DB への簡易マイグレーション（カラム追加）も行います。
- process_priority ユーティリティはプラットフォームに依存した優先度設定（psutil 使用）を行います。権限不足時は警告でスキップします。
- AI 周りは外部 API 呼び出しが含まれ、レート制限や一時エラーに対するリトライロジックがありますが、最終的に失敗しても例外を投げずに安全側のフォールバックをする設計の箇所があります（フェイルセーフ）。

---

## ディレクトリ構成

以下は主要なソース配置（src/kabusys 以下）です。実際のファイル群はリポジトリを参照してください。

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / Settings 管理
    - run_monitoring.py
    - run_execution.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py (他多数)
      - broker_factory.py
      - broker_api.py (プロトコル・例外定義)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - data/
      - pipeline.py (prices_daily などの抽象)
      - stats.py (zscore_normalize 等)
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py

---

## 開発 / テストに関する備考

- DB / API の外部依存を持つ機能は、ユニットテストではモック可能な設計（例えば OpenAI 呼び出しやブローカー API 呼び出しを差し替えられる）になっています。
- research / portfolio モジュールは純粋関数が多く、外部副作用を持たず単体テストが容易です。
- streamlit ダッシュボードは監視 DB を read-only URI で開くため、運用中の監視データを安全に閲覧できます。

---

## サポート項目（今後の改善や注意点）

- 価格が欠損（0.0 等）の際のフォールバック戦略（position sizing / sector cap）について注記あり
- 単元株（lot_size）は現状グローバル定義だが、将来は銘柄別に対応する設計に拡張予定
- マイグレーションは簡易（カラム追加）に留まるため、スキーマ変更が大きくなる場合は別途マイグレーションメカニズムが必要

---

README に書かれている操作で不足がある場合、用途（実行 / デバッグ / 開発テスト）を教えてください。具体的なコマンド例や .env のテンプレート、起動ログの読み方などを追加で用意します。