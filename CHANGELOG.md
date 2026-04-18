# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠します（コード内容から推測して記載しています）。

注: 本 CHANGELOG は提供されたコードベースの内容から推測して作成したもので、実際のコミット履歴や変更差分に基づくものではありません。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回公開（推測）。自動売買システム「KabuSys」の基礎機能を実装した初期リリース相当の内容を含みます。

### Added
- パッケージの基本バージョンを追加（`__version__ = "0.1.0"`）。 (src/kabusys/__init__.py)
- 環境設定・ロード機能を実装
  - .env ファイルの自動読み込み（プロジェクトルートを検出して `.env` と `.env.local` を読み込む）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。 (src/kabusys/config.py)
  - .env パースの堅牢化（export プレフィックス、クォート内のエスケープ、行末コメント処理など）を実装。 (src/kabusys/config.py)
  - Settings クラスにより環境変数をプロパティで提供（DB パス、ログ設定、閾値、pid/kill フラグパス、paper_trading 用設定など）。 (src/kabusys/config.py)
  - PAPER_FILL_MODE の検証ロジックを追加（有効値チェック）。 (src/kabusys/config.py)

- 起動支援 CLI を追加
  - 対話式 .env 設定ウィザード `config_setup`（.env の初期作成・更新を支援、シークレットマスク表示、デフォルト値）を追加。 (src/kabusys/config_setup.py)
  - 設定検証 CLI `validate_config`（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config/*.yaml 存在チェック、--strict モード）を追加。 (src/kabusys/validate_config.py)

- 実行コンポーネント
  - ExecutionEngine 起動スクリプト `run_execution` を追加。プロセス優先度設定、高優先度での実行、paper_trading 時の専用 DB 分離、BrokerClientFactory によるブローカ選択、ExecutionEngine の起動/停止制御（stop flag, pid ファイル）などを実装。 (src/kabusys/run_execution.py)
  - Monitoring 起動スクリプト `run_monitoring` を追加。プロセス優先度設定、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き、停止フラグ検知、監視 DB 初期化を実装。監視は環境にかかわらず本番 sqlite_path を使用する方針。 (src/kabusys/run_monitoring.py)

- 監視・レポート関連
  - 監視 DB 初期化ユーティリティ（monitoring_db 初期化を参照）を想定して統合。 (参照: run_monitoring, run_execution)
  - Paper Trading 検証レポート生成スクリプト `paper_verification_report` を追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を抽出して PASS/FAIL 判定する。CLI 引数で期間指定や DB パス指定可能。 (src/kabusys/tools/paper_verification_report.py)

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み算出（select_candidates / calc_equal_weights / calc_score_weights）を実装。スコアが全て 0 の場合のフォールバック等の挙動を含む。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）を実装。セクター上限判定やレジーム別乗数（bull/neutral/bear）を提供。 (src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定・リスク制限・単元株丸め（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）に対応、単元株（lot_size）での丸め、aggregate cap に基づくスケールダウン、cost_buffer を考慮した安全弁を備える。 (src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージのエクスポートを整備。 (src/kabusys/portfolio/__init__.py)

- ユーティリティ
  - ロギング設定ユーティリティ `setup_logging` を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定、ログディレクトリ作成に失敗した場合はファイル出力を無効化して続行。 (src/kabusys/utils/logging_setup.py)
  - プロセス優先度 / CPU アフィニティ設定ユーティリティを追加（psutil ベース、Windows / POSIX を吸収）。アクセス権限不足等は警告でスキップ。 (src/kabusys/utils/process_priority.py)

- リサーチ群（骨組み）
  - ファクター計算モジュール（factor_research）の骨組みを追加。Momentum / Value / Volatility / Liquidity を想定した設計ドキュメント相当の実装方針と定数を定義（モメンタム計算関数の実装開始）。（ファイルは未完の可能性あり） (src/kabusys/research/factor_research.py)

### Changed
- （初回リリース相当のため明確な変更はなし、ただし以下の設計判断を明記）
  - monitoring は KABUSYS_ENV に依存せず「本番 sqlite_path」を利用する仕様を採用（監視データと paper_trading の DB 分離の方針）。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
  - run_execution は paper_trading 環境時に専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用することで本番 DB と完全分離。 (src/kabusys/run_execution.py)

### Fixed / Robustness improvements
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、`export KEY=val` 形式対応などを実装して一般的な .env フォーマットに耐性を追加。 (src/kabusys/config.py)
- 設定値検証
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を追加し、無効な値は ValueError を送出して早期検出するようにした。 (src/kabusys/config.py, src/kabusys/validate_config.py)
- ロギング / ファイル IO のフォールバック
  - ログディレクトリの作成失敗やファイルハンドラ作成失敗時にコンソール出力のみで継続するよう安全にフォールバック。 (src/kabusys/utils/logging_setup.py)
- process_priority / cpu_affinity の安全化
  - アクセス権限不足や未実装環境で例外が発生してもログ警告で処理をスキップするようにして、起動失敗を防止。 (src/kabusys/utils/process_priority.py)
- CLI の耐障害性
  - `validate_config` / `paper_verification_report` で対象テーブルや PyYAML 非インストール時の処理を適切にハンドリング（警告やデフォルト値で続行）。 (src/kabusys/validate_config.py, src/kabusys/tools/paper_verification_report.py)

### Documentation / UX
- config_setup の対話式ウィザードにより、.env を安全に作成・更新できる仕組みを提供（シークレットはマスク、確認プロンプト有り）。 (src/kabusys/config_setup.py)
- 各モジュールにドキュメント文字列を充実させ、設計方針や使用例、引数説明、注意点（例: lot_size 将来拡張予定、価格欠損に対する TODO）を明記。 (複数ファイル)

### Potential Known Limitations (推測)
- factor_research モジュールはファイル末尾が未完の状態に見え、実装が途中の可能性あり。実運用前の完成化が必要。 (src/kabusys/research/factor_research.py)
- position_sizing の lot_size は現状全銘柄共通とし、将来的に銘柄別単位への拡張を予定（TODO コメントあり）。 (src/kabusys/portfolio/position_sizing.py)
- apply_sector_cap は sector_map に存在しないコードを "unknown" 扱いとして無条件に除外しない設計だが、価格が欠損（0.0）の場合にエクスポージャー過少見積りのリスクがある点を注記。 (src/kabusys/portfolio/risk_adjustment.py)

---

以上。必要であれば、この CHANGELOG をプロジェクトの実際のコミット歴に合わせて調整（各コミット/PR 単位でのセクション分けや日付修正）できます。どのレベルまで詳細化したいか（例えば各ファイルの変更点を個別コミットとして分ける等）を指示してください。