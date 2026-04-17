Keep a Changelog 形式でコードベースの内容から推測して CHANGELOG.md を作成しました。必要に応じて日付やバージョンを調整してください。

---
# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 初期リリース相当の機能群を追加。
  - 実行エンジン起動スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ完全分離して記録。
    - 停止フラグファイル (data/stop_requested.flag) を監視して安全にシャットダウン可能。実行 PID を data/execution.pid に記録。
  - 監視（Monitoring）起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境設定にかかわらず本番の sqlite_path を利用して監視テーブルを初期化・更新。
  - 設定 / 環境変数管理
    - config.py: .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。
    - .env の読み込み順序は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - 環境変数パースの改善（export プレフィックス、シングル/ダブルクォート対応、インラインエスケープ、コメント処理）。
    - Settings クラスに各種設定プロパティを追加・検証:
      - DB パス: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
      - Paper Trading 関連: PAPER_FILL_MODE, paper_sqlite_path
      - 監視閾値: CPU/MEM/DISK の割合設定
      - KABUSYS_ENV 検証（development / paper_trading / live）
      - ログレベル検証
      - PID / kill flag 関連設定
  - ポートフォリオ構築ライブラリ（純粋関数）
    - portfolio_builder: 候補選定(select_candidates)、等分配(calc_equal_weights)、スコア加重(calc_score_weights) を実装。
    - risk_adjustment: セクター集中制限を行う apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - position_sizing: 発注株数決定 calc_position_sizes を実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer の考慮）。
  - リサーチ / ファクター計算
    - research/factor_research.py:
      - モメンタム (mom_1m/mom_3m/mom_6m, MA200 乖離)、ボラティリティ (ATR20, 相対ATR, 平均売買代金, 出来高比)、バリュー (PER, ROE) の計算関数を実装。
      - DuckDB 接続を受けて SQL + Python で計算（prices_daily / raw_financials を参照）。
    - research/feature_exploration.py:
      - 将来リターン算出(calc_forward_returns)、IC（スピアマンランク相関）計算(calc_ic)、ファクター統計サマリー(factor_summary)、ランク関数(rank) を実装。
      - 標準ライブラリのみでの実装を志向。
    - research パッケージのエクスポートを調整（zscore_normalize 統合など）。
  - ツール
    - tools/paper_verification_report.py:
      - Paper Trading の検証レポート生成スクリプトを追加。期間指定 (--from/--to) と DB パス指定 (--db) に対応。
      - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を出力（閾値定義あり）。
  - AI ニュース NLP
    - ai/news_nlp.py:
      - raw_news テーブルと news_symbols を集約して OpenAI API（gpt-4o-mini）で銘柄単位にセンチメントスコアを算出、ai_scores テーブルへ書き込む処理を実装。
      - バッチ処理、トークン肥大化対策（最大記事数・最大文字数）、リトライ（指数バックオフ）、レスポンス検証、スコアの ±1 クリップなどを想定。
  - ユーティリティ
    - utils/process_priority.py:
      - Windows と POSIX（Linux/Mac/FreeBSD）でのプロセス優先度設定(set_process_priority) を抽象化して実装。psutil ベース。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
      - 権限不足や非対応環境時は警告を出力して安全にスキップ。
  - パッケージ情報
    - __init__.py に __version__ = "0.1.0" を追加。

### Changed
- 環境変数読み込みの挙動を安全化:
  - OS 環境変数を保護する protected キー概念を導入し、.env.local で OS 環境を誤って上書きしないようにした。
- DB 初期化の冪等性確保:
  - run_execution と run_monitoring 起動時に監視用テーブル初期化(init_monitoring_db) を実行しておくことで、監視テーブルが存在しない場合でも安全に起動できるように。

### Fixed / Hardened
- 環境変数パースの堅牢化:
  - クォートとエスケープ処理、export プレフィックス対応、コメントの扱いを改善。無効行は無視。
- モジュール間のデータ分離:
  - Paper Trading 実行時は paper_sqlite_path を使用して本番 DB からロジック・データを分離。
- 実行・監視の安全シャットダウン:
  - stop flag の存在チェックと例外/KeyboardInterrupt のハンドリングを追加。
- ポジションサイズ計算の安全措置:
  - price が不正（0/None）な場合のスキップ、lot_size による丸め、available_cash による aggregate スケールダウンを実装。
- research / factor 計算での NULL / データ不足時の扱いを明確化（十分な履歴がない場合は None を返す）。

### Known issues / Notes / TODO
- ai/news_nlp.py は大部分が実装されているが、提供されたスニペットの末尾が途切れており（コード末尾が不完全）、実運用前に残り処理（記事フェッチ関数、API 呼び出しループ、DB 書き込み処理など）の確認・完成が必要。
- portfolio/risk_adjustment.apply_sector_cap 内に price の欠損時に過少見積りされる注釈（TODO）があり、将来的に前日終値や取得原価でのフォールバック検討が必要。
- position_sizing の lot_size は現在全銘柄共通（100）を前提。将来的には銘柄別 lot_map への対応が想定されている。
- process_priority の優先度変更は環境や権限に依存して失敗する可能性があり、その場合は警告を出して処理を継続する設計。
- DuckDB の executemany に関する注意（ai モジュールのコメント）: 空パラメータでの実行を避ける必要あり。
- paper_verification_report は SQLite のテーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値でレポートを作成するが、データ欠損時の表示は N/A 表示となる。

---

## [0.1.0] - 2026-04-17
初回公開リリース（上記 Added の機能群）。  
主に自動売買の実行基盤（ExecutionEngine 起動、監視ループ、環境設定、安全停止）、ポートフォリオ構築ロジック、研究用ファクター計算、Paper Trading の検証ツール、OpenAI を用いたニュース NLP の下地、および実運用向けの堅牢化を含む。

- See also: ソースコード内のドキュメント（各モジュールの docstring）を参照してください。

---

追記（運用メモ）
- 重要な環境変数:
  - KABUSYS_ENV: development | paper_trading | live
  - OPENAI_API_KEY: news_nlp の呼び出しに必要
  - PAPER_FILL_MODE: instant | partial | never | reject
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（整数）
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB パス
  - KILL_FLAG_PATH / PID_FILE_PATH: 監視・停止関連
- 停止フラグ: data/stop_requested.flag を作成すると監視/実行が安全停止します（プロジェクトルートを基準に data 配下）。

-- End of CHANGELOG.md --