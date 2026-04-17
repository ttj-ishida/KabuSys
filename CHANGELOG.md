# Changelog

すべての非互換性のある変更は明記します。  
このファイルは Keep a Changelog の形式に従います。  

参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- 現時点での未リリース変更はありません（初回リリースを作成）。

## [0.1.0] - 2026-04-17

初回リリース（コードベースから推測して作成）。

### Added
- 全体
  - プロジェクトの初期バージョンを追加。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - 環境変数および .env ファイルの読み込み・管理を行う `kabusys.config.Settings` を追加。
    - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - OS 環境変数を保護しつつ `.env` / `.env.local` を読み込む仕組み。
    - 各種プロパティ（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、環境判定フラグ等）と入力検証を提供。
    - `PAPER_FILL_MODE`（paper trading の振る舞い）など、特定環境向けのバリデーションを実装。

- 設定関連 CLI
  - 対話的ウィザード `kabusys.config_setup` を追加。
    - `.env` の初期作成・更新を支援する対話式プロンプト、既存値の読み込み、シークレットマスク表示、保存機能を提供。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在チェック）、
      config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行 / 監視ランナー
  - `kabusys.run_execution` を追加。
    - 起動時にプロセス優先度を「high」に設定（可能な場合）。
    - 環境に応じて paper_trading 用の専用 SQLite DB を使用（分離）。
    - ブローカークライアントを `BrokerClientFactory` で生成（paper_trading 時は MockBrokerClient 想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、`ExecutionEngine` をスレッドで実行。停止フラグ（data/stop_requested.flag）を監視して安全に停止。
    - PID ファイルの取り扱いを想定（data/execution.pid）。
  - `kabusys.run_monitoring` を追加。
    - SystemMonitor を初期化してポーリングループを実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する挙動。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。

- モニタリング / DB
  - 監視テーブル初期化ユーティリティ `init_monitoring_db` を使用して、起動時に監視用テーブルの存在を保証（冪等処理）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナルの候補選定（スコア降順、タイブレークに signal_rank を使用）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights、全スコアが0なら等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する `apply_sector_cap`（既存保有のエクスポージャ計算、売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - 市場レジームにより投下資金乗数を返す `calc_regime_multiplier`（"bull" / "neutral" / "bear" マップ、未知レジームは警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - position sizing の実装（risk_based / equal / score の配分方式）。
    - 単元株（lot_size）での丸め、1 銘柄上限や aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した保守的見積り、
      スケーリング後の残差処理（fractional remainder に基づく追加配分）を実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`
    - DuckDB 接続を受けてファクター（Momentum, Volatility, Value, Liquidity 等）の計算を行う関数群（例: calc_momentum, calc_volatility）。
    - 移動平均やATR、各種ラグ計算を SQL（DuckDB）で実装し、DataFrame 的な集計を行う設計。

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用の検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定（閾値はソース内に定義）。
    - 日付範囲フィルタ、DB パスの指定（コマンドラインオプション／環境変数利用）に対応。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX 系（nice 値）に対応し、失敗時は警告を出してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（例外時は警告してスキップ）。

- パッケージ API
  - `kabusys.portfolio` の __init__ による関数の再エクスポートを追加（外部 API を整理）。

### Changed
- 初期リリースのため、既存コードの整理・責務分離を実施（設定読み込み、CLI、エンジン起動、監視、ポートフォリオ計算、ファクター計算をモジュール化）。

### Fixed
- 起動スクリプトと各コンポーネントでの障害耐性を強化（例: run_monitoring の loop 内で check_once の例外をキャッチしてログを残して継続、プロセス優先度設定時の権限不足を警告で扱う）。

### Notes / Implementation details（コードから推測）
- .env パーサは引用符付き値、export プレフィックス、インラインコメントの扱い（クォート付きではバックスラッシュエスケープを処理、非クォートでは # 前に空白がある場合をコメントとみなす）に細かく対応しているため、一般的な .env フォーマットに柔軟に対応する想定。
- validate_config は PyYAML がインストールされている場合に限り config/*.yaml の中身をパース検証する実装。未インストール時は警告を出す。
- ExecutionEngine の起動はスレッドで行い、外部の停止フラグにより安全に停止できる設計。paper_trading は本番 DB と完全に分離される。
- position sizing の aggregate cap スケーリングや remainder による調整、lot_size 丸め等は実運用を想定した実装になっている（手数料・スリッページを cost_buffer で見積もる）。
- Monitoring は production sqlite_path を常に使用する（環境に依存しない監視設計）。

---

（この CHANGELOG は与えられたコードからの推測に基づいて作成されています。実際のリリースノート作成時はコミット履歴・リリース要求に基づいて調整してください。）