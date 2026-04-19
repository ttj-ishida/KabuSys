# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。

全体方針:
- 初期リリースとして機能群を追加。設定管理・起動スクリプト・監視/実行エンジン周りのユーティリティ、およびポートフォリオ構成や検証ツールを含みます。

## [0.1.0] - 2026-04-19

### Added
- パッケージ初期リリース。
  - バージョン: `kabusys.__version__ = "0.1.0"`

- 環境設定 / ロード
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env / .env.local の読み込み順序と上書きルールを整備（OS環境変数を保護）。
  - 環境変数のパース機能を強化（export 形式対応、クォート内のエスケープ、インラインコメントの取り扱い）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- 設定管理クラス
  - `kabusys.config.Settings` を導入。J-Quants / kabuAPI / LINE / DB / 監視 / システム設定等のプロパティを提供。
  - `Settings` による環境判定（development / paper_trading / live）、paper_trading 用 DB パス、PAPER_FILL_MODE バリデーション等を実装。
  - 必須環境変数未設定時に例外を投げる `_require` ヘルパーを導入。

- 設定ウィザード CLI
  - `kabusys.config_setup` により対話式で .env を作成・更新可能。
  - シークレット入力対応、既存 .env 読み込み、保存前の確認表示を実装。

- 設定検証 CLI
  - `kabusys.validate_config` を実装。起動前に必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）をチェック。
  - --strict オプションで警告も失敗扱いにできる。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
  - stdout (StreamHandler) と日次ローテーションのファイルハンドラ (TimedRotatingFileHandler) をルートロガーへ設定。
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - ログレベルとログディレクトリ解決ルール（引数 > 環境変数 > デフォルト）を実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority` を実装。Windows / POSIX の差分を吸収し、アクセス権限や未対応 OS は警告でフォールバック。
  - `set_cpu_affinity` を実装し最初の N コアへピン留めする機能を提供。

- 起動スクリプト
  - 実行エンジン起動スクリプト: `run_execution.py`
    - プロセス優先度を高に設定。
    - 環境に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成（paper_trading の場合は Mock を使用する設計）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと起動（スレッド実行）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルを用いた起動/停止制御。
    - 監視テーブルの初期化（init_monitoring_db）を保証。

  - 監視ループ起動スクリプト: `run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番の sqlite_path を使用する設計（ドキュメント化）。
    - SystemMonitor の単発チェックをポーリングで呼び出し、例外はログに記録してループ継続。
    - 停止フラグ検出でループを終了し、DB 接続をクローズ。

- 監視 DB 初期化フック
  - `init_monitoring_db` 呼び出しにより、起動時に監視テーブルが存在することを保証（冪等）。

- Portfolio（銘柄選定・配分・サイズ決定）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定: スコア降順、タイブレークは signal_rank。
    - 等金額配分(calc_equal_weights) とスコア加重配分(calc_score_weights)（全銘柄スコアが 0 の場合は等金額へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 (apply_sector_cap): 既存保有のセクター時価を計算し上限を超える場合は当該セクターの新規候補を除外（"unknown" セクターは無視）。
    - レジーム乗数(calc_regime_multiplier): "bull"=1.0, "neutral"=0.7, "bear"=0.3。未知のレジームは 1.0 にフォールバック。
  - `kabusys.portfolio.position_sizing`
    - position size 計算 (calc_position_sizes)
      - risk_based / equal / score の割当方式に対応。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ概算）を加味した安全な配分アルゴリズム。
      - aggregate スケールダウン後の端数処理を remainder に基づいて lot 単位で再配分するロジックを実装。

- Paper Trading 検証レポートツール
  - `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）に対して稼働率、注文成功率・送信率、API レイテンシ（平均/最大/P95）、リスク却下数を集計してレポート出力。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db) に対応。
    - パス/フェイルの閾値を導入（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - データ不足時の安全なハンドリング（テーブルが無い・SQL エラー時に N/A として扱う）。

- 研究 / ファクタ計算（着手）
  - `kabusys.research.factor_research` の基礎を追加（モメンタム・MA200・ATR 等の定義と calc_momentum の骨子）。
  - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針（外部 API 不使用）。※ファイル末尾で実装途中の箇所あり。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

注意事項・設計上のポイント
- Monitoring は環境に依存せず production sqlite_path を使用するという実装上の挙動をドキュメント化（run_monitoring の docstring）。
- Paper Trading は DB を明確に分離（paper_sqlite_path）しており、本番データと混在しないよう配慮。
- process_priority / CPU affinity の設定は権限不足や未対応プラットフォームで失敗しても警告ログを出して安全にフォールバックする設計。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後も CWD に依存せず動作するよう配慮。
- 一部モジュール（例: factor_research の一部）は実装途中のコメント/未完部分あり。将来的な拡張を予定。

---

今後の予定（例）
- factor_research の完全実装（モメンタム以外のファクター、標準化ユーティリティとの連携）。
- テストカバレッジの追加（ユニットテスト、統合テスト）。
- ExecutionEngine / Broker の詳細実装と paper_trading のモック動作検証用ユーティリティの充実。
- config/*.yaml の具体的なスキーマ検証の強化。