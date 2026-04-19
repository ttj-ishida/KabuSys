# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）。

このリポジトリはトレード実行エンジン、監視サブシステム、ポートフォリオ構築・サイズ決定、リサーチ（ファクター計算）、
および OpenAI を使ったニュース NLP / レジーム判定などの補助ツールを含みます。

注意: .env や API キーなど秘匿情報は絶対に Git にコミットしないでください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- ファイル／ディレクトリ構成

---

プロジェクト概要
- 実運用を想定した日本株自動売買システムのコアライブラリ群。
- 実行エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、リスク管理、注文管理、ポートフォリオ構築ロジック、研究用ファクター計算、AI を用いたニューススコアリングなどを含む。
- SQLite（監視ログ等）と DuckDB（時系列・分析用）をデータストアとして利用。
- paper_trading モードが用意されており、本番 DB とは分離したペーパートレードが可能。

---

主な機能一覧
- 実行エンジン起動スクリプト（run_execution）:
  - KABUSYS_ENV による paper_trading / live / development 切り替え。
  - Paper Trading 時は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）。
  - プロセス優先度の設定・PID 管理・停止フラグ対応。
- 監視プロセス（run_monitoring / MonitoringEngine）:
  - CPU / メモリ / ディスク の監視、Execution プロセス生存確認、データ鮮度チェック。
  - リスク監視（ドローダウン、ポジション上限）と Kill Switch（データ/警告に基づき停止フラグを作成）。
  - 監視ログは SQLite（data/monitoring.db）に永続化。
- ポートフォリオ構築（kabusys.portfolio）:
  - 候補選定、重み計算（等金額・スコア加重）、セクターキャップ適用、ポジションサイズ計算（単元丸め・資金制約適用）。
- 研究モジュール（kabusys.research）:
  - モメンタム、ボラティリティ、バリュー等のファクター算出（DuckDB を使った SQL + Python 実装）。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ等。
- AI 補助（kabusys.ai）:
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメント評価（ai_scores テーブルへ書込）。
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して日次で市場レジーム判定し DB に保存。
  - API 呼び出しはリトライ／バックオフやレスポンス検証を組み込み（フェイルセーフ設計）。
