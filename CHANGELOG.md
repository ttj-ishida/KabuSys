# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ に合わせています。

## [0.1.0] - 2026-04-19

初回リリース

### Added
- 全体
  - 初期パッケージを追加。ライブラリ名: KabuSys（日本株自動売買システム）。
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数/`.env` 読み込みユーティリティ（src/kabusys/config.py）を追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env を読み込む。
    - export KEY=val、クォート文字列、インラインコメント処理などを考慮した堅牢なパーサを実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / DB パス /監視閾値 等のプロパティを解決。
    - 環境（KABUSYS_ENV）の取り得る値を `development`, `paper_trading`, `live` として検証。
    - paper trading 用の DB パス（PAPER_TRADING_SQLITE_PATH）、PAPER_FILL_MODE の検証等を実装。

- 設定関連 CLI
  - 対話式環境設定ウィザード（src/kabusys/config_setup.py）を追加。
    - .env の作成・更新を対話的に支援。シークレット入力、選択肢、デフォルト表示に対応。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在 & パースチェック（PyYAML がある場合）。
    - `--strict` フラグで警告も失敗扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時に paper-trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler 等の組み立てと起動ロジックを含む。
    - 停止フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) に対応し、安全に停止処理を行う。
    - 標準的な RiskConfig デフォルト値を設定（max_position_pct 等）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用するよう明示。
    - 停止フラグ検知でループを終了、例外時にはログ出力して次回ポーリングまで待機。

- ロギング・ユーティリティ
  - 統一ロギングセットアップ関数（src/kabusys/utils/logging_setup.py）を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - 既存ハンドラの二重登録を防ぐため再設定時にクリアする。
    - ログレベル/ログディレクトリは引数 > 環境変数 > デフォルト の順に解決。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。

- プロセス優先度 / CPU affinity
  - クロスプラットフォーム対応ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応して優先度を "high"|"normal"|"low" に設定。
    - CPU affinity を最初の N コアに固定する機能を提供。権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築関連（pure functions）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - 候補選定（スコア降順、signal_rank でタイブレーク）、等金額配分、スコア加重配分（全銘柄スコアが 0 の場合は等金額にフォールバック）を実装。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap：既存保有のセクター比率が上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供（未知のレジームは警告して 1.0 でフォールバック）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method により "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（利用可能現金に対するスケーリング）、コストバッファによる保守的見積り、残差分の再配分アルゴリズムを実装。
    - 価格欠損時のログ出力・スキップ、将来的な拡張（銘柄別 lot_size 等）に関する TODO を含む。

- リサーチ（部分実装）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加（Momentum 等の計算ロジックを実装予定）。
    - DuckDB を使って prices_daily / raw_financials を参照し、モメンタム・MA200乖離・ATR 等を計算する設計（関数 calc_momentum の骨格を含む）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う CLI。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。
    - DB パスは引数 `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db` の順で解決。

### Changed
- なし（初回リリースのため）

### Fixed
- なし（初回リリースのため）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### 注意事項 / 既知の制約
- .env / 設定ファイルは機密情報を含む可能性があるため、.env は Git にコミットしない旨を README 等で周知する必要があります（config_setup.py にも注記あり）。
- process_priority や CPU affinity の設定は権限に依存するため、AccessDenied の場合は警告が出てスキップされます。
- position_sizing や apply_sector_cap は価格データが欠損していると過少見積りになる可能性があり、コメントで示したように将来的にフォールバック価格の導入を検討する必要があります。
- research モジュールはモメンタム計算の骨格が含まれますが、完全実装（全ファクターの算出・正規化等）は引き続き作業が必要です。

---

今後のリリースでは以下を予定しています（例）:
- research モジュールの全ファクター実装とバッチ/単体テスト追加
- ExecutionEngine / Broker クライアント周りの統合テスト・モックの拡充
- 単体テスト・CI の導入およびドキュメント整備

（必要であれば、この CHANGELOG を英語版に翻訳したり、より細かいコミット毎の記録を生成します。）