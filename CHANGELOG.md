# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
各リリースには互換性の有無（Breaking changes）や重要な動作仕様も記載しています。

なお、この CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-24
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### Added
- 実行系
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - スレッドでエンジンを実行し、停止フラグ検出時に安全に停止する仕組みを実装。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory により環境に応じて MockBrokerClient / 実ブローカーを切り替え可能。
    - リスク管理（RiskManager）設定、OrderManager、Reconciler、OrderRepository 等の組み立てロジックを実装。
    - 起動時にプロセス優先度を "high" に設定するフローを導入。

- 監視系
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計（監視データは本番 DB に記録）。
    - stop フラグ（data/stop_requested.flag）を検知してループ終了。
    - check_once() の例外を拾ってログに出力し、次のポーリングでリトライする堅牢化。

- 設定 / 初期化
  - 環境設定管理モジュール（src/kabusys/config.py）を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）を行い、.env/.env.local を自動読み込み（任意で無効化可能）。
    - .env パーサは export 形式、クォート付き値、エスケープ、コメント処理に対応。
    - Settings クラスで各種設定値をプロパティとして提供（DB パス、API トークン、Paper Trading 設定、しきい値等）。
    - PAPER_FILL_MODE のバリデーション（有効値: instant/partial/never/reject）、KABUSYS_ENV / LOG_LEVEL の検証を実装。

  - 設定ウィザード CLI（src/kabusys/config_setup.py）を追加。
    - 対話式で .env を生成・更新。
    - シークレット項目はマスク表示、既存 .env の読み込み・再利用に対応。
    - 保存前に設定内容の確認プロンプトを実装。

  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数の未設定チェック、プレースホルダ検出、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があれば内容も検証）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順・タイブレーク処理）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコア 0 の場合は等金額にフォールバック）
  - セクター集中・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有比率に基づくセクター上限フィルタ（"unknown" セクターは除外しない挙動）
    - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数（未知は 1.0 でフォールバック）
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method（risk_based / equal / score） に対応
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（投下資金が available_cash を超える場合のスケーリング）、cost_buffer を考慮した保守的見積り、残差処理（lot 単位での追加配分）を実装

- ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに統一的に設定
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続
    - LOG_LEVEL / LOG_DIR の解決ロジックを提供
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS の差分を吸収して優先度設定（high/normal/low）を適用
    - CPU affinity を最初 N コアに固定する機能を提供
    - 権限不足等の失敗時には警告ログを出してスキップ
  - パッケージ初期化ファイルにバージョン設定（src/kabusys/__init__.py: __version__ = "0.1.0"）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を集計してレポートを出力
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定
    - 日付範囲フィルタ/DB パス指定オプションをサポート

- リサーチ（部分実装）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py、モメンタム等）を追加（DuckDB を使った prices_daily/raw_financials 参照によるファクター計算設計を実装。calc_momentum の骨子を含む）

### Changed
- （初回リリースのため履歴上の変更なし。ただし以下の設計上の決定を明示）
  - 監視（monitoring）は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは本番側で一元管理）。
  - Execution は paper_trading 環境で専用 DB を使用することで本番データと完全分離する設計。

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- config の自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- 一部モジュール（例: research.calc_momentum）の実装が途中のファイルや TODO コメントが存在する可能性があります（今後の拡張予定）。
- position_sizing の価格欠損（price が 0.0）の扱いについて TODO コメントがあり、将来的にフォールバック価格の導入が検討されています。

### Security
- （初回リリースのため該当なし）

---

今後のリリースでは以下を予定しています（予定項目）:
- research モジュールのファクター群の完成（Value / Volatility / Liquidity 等の実装と正規化）
- ExecutionEngine の追加テスト・障害復旧ロジック強化
- モニタリングのアラート送信（LINE 通知等）統合
- 銘柄ごとの lot_size マスタ対応（銘柄別単元対応）