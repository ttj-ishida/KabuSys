# CHANGELOG

すべての重要な変更を Keep a Changelog の形式に従って記録します。

フォーマット:
- すべてのリリースは日付付きで記載
- 主要な追加・変更・修正点を日本語で記載

## [0.1.0] - 2026-04-24

最初の公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理ツール、Paper Trading 検証ツール、および研究用ファクター計算モジュール（部分実装）を含みます。

### Added
- 全体
  - パッケージ初版を追加。バージョンは `kabusys.__version__ = "0.1.0"`（src/kabusys/__init__.py）。
  - プロジェクトルート検出と .env 自動ロード機能を実装（src/kabusys/config.py）。
    - 読み込み順: OS 環境 > .env.local > .env
    - OS 環境変数を保護して上書きを制御
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート
- 設定管理 / CLI
  - 対話式設定ウィザードを実装（src/kabusys/config_setup.py）
    - .env の初期作成・更新を支援、シークレット入力のマスク表示、デフォルト値と選択肢のサポート
    - 生成される .env に注釈を付与し、誤ってリポジトリへコミットしないよう注意喚起
  - 設定検証 CLI を実装（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス・config/*.yaml の存在・YAML パース確認など
    - `--strict` オプションで警告をエラー扱いにできる
- 起動スクリプト
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）
    - デフォルトポーリング間隔 60 秒（`MONITOR_POLL_INTERVAL` 環境変数で上書き可能）
    - 停止フラグファイルによる安全停止、プロセス優先度を High に設定する仕組み、monitoring 用 DB 初期化、duckdb 接続を利用
    - 例外発生時はログに例外出力して次ポーリングへフォールバック
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite を使用して本番 DB と分離
    - BrokerClientFactory 経由でブローカークライアントを取得、ExecutionEngine をスレッドで実行、停止フラグで安全停止
    - PID ファイル、停止フラグの扱いを実装
- ロギング / プロセス管理ユーティリティ
  - 統一的なログ設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）
    - stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を root ロガーへ設定
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX (Linux/Mac/FreeBSD) を透過的に扱う
    - 優先度設定（high/normal/low）と CPU affinity 固定機能を提供。失敗時は警告ログを出力してスキップ
- ポートフォリオ構築
  - 候補選定・重み計算（純粋関数群）を実装（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N 件を選択
    - calc_equal_weights / calc_score_weights: 等分配 / スコア加重（スコア合計が 0 の場合は等分配へフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率が閾値を超える場合に同セクターの新規候補を除外
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）
  - 数量決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割付方式をサポート
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケールダウン、コストバッファ考慮
    - スケールダウン時の残差分配ロジック（fractional remainder を用いて lot 単位で追加配分）
- Paper Trading / 検証ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出して human-readable レポートを出力
    - デフォルト DB パスは `data/paper_trading.db`、環境変数 `PAPER_TRADING_SQLITE_PATH` または CLI オプション `--db` で指定可能
    - パス/テーブル欠損時はフォールバックして N/A を表示
- 研究用
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）
    - Momentum, Value, Volatility, Liquidity に関する設計と一部実装。DuckDB 接続を受け prices_daily / raw_financials を参照する設計
    - モメンタム計算関数 calc_momentum の実装を開始（ファイル末尾で未完の箇所あり）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Limitations / TODO
- config.auto-load:
  - .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。
- セキュリティ:
  - .env はデフォルトで secrets（トークン/パスワード）を含むため、リポジトリへコミットしないことを README 等で強く推奨。
  - config_setup はシークレット項目をマスクして表示するが、生成される .env には生の値が書き込まれる点に注意。
- 未完成 / 将来の拡張候補:
  - src/kabusys/research/factor_research.py の calc_momentum 関数はファイル末尾で途中までの実装（切り欠け）があります。完全実装が必要です。
  - src/kabusys/portfolio/position_sizing.py 内で価格が欠損（0.0）の場合のフォールバック（前日終値や取得原価など）については TODO コメントあり。将来的に stocks マスタで lot_size を銘柄別に持たせる拡張も検討。
  - process_priority の実行は権限により失敗する可能性があるため、実行環境の権限（特に Linux の nice 値マイナスなど）に注意してください。
- ログ:
  - logging_setup はログディレクトリの作成に失敗した場合でもコンソール出力のみで継続するよう設計されています。ログファイルが必要な環境では LOG_DIR の書き込み権限を確認してください。
- 実行スクリプト:
  - run_monitoring/run_execution は stop フラグファイル（data/stop_requested.flag）と PID ファイルを用いてプロセス管理します。CI/デプロイ環境での扱いに注意してください。

---

今後のリリースでは次を目標にしています:
- research/factor_research の完全実装とテスト
- strategy や execution 周り（OrderManager / ExecutionEngine）のユニットテスト追加
- モニタリング・アラート（LINE 通知等）の実装強化と設定周りのドキュメント充実

ご要望や不具合報告は issue を作成してください。