# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

## [0.1.0] - 2026-04-17

初回公開リリース。

### Added（追加）
- 基本パッケージとバージョン情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 実行用エントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止はプロジェクト内 `data/stop_requested.flag` ファイルで制御。
    - 監視用 DB は環境にかかわらず本番向け `sqlite_path` を使用。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB (`data/paper_trading.db` または環境変数による上書き) に完全分離して記録。
    - 起動時にプロセス優先度を "high" に設定。
    - エンジンの停止は `data/stop_requested.flag` により制御。PID 保存先を指定（デフォルト `data/execution.pid`）。

- 設定 / 環境変数管理
  - config.py
    - プロジェクトルート探索（.git または pyproject.toml）に基づく .env 自動読み込み機能を追加（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env の詳細なパース実装（export プレフィックス、クォート内のエスケープ、インラインコメント扱い等に対応）。
    - Settings クラスを追加し、環境変数をプロパティで安全に取得。主要プロパティ:
      - J-Quants / kabu API トークン・パスワード
      - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
      - PID / KILL フラグ関連パス
      - 各種しきい値（CPU/MEM/DISK）
      - KABUSYS_ENV / LOG_LEVEL の検証
      - PAPER_FILL_MODE の検証（許可値: "instant" | "partial" | "never" | "reject"）
    - `settings` のインスタンスをモジュールレベルで提供。

- 設定確認・ウィザード
  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスや YAML ファイルの存在・パースチェック、KABUSYS_ENV=live 時の追加ガードを実装。
    - `--strict` オプションで警告も失敗扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - シークレット項目は表示時にマスク。デフォルト値・選択肢・説明付き。
    - 作成/更新は安全に .env を書き出す機能を提供。

- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄除外、"unknown" セクターには制限を適用しない挙動）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull", "neutral", "bear" をサポート、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、1 銘柄上限・集約上限（available_cash）を考慮、cost_buffer による保守的見積り、aggregate キャップ超過時のスケーリングと残差処理（lot 単位での再配分）を実装。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily テーブルを用いたモメンタム / ボラティリティ系ファクター計算関数を追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR 20 日、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - 設計上、DuckDB SQL を用いた高速集計と欠測データに対する堅牢性を考慮。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite ログから検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ (avg/max/P95)、リスク却下数。
    - デフォルトしきい値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ (--from / --to)、DB 指定 (--db) に対応。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加。
    - Windows と POSIX (Linux, macOS, FreeBSD) の差異を吸収して p.nice()/HIGH_PRIORITY_CLASS を使用。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足や未サポート環境では警告を出して安全にスキップ。

- 監視 DB 初期化ユーティリティの呼び出し
  - run_monitoring / run_execution の起動時に監視用テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。

### Changed（変更）
- .env の自動読み込みロジック
  - プロジェクトルート探索を __file__ の親階層から行うようにして、CWD に依存しない自動ロードを実現。
  - OS 環境変数は保護 (protected) され `.env.local` は上書き可能な挙動とした。

### Fixed（修正 / 安全性改善）
- 環境変数のパース改善
  - クォート内のエスケープ文字とインラインコメントの扱いを適切に処理するよう修正（以前の単純パースで誤読する可能性を低減）。
- 停止/起動の安全ガード
  - run_execution 起動時に停止フラグが既に立っている場合は起動を行わないようにし、誤起動のリスクを軽減。
- 実行時例外の安全ハンドリング
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループ継続するように例外をキャッチしてログ出力するようにした。

### Notes（注意点 / 既知の挙動）
- 監視 DB の使用
  - run_monitoring は「環境にかかわらず」Settings.sqlite_path（本番監視 DB）を使用します。監視データを環境別に分離したい場合は設定の見直しが必要です。
- Paper Trading の DB 分離
  - run_execution は `settings.is_paper`（KABUSYS_ENV=paper_trading） 時に `PAPER_TRADING_SQLITE_PATH` を用いるため、本番 DB と完全分離されます。
- .env 自動ロードの無効化
  - テストなどで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境変数の必須項目
  - 実行に必須の環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。未設定時は Settings のプロパティアクセスで ValueError が発生します。
- PAPER_FILL_MODE の妥当性チェック
  - `PAPER_FILL_MODE` は "instant", "partial", "never", "reject" のいずれかでなければなりません。誤った値は ValueError を送出します。
- process_priority / cpu_affinity の動作
  - 権限不足（一般ユーザ）やプラットフォーム依存のため変更が適用できないケースがあります。その場合はログに警告を出してスキップします。

---

今後の予定（非 exhaustive）
- factor_research の追加ファクター実装（Value, Liquidity 等）および統合テスト
- 監視・実行のさらなる堅牢化（Transient エラー時のリトライ、メトリクスの拡充）
- 銘柄別単元 (lot_size) 情報を銘柄マスタに持たせる拡張

もし特定の変更点をより詳しく記載してほしい箇所があれば教えてください。