- ツール:
  - 設定ウィザード（config_setup）: 対話式に .env を生成/更新。
  - 設定検証 CLI（validate_config）: .env と config/*.yaml の存在・基本妥当性チェック（--strict オプションあり）。
  - paper_verification_report: ペーパートレーディング DB を解析して運用検証レポートを生成。
- ユーティリティ:
  - 統一的なロギング設定（console + 日次ファイルローテーション）。
  - プロセス優先度 / CPU affinity 設定ユーティリティ。
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

---

セットアップ手順（ローカル開発向け）
前提: Python 3.10 以上を推奨（typing の構文などを利用）。

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   pip install --upgrade pip
   pip install duckdb psutil openai

   オプション（YAML 検証や追加ツールが必要な場合）:
   pip install pyyaml

   （必要に応じて requirements.txt を用意している場合はそれを使用してください）

4. .env を作成
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup

   - もしくは手動で .env を作成（プロジェクトルート）。必要最低限のキー:
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here

   - 注意: .env は絶対にリポジトリにコミットしないこと。

5. 設定検証（任意）
   python -m kabusys.validate_config
   警告も失敗としたい場合:
   python -m kabusys.validate_config --strict

6. データディレクトリ／ログディレクトリ
   デフォルトでは data/ に DB ファイルが作られ、logs/ にログが出力されます。権限などに注意してください。

---

主要な使い方（コマンド例）

- 実行エンジン（ExecutionEngine）を起動
  # 通常（開発）:
  python -m kabusys.run_execution

  # ペーパートレードで起動（.env の KABUSYS_ENV を paper_trading にするか環境変数で指定）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  特記事項:
  - Paper トレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に発注記録を保存します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

- 監視ループを起動
  python -m kabusys.run_monitoring

  - ポーリング間隔を秒単位で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    （デフォルト 60 秒）
  - 監視は常に（環境にかかわらず）本番 sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 停止はプロセスに SIGINT（Ctrl+C） またはプロジェクトの data/stop_requested.flag を作成することで行えます。

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラム内で利用）
  - OpenAI API キーは環境変数 OPENAI_API_KEY で指定するか、関数引数で渡せます。
  - 例（ライブラリ呼び出し）:
    from kabusys.ai import score_news
    # duckdb_conn は kabusys.config.Settings.duckdb_path に接続した DuckDB 接続
    written = score_news(duckdb_conn, target_date, api_key="sk-...")

---

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード

- 動作環境:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development

- データベース / ファイルパス:
  - DUCKDB_PATH  (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH  (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
  - PID_FILE_PATH, KILL_FLAG_PATH などは Settings クラス経由で取得可能

- ログ:
  - LOG_LEVEL（DEBUG/INFO/WARNING/...）, LOG_DIR（デフォルト logs/）

- 監視:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

- OpenAI:
  - OPENAI_API_KEY — AI モジュール利用時に参照

- その他:
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

---

停止／Kill Switch の仕組み
- 監視サブシステムはリスク条件（ドローダウン・ポジション上限等）を評価し、必要に応じて data/kill.flag を書き込みます。
- ExecutionEngine は起動時／実行中に kill.flag や stop_requested.flag を監視し、検出時に安全に停止します。

---

ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイルと役割の概略です。

- src/kabusys/
  - __init__.py                  — パッケージ定義 / バージョン
  - config.py                    — Settings クラス（.env 自動ロード含む）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングスクリプト

  - execution/                    — 発注・エンジン関連（省略されているが起動で使用）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status / trade_logs / risk_logs / positions / dashboard）
    - system_monitor.py           — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py            — 注文ログ・約定異常検出（実装あり）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 管理
    - monitoring_engine.py        — 各 Monitor を束ねる

  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 発注株数決定、資金制約・単元丸め
    - risk_adjustment.py          — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py          — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py      — 将来リターン・IC・統計サマリ

  - ai/
    - news_nlp.py                 — ニュースNLP（OpenAI）で銘柄スコア算出・ai_scores 書込
    - regime_detector.py          — レジーム判定（MA200 + マクロセンチメント）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - logging_setup.py            — 共通ログ設定
    - process_priority.py         — プロセス優先度 / CPU affinity

- data/                            — デフォルトの DB / フラグ / PID を配置する想定（自動作成）
  - monitoring.db (SQLITE_PATH デフォルト)
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                            — デフォルトログ出力先（setup_logging が作成）

（実際のリポジトリには他にもサブモジュールや追加ファイルが存在します。上は主な構成の抜粋です。）

---

運用上の注意事項
- 本番運用時（KABUSYS_ENV=live）は設定（特に LINE 通知周りや KILL_FLAG_CLEAR_ON_START）を慎重に確認してください。
- OpenAI 利用には API キーが必要です。API 呼び出しはレート制限、ネットワーク障害に対するリトライロジックがありますが、運用コストに注意してください。
- .env にはシークレットを含めるため、必ず .gitignore に含め、適切に管理してください。
- process_priority の設定はプラットフォーム依存で権限不足により失敗することがあります（警告ログのみ）。

---

開発／拡張のヒント
- DuckDB を使ったファクター計算は SQL ベースなので、分析用クエリの追加や最適化が容易です。
- AI モジュールはレスポンス検証を厳格に行っているため、プロンプト・モデル変更時は検証ロジックも見直してください。
- ポジションサイズ計算やセクターキャップなどのパラメータは関数引数で変更可能です。ユニットテストを書きやすい純粋関数設計になっています。

---

ライセンス、貢献、問い合わせ
- ライセンスや貢献方法、連絡先はリポジトリのトップレベル README / CONTRIBUTING を参照してください（ここには含まれていません）。

---

以上。README に追加したい具体的なコマンド例や環境固有の注意点があれば教えてください。