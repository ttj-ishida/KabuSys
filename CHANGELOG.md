CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
このファイルはリポジトリ内のコードから推測して作成したものです。

フォーマット
------------
- 変更はセクションごとに分類（Added / Changed / Fixed / Deprecated / Removed / Security）。
- 既存リリースはバージョン番号（src/kabusys/__init__.py の __version__）に合わせて作成しています。

[Unreleased]
------------
（現時点で未リリースの作業はありません。）

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ初期実装（初回リリース）。
  - src/kabusys/__init__.py: パッケージバージョン __version__ = "0.1.0" を追加。
- 実行用エントリポイント
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - data/stop_requested.flag を検知してループを安全に停止する仕組みを実装。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、Paper Trading 用専用 SQLite（PAPER_TRADING_SQLITE_PATH の指定可、デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動前に data/stop_requested.flag の存在を確認し、既に立っていれば起動を中止。
    - エンジンはスレッドで実行され、stop フラグを検知すると engine.stop() を呼び出して停止する。

- 設定管理
  - src/kabusys/config.py
    - .env ファイル（.env / .env.local）の自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を実装。
    - クォート・エスケープ・export 形式・インラインコメント等に対応した .env パーサーを実装。
    - Settings クラスを提供し、環境変数（DB パス、各種閾値、KABUSYS_ENV 等）をプロパティとして取得可能に。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/kill flag 関連、監視閾値（CPU/MEM/DISK）などのプロパティを追加・ドキュメント化。
    - KABUSYS_ENV / LOG_LEVEL の有効値チェックを実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/*
    - portfolio_builder.py
      - select_candidates: スコア降順＋signal_rank による候補選択。
      - calc_equal_weights / calc_score_weights: 等金額／スコア加重配分（スコア全ゼロ時は等金額にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（unknown セクターは除外しない）。
      - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear を定義、未知は 1.0 にフォールバックして警告）。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく株数計算、lot_size（単元）丸め、aggregate cap（利用可能現金に合わせたスケーリング）、コストバッファ対応などを実装。

- 研究（リサーチ）機能
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials を利用したファクター計算を実装（欠損やデータ不足時は None を返す仕様）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターンを一括クエリで計算（horizons の検証あり）。
    - calc_ic / rank / factor_summary: IC（Spearman 相関）計算、ランク付け（同順位は平均ランク）、統計要約を実装。
  - src/kabusys/research/__init__.py を通じて公開 API を整備。

- ニュース NLP（OpenAI 連携）
  - src/kabusys/ai/news_nlp.py
    - raw_news テーブルを集約して OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルに書き込む機能を実装。
    - バッチ処理（最大 _BATCH_SIZE=20）、トークン肥大対策（記事数・文字数制限）、429/ネットワーク/5xx の指数バックオフリトライ (_MAX_RETRIES) を実装。
    - レスポンス検証、スコア ±1.0 クリップ、部分失敗時にも既存スコアを保護する更新（特定 code に対する削除→挿入）方針を採用。
    - calc_news_window: target_date に基づくニュース収集ウィンドウ（JST→UTC 変換）を提供。
    - API キー未設定時は ValueError を発生させる挙動を定義。

- モニタリング DB 初期化ユーティリティ
  - src/kabusys/monitoring/monitoring_db.py への参照（init_monitoring_db の呼び出しにより、monitoring テーブル群の存在を保証）。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定。権限不足等は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアに固定する機能を追加（None の場合は無処理）。権限不足は警告ログでスキップ。

- CLI ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ。しきい値（PASS/FAIL 判定）を定義。
    - --from / --to / --db オプション対応。PAPER_TRADING_SQLITE_PATH 環境変数からの参照も可能。
    - DB/Tables が存在しない場合のフォールバック処理（OperationalError 捕捉）を実装。

Changed
- （初回リリースのため該当なし）

Fixed / Improvements
- .env パーサーの堅牢化（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等）。
- DuckDB / SQLite クエリでデータ不足時に None を返す防御的実装（ファクター計算・レイテンシ計算など）。
- ランキング関数における ties 処理を平均ランクで行い、浮動小数丸め誤差対策に round(..., 12) を導入。
- process_priority と set_cpu_affinity は権限不足・未対応プラットフォームで例外を握りつぶして警告を出すように改善（フェイルセーフ）。
- position_sizing の aggregate スケーリングは残差配分ロジックを持ち、lot_size 単位で再配分することで利用可能現金の有効活用を試みる。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キー（OPENAI_API_KEY）は環境変数経由で安全に供給することを想定。キー未設定時は処理を中止して明示的なエラーを返す仕様。

使用上の注意 / 環境変数
- KABUSYS_ENV: development | paper_trading | live（必須、Settings.env で検証）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。不正値はデフォルトにフォールバック。
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード（instant|partial|never|reject）。不正値は ValueError。
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）。
- SQLITE_PATH / DUCKDB_PATH: 監視・解析用 DB パス（デフォルト data/monitoring.db, data/kabusys.duckdb）。
- OPENAI_API_KEY: news_nlp の API キー（必須でない場合でも、score_news を呼ぶときは指定が必要）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化。

実行例
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または環境変数 PAPER_TRADING_SQLITE_PATH を指定して実行

補足
- 多くのモジュールは DuckDB / SQLite のテーブル構造（prices_daily, raw_financials, raw_news, trade_logs, system_status, risk_logs, ai_scores 等）を前提としており、DB スキーマに依存する処理が含まれます。実運用前に DB スキーマ初期化（init_monitoring_db 等）やマスタデータの準備が必要です。
- 各関数は「データ不足時は None を返す」「外部 API エラーはログを出してスキップする」等、フェイルセーフを優先する設計方針が採られています。

もし CHANGELOG を別バージョン単位で分割したい、あるいは各ファイルごとのより詳細な変更点（関数単位）を追記したい場合は、対象の範囲を指定して指示してください。