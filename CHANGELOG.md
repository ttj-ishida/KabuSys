# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

### Added
- research.factor_research モジュールを追加（モメンタム等のファクター計算の枠組みを実装開始）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して各種ファクターを計算する設計。
- 細かな TODO / 拡張点をコード内に明示（価格フォールバック、lot_size の銘柄別対応、P95 計算等）。

### Changed
- なし（開発中の改善 / 未リリースの変更点をここに追加してください）。

### Fixed
- なし

---

## [0.1.0] - 2026-04-19

Initial release — 基本機能を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 設定・環境管理
  - Settings クラスによる環境変数ラッパー（`src/kabusys/config.py`）。
    - 必須変数取得時の検証（未設定時に ValueError）。
    - 各種パス（DuckDB/SQLite/紙トレードDB 等）、ログレベル、環境モード（development/paper_trading/live）判定、paper_fill_mode の妥当性チェックを提供。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み機能を実装。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースはクォート、エスケープ、インラインコメント等に対応。

- 環境セットアップ / 検証ツール
  - 対話式 .env 作成ウィザード（`src/kabusys/config_setup.py`）。
    - 対話入力、既存 .env 読み込み、.env 書き出し機能。
  - 設定検証 CLI（`src/kabusys/validate_config.py`）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス確認、config/*.yaml の存在と（PyYAML がある場合は）パース検証、live 環境向けガードチェックを実装。
    - --strict オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（`src/kabusys/run_execution.py`）。
    - プロセス優先度設定（high）を起動時に行う。
    - 環境に応じた DB 分離（paper_trading モードでは paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとセッション実行の管理（停止フラグ / PID ファイル連携）。
  - 監視ループ起動スクリプト（`src/kabusys/run_monitoring.py`）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。0 以下や不正値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を参照し監視テーブルを初期化。
    - 停止フラグ検知、エラー時のロギング、KeyboardInterrupt 対応を実装。

- モニタリング基盤
  - 監視データベース初期化呼び出し箇所を各スクリプトで保証（init_monitoring_db の呼び出し）。

- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティ（`src/kabusys/utils/logging_setup.py`）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - ログレベルとログディレクトリの解決順序を実装。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（`src/kabusys/utils/process_priority.py`）。
    - Windows / POSIX（Linux, macOS 等）差分を吸収。優先度(high/normal/low) 設定、CPU affinity 固定をサポート。権限不足や未対応 OS は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（`src/kabusys/portfolio/portfolio_builder.py`）。
    - シグナルのスコア降順ソート、等金額配分、スコア加重配分（全銘柄スコアが 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（`src/kabusys/portfolio/risk_adjustment.py`）。
    - セクター上限チェック（既存ポジション評価から当日売却予定を除外可能）。
    - レジームに応じた投下資金乗数（bull/neutral/bear をマップし、未知レジームはフォールバック）。
    - 既知の注意点（価格欠損時の過少見積り等）を TODO コメントで明示。
  - ポジションサイズ計算（`src/kabusys/portfolio/position_sizing.py`）。
    - risk_based / equal / score の配分方式を実装。単元（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金超過時のスケーリング）および端数配分のロジックを実装。
    - cost_buffer を用いた保守的なコスト見積り機構を備える。
    - 将来的な拡張点（銘柄別 lot_size）をコメントに記載。

- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプト（`src/kabusys/tools/paper_verification_report.py`）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ (avg/max/P95) 等を集計し、PASS/FAIL 判定を出力。
    - P95 は独自実装で計算。DB パスはコマンドライン --db / 環境変数で指定可能。
    - 判定基準（閾値）をソース内で定義（稼働率 99%, 成立率 90% 等）。

### Changed
- なし（初版公開のため該当なし）。

### Fixed
- なし（初版公開のため該当なし）。

### Security
- なし

---

注記 / 既知の制限・今後の作業
- research.factor_research はファクター計算の骨格があるが実装の途中で終端している箇所があり、追加実装／テストが必要。
- position_sizing と risk_adjustment 内に将来的な拡張（銘柄別 lot_size、価格フォールバック等）の TODO コメントあり。
- 一部モジュール（例: execution.* の細部、monitoring.monitoring_db / system_monitor）の実装ファイルは本差分に含まれていないが、スクリプトはそれらを参照して統合する構成になっている（リポジトリ全体での結合テスト推奨）。
- .env の自動読み込みはデフォルトで有効。自動ロードを望まない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

開発者向けヒント
- 起動スクリプトはまず setup_logging() と set_process_priority("high") を呼ぶことで、ログ環境とプロセス優先度を統一しています。デバッグ時は LOG_LEVEL や LOG_DIR を使って挙動を調整してください。
- Paper Trading と Live の DB は意図的に分離されています。Paper モードでの誤って本番 DB を操作するリスクは低い設計です（ただし設定ミスに注意）。

（この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際の変更履歴やコミット履歴に基づく差分が必要な場合は、git log 等の履歴情報を提供してください。）