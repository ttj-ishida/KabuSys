# Changelog

すべての変更は "Keep a Changelog" の形式に従い、重大度順に記載しています。  
日付はリリース日時（推定）です。

## [0.1.0] - 2026-04-24 (initial release)

### 追加 (Added)
- 基本アプリケーションメタ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - ブローカークライアント生成（BrokerClientFactory）／OrderRepository／OrderManager／RiskManager／Reconciler の組み立てを行い、スレッドでエンジンを実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）により安全に停止可能。

  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - SystemMonitor を起動するポーリングループ。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用の sqlite_path を使用する（監視データを一元化）。
    - 停止フラグの検知でループを終了し、DB 接続を正しくクローズ。

- 設定管理
  - 環境設定モジュール: `src/kabusys/config.py`
    - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み（`.env` → `.env.local`、OS 環境変数を保護）。
    - .env 行パーサは `export` プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等に対応。
    - Settings クラスにより、各種設定（J-Quants トークン、kabu API、DB パス、paper_fill_mode、PID/kill flag パス、監視閾値、環境名・ログレベル検証など）をプロパティとして提供。
    - `paper_fill_mode` の妥当性チェック（"instant"|"partial"|"never"|"reject"）や `KABUSYS_ENV` / `LOG_LEVEL` の検証ロジックを実装。

- 設定関連 CLI
  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パス親ディレクトリの存在確認、`config/*.yaml` の存在および（PyYAML があれば）パース検証を実施。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（live）環境向けの追加ガード（LINE トークン未設定、KILL_FLAG_CLEAR_ON_START の注意喚起など）。

  - 環境設定ウィザード: `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を初期作成 / 更新するユーティリティ。
    - 複数の設定項目（KABUSYS_ENV、トークン/パスワード、DB パス、LOG_LEVEL、Kill Switch 設定など）をサポート。シークレット項目はマスク表示。
    - 既存 .env 読み込み、Enter で既存値/デフォルトを再利用。最終確認後に .env を書き込み。

- ロギング・プロセス管理ユーティリティ
  - ロギング設定ユーティリティ: `src/kabusys/utils/logging_setup.py`
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、既定 30 日保持）を設定。
    - ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト の順に解決。
    - ログディレクトリ（引数 > LOG_DIR > "logs/"）を作成し、作成失敗時はファイル出力をスキップしてコンソールのみで継続。StreamHandler は stdout を使用。

  - プロセス優先度 / CPU affinity ユーティリティ: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差を吸収してプロセス優先度（"high"/"normal"/"low"）を設定。
    - CPU affinity を最初の N コアに固定するヘルパーを提供。
    - psutil を使用し、権限不足や未対応 OS の場合は警告を出力してスキップ。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - 候補選定・重み付け: `src/kabusys/portfolio/portfolio_builder.py`
    - select_candidates: スコア降順、同点は signal_rank 小さい方を優先して上位 N 件を返却。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化による配分。全スコアが 0 の場合は等分にフォールバックして警告。

  - セクター集中制限・レジーム調整: `src/kabusys/portfolio/risk_adjustment.py`
    - apply_sector_cap: 既存ポジションのセクター比率が閾値を超える場合、そのセクターの新規候補を除外。`unknown` セクターは除外対象外。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に対して乗数を返却（フォールバックは 1.0）。未登録レジームは警告。

  - 株数計算・リスク制限・単元丸め: `src/kabusys/portfolio/position_sizing.py`
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。
    - 単元（lot_size）で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に対するスケールダウンと残差配分ロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を加味して保守的に算出。

- Paper Trading 検証レポート
  - ツール: `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）からデータを集計し、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算して標準出力にレポートを生成。
    - 判定基準（閾値）を定義:
      - 稼働率 >= 99.0%
      - 注文成立率（fill） >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付範囲フィルタ、DB 存在チェック、SQLite のテーブル欠如に対する耐性（OperationalError を補足し N/A や 0 を出力）。

- 研究用ファクター計算（部分実装）
  - `src/kabusys/research/factor_research.py` にモメンタム計算や ATR、流動性等の指標計算の骨格を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。ファイルは途中までの実装（未完）を含む。

- パッケージエクスポート
  - `src/kabusys/portfolio/__init__.py` により主要関数群を再エクスポートして外部利用を容易に。

### 変更 (Changed)
- なし（初期リリースに相当するため新規追加中心）。

### 修正 (Fixed)
- なし（初期リリース）。

### 注意事項 / 補足
- config モジュールは自動で .env を読み込むが、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動ロードを無効化できる（テスト時に有用）。
- run_monitoring は監視用 DB に対して本番 sqlite_path を使用する仕様（意図的な設計）。運用時は監視 DB の配置場所に注意。
- process_priority / cpu_affinity の設定は OS 権限に依存し、権限不足時は警告を出して処理を継続する。
- 一部の実装（research/factor_research の続きや TODO コメント）は継続作業が必要。

--- 

この CHANGELOG は、提供されたソースコードから推測できる機能追加・設計方針を基に作成しています。追加のコミット履歴や意図がある場合は、それに合わせて更新してください。