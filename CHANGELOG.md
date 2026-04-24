# Changelog

すべての重要な変更をここに記録します。書式は「Keep a Changelog」に準拠しています。  

- リリース方針・セマンティクス: バージョンはパッケージの __version__ に準拠しています（現在: 0.1.0）。

## [Unreleased]

（現時点で未リリースの変更はありません。次回リリース時にここを更新してください）

---

## [0.1.0] - 初回リリース（推定）
初期公開リリース。システム起動スクリプト、設定管理、検証・ウィザード、ポートフォリオ構築・リスク制御ロジック、ユーティリティ群、ペーパートレード検証ツールなどを含むフルスタックの自動売買サブシステムを導入。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。スレッドでセッションを実行し、stop フラグで安全停止。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig を含む）を組み立てて実行エンジンを起動。
    - 起動時にプロセス優先度を "high" に設定する処理を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒で、環境変数 MONITOR_POLL_INTERVAL により上書き可能。
    - 監視実行は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する仕様（設計上の注意点）。
    - 停止フラグ（data/stop_requested.flag）を検知してループから安全に抜ける実装。

- 設定関連
  - config.py
    - .env の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を基準）を実装。
    - .env のパース機能を改良（export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等）。
    - 環境変数の保護/上書きルール（OS 環境変数を保護する protected セット）を導入。
    - Settings クラスを実装し、各種設定 (DB パス、API トークン、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等) をプロパティとして提供。値検証（有効値チェック）を行う。
    - settings = Settings() をエクスポート。

  - config_setup.py
    - 対話式ウィザードで .env を新規作成/更新する CLI を追加。シークレット項目はマスク表示、選択肢・デフォルト提示、保存前確認をサポート。
    - 出力される .env テンプレートには注意書き（Git にコミットしない等）を付与。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数の未設定チェック、プレースホルダ警告、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在/パースチェック（PyYAML がない場合はスキップ）などを行う。
    - --strict オプションで警告を失敗扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアがすべて 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を追加（既存保有の時価を計算し、上限を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じた計算（risk_based / equal / score）をサポートし、
      - 単元株（lot_size）での丸め、
      - 1 銘柄上限（max_position_pct）適用、
      - aggregate cap（available_cash）を超える場合のスケールダウンと残差処理を実装、
      - cost_buffer による保守的見積りを考慮。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。既存ハンドラのクリアやログディレクトリ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を追加。Windows と POSIX（Linux/Mac 等）の差分を吸収し、権限不足等の例外は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、閾値（稼働率 99% など）に基づく PASS/FAIL 判定を行う。CLI で期間指定や DB パス指定が可能。

- リサーチ（骨格）
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム等）の実装を開始。DuckDB を使った prices_daily / raw_financials の参照設計、各種期間定数、calc_momentum 等の関数スケルトンを含む（calc_momentum が途中まで実装されている状態）。

- パッケージメタ
  - __init__.py にてバージョンを 0.1.0 に設定。

### Changed
- ロギング
  - stdout に出力する StreamHandler を採用（stderr ではなく stdout を使用）。cron 等からのリダイレクト運用を想定。
  - ログディレクトリの作成失敗時はファイルハンドラをスキップしてコンソールのみで継続する堅牢性を追加。

- 環境変数の自動読み込み挙動
  - プロジェクトルート検出を .git / pyproject.toml にて行うようにして、パッケージ配布後や CWD に依存しない自動読み込みを目指す。

### Fixed
- .env パースの改善
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等を正しくパースするよう強化。これにより .env のより実用的な記述をサポート。

### Security
- シークレットの扱い
  - config_setup の対話ではシークレット項目（トークン・パスワード）を入力時にマスク表示し、.env の取り扱いについて「絶対に Git にコミットしないこと」を強調する注釈を付与。

### Notes / Breaking changes / Important design decisions
- 監視（run_monitoring.py）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用監視 DB）を使用します。テスト/開発環境で監視データを分離したい場合は設定・実装の見直しが必要です。
- PAPER_TRADING では発注ロジックはモック化され、paper_trading 用別 DB（デフォルト data/paper_trading.db）にログを残す設計のため、本番データと完全に分離可能。
- process_priority / cpu_affinity の設定は権限が必要な操作であり、権限不足や環境によっては設定がスキップされることがあります（警告ログが出力されます）。
- research/factor_research.py は計算ロジックの骨格を含みますが、一部未完（サンプルの最後で切れているため追加実装が必要）。

### CLI / 実行例（ドキュメント的メモ）
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

今後の改善案（参考）
- factor_research の未完部分（calc_momentum 等）の実装完了。
- monitoring が本番 DB を使用する仕様を設定で切り替え可能にする（テスト用 DB の利用を容易に）。
- stocks マスタに lot_size を持たせ、calc_position_sizes を銘柄別単元サイズに対応させる拡張。
- ロギング設定の単体テストカバレッジ拡充、ファイルハンドラ失敗時の詳細ロギング強化。