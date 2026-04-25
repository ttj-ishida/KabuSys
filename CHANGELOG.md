# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルではコードベースに含まれる主要な機能追加・改善点・既知の制約を、現時点のソースコードから推測してまとめています。

## [0.1.0] - 2026-04-25

初回リリース（コードベースのスナップショットに基づく主要機能群）。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - CLI・ユーティリティ群、ポートフォリオ構成ロジック、実行・監視用スクリプト、レポート生成ツールなど基盤機能を実装。

- 実行／監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用して本番データと分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（MockBrokerClient の切替想定）。
    - ExecutionEngine をバックグラウンドスレッドで実行し、 data/stop_requested.flag による停止検知対応。
    - 起動時にプロセス優先度を "high" に設定し、pid ファイルを管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は実行環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt を扱う。

- 設定管理
  - config.py: 環境変数/.env ロード・設定取得のユーティリティを実装。
    - .env 自動読み込み機能（.env / .env.local）を提供。OS 環境変数は保護（上書き防止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 行パーサは export のサポート、クォート内のエスケープ、インラインコメントの扱い等を考慮。
    - 各種設定プロパティ（DB パス、PID/kill flag パス、しきい値、環境判定、paper_trading 関連設定など）を提供。
    - PAPER_FILL_MODE の入力検証（有効値: "instant"|"partial"|"never"|"reject"）。

  - config_setup.py: 対話式 .env 作成ウィザードを実装。
    - 各種設定項目の説明・デフォルト値・シークレット入力対応。
    - 既存 .env の読み込みと上書き、最終確認後に .env を生成。

  - validate_config.py: 設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース検証（PyYAML がない場合はスキップ）を実行。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング／プロセス管理
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL による設定上書き、ファイルハンドラ作成失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定ユーティリティを追加。
    - Windows (psutil の priority クラス) / POSIX (nice 値) を吸収。
    - CPU affinity 設定ユーティリティも提供（set_cpu_affinity）。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルをスコア降順で選抜。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等金額配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するフィルタを提供（売却予定銘柄の除外対応、"unknown" セクターは制限除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method (risk_based / equal / score) に応じた発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積り、残差分配の安定化ロジックを実装。

- リサーチ
  - research/factor_research.py: ファクター計算モジュール（Momentum/Value/Volatility/Liquidity）を追加（DuckDB 接続で prices_daily / raw_financials を参照する設計）。
    - モメンタムのパラメータ・スキャン範囲等が定義され、calc_momentum 関数が用意されている（ソースは途中まで実装されている箇所あり）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計し、稼働率、注文成立率、送信率、P95 レイテンシ等を算出。
    - 閾値を元に PASS/FAIL を判定し標準出力でレポートを出力。
    - コマンドラインで期間フィルタ (--from / --to) と DB パス (--db) を指定可能。

### 変更 (Changed)
- なし（初回リリースのため該当なし。ただし各モジュールで実装上の設計コメント・TODO を残しています）。

### 修正 (Fixed)
- なし（初回バージョンとして既知の改善点/注意点をコード内コメントで記載）。

### 廃止 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- なし（ただしシークレット値を .env に保存する設計であるため、.env を絶対に Git にコミットしない旨を config_setup.py に明示）。

---

## 注意事項 / 既知の制約（ソースコードから推測）
- factor_research.py は calc_momentum の実装が途中で切れている箇所があり、完全実装されていない可能性があります（追加実装が必要）。
- portfolio/risk_adjustment.py の apply_sector_cap は price が欠損（0.0）の場合、エクスポージャーが過少評価されうる旨の TODO コメントあり。将来的にフォールバック価格（前日終値 等）を導入することが推奨されています。
- process_priority および set_cpu_affinity は psutil の権限・OS サポートに依存。権限不足や未サポート OS では警告を出してスキップします。
- .env 自動読み込みロジックはプロジェクトルートの特定（.git または pyproject.toml）に依存するため、配布後や特定の配置では自動ローディングを無効にする必要がある場合があります（KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能）。
- PAPER_FILL_MODE の不正値は ValueError を送出するため、環境変数設定時は注意が必要。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力をスキップして stdout のみで継続します。
- validate_config の YAML 検証は PyYAML がインストールされていない環境ではスキップされます（警告出力）。

---

もし特定の変更点（コミットや差分）に基づいたより詳細な CHANGELOG を希望される場合は、差分情報（git diff / コミットログ）を提供してください。それに基づきバージョンごとの変更点を時系列で整理します。