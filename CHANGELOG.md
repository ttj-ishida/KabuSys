CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
※ 日付はリリース日を想定しています。

[0.1.0] - 2026-04-16
--------------------

Added
- 基本アプリケーション初回実装を追加。
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン情報を追加 (__version__ = "0.1.0")。
  - 実行エントリ
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離。
      - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション起動を実装。
      - 停止制御: data/stop_requested.flag を検知して安全停止。PID ファイル (data/execution.pid) を管理。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグ (data/stop_requested.flag) による終了、例外時のロギング保護を実装。
  - 設定管理
    - config.py: 環境変数/.env ファイルの自動読み込み機能を実装。
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env/.env.local の読み込み。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - export 句や引用符付き値、行内コメント等に対応したパーサを実装。
      - Settings クラスで各種設定値（DB パス、API キー、監視しきい値、環境モードなど）をプロパティ経由で厳密に取得・検証。
  - データベース / 分析基盤
    - DuckDB と SQLite の併用を前提とした設計を導入（各モジュールで受け取る形の API）。
    - 監視テーブル初期化ユーティリティ（init_monitoring_db）を起動時に呼び出し、冪等にテーブル存在を保証。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights) を実装。スコア全ゼロ時のフォールバックあり。
    - portfolio/risk_adjustment.py
      - セクター集中上限の適用(apply_sector_cap)、市場レジームに基づく乗数(calc_regime_multiplier) を実装。
      - 未知のセクター／未知レジームに対するフォールバック動作を実装（"unknown" 処理、ログ警告）。
    - portfolio/position_sizing.py
      - position sizing ロジックを実装（risk_based / equal / score）。
      - lot_size（単元株）丸め、per-position 上限、aggregate cap によるスケーリング、残差配分アルゴリズム（fractional remainder による lot 単位追加）を導入。
      - cost_buffer による保守的なコスト見積り対応。
  - 研究機能（Research）
    - research/factor_research.py
      - Momentum / Volatility / Value ファクター計算を DuckDB SQL ベースで実装（ma200, mom_1m/3m/6m, atr_20 等）。
    - research/feature_exploration.py
      - 将来リターン計算(calc_forward_returns)、IC（calc_ic）、統計サマリ(factor_summary)、順位付け(rank) を実装。外部ライブラリに依存せずに標準ライブラリで完結。
    - research/__init__.py に各公開 API をまとめてエクスポート。
  - AI / ニュース NLP（設計と大部分の実装）
    - ai/news_nlp.py
      - raw_news を OpenAI（gpt-4o-mini）に送って銘柄別センチメントを ai_scores テーブルへ書き込む設計を実装。
      - バッチサイズ、トークン膨張対策（記事数・文字数制限）、スコアクリップ（±1.0）、リトライ（指数バックオフ）等の堅牢な処理フローを導入。
      - ニュース集計ウィンドウ計算（JST→UTC 変換）を提供（calc_news_window）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を解析し、PASS/FAIL 判定を出力。
      - デフォルトの DB パスは data/paper_trading.db。--from/--to/--db オプションに対応。
      - レポート生成時の堅牢性確保（テーブル欠損時の例外吸収）。
  - ユーティリティ
    - utils/process_priority.py
      - Windows / POSIX を吸収したプロセス優先度設定を実装（set_process_priority）。
      - CPU affinity 設定関数 set_cpu_affinity を追加。psutil の権限不足等は警告ログでスキップ。

Changed
- 設計/実装方針を明確化
  - Research / Portfolio / Execution の各モジュールは「DB 参照を受け取る」「純粋関数は副作用なし」を基本方針として実装。
  - Paper Trading と本番 DB の明確な分離。run_execution.py は settings.is_paper により専用 SQLite を使用。

Fixed / Improved
- 設定検証の強化
  - Settings の各プロパティで値検証を実施（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）。
- 実行時の堅牢性向上
  - run_monitoring.py のポーリング間隔取得(_get_poll_interval) は不正な値（<=0 や非整数）を検出してデフォルトにフォールバック、警告ログを出力。
  - run_monitoring.py / run_execution.py のループで停止フラグ検出時に安全に終了する処理を追加。
  - process_priority や cpu_affinity は権限不足や未対応プラットフォーム時に例外を握り潰して警告ログを出すことで起動失敗を防止。
- SQL/集計ロジックの堅牢化
  - research.calc_volatility の true_range 計算で high/low/prev_close の NULL 値伝播を明示的に扱い、ATR の集計カウントを正確化。
  - paper_verification_report の集計・P95 計算を実装し、対象期間フィルタを安全に組み立て。

Known issues / Notes / TODO
- ai/news_nlp.py の article aggregation 部分（関数 score_news 内）がソース末尾で切れており（ファイル末尾が途中で終わっている）、完全な実装・統合テストが必要です。現状では API 呼び出し以降（記事取得 → バッチ化 → 書き込み）の一部が未完です。
- position_sizing.py
  - 将来的に銘柄別 lot_size を導入する意図の TODO コメントあり（現在は単一 lot_size を想定）。
- risk_adjustment.apply_sector_cap
  - price が欠損（0.0）である場合にエクスポージャーが過少評価される注記あり。前日終値や取得原価などのフォールバック実装が検討課題。
- DuckDB executemany の制約を考慮した注意事項やエラーハンドリング（ai/news_nlp の設計上の注意）あり。
- 監視 (run_monitoring.py) は設計上「環境にかかわらず本番 sqlite_path を使用」する点に注意。Paper Trading の監視を分離したい場合は設定を見直してください。

Environment / Configuration notes
- 新規に使用される / 影響を受ける主要な環境変数:
  - KABUSYS_ENV (development | paper_trading | live)
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
  - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper trading 用 DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper trading の fill モード: instant | partial | never | reject）
  - DUCKDB_PATH（DuckDB のパス、デフォルト: data/kabusys.duckdb）
  - OPENAI_API_KEY（ai/news_nlp の API キー）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（=1 で .env 自動ロードを無効化）
  - LOG_LEVEL（ログレベル: DEBUG/INFO/...）
- .env ファイルの読み込み順序:
  - OS 環境変数 > .env.local > .env。OS 側の既存キーは protected され上書きされません。

Security
- OpenAI API キーや各種秘密情報は環境変数（または .env）で管理する設計。Settings は必須キー未設定時に ValueError を投げるため、起動前に適切に環境を用意してください。

Unreleased
- 今後の予定:
  - ai/news_nlp の未完部分の実装と統合テスト。
  - 銘柄別 lot_size 対応、価格フォールバック実装、より細かい監視/アラート機能。
  - 実運用に向けたバックテスト / スモークテストの追加・CI 統合。

--------------------------------------------------------------------
履歴は上記の通りです。必要であれば各変更点をさらに細分化してコミットハッシュや関連テストケース／使用例を追記します。