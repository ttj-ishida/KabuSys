# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在の想定バージョン: 0.1.0（初回リリース／コードベースから推測して作成）

## [Unreleased]
このセクションは将来の変更用に予約しています。  
コード内の TODO / 未完事項や既知の制約をここに記載します。

### Known issues / TODO
- research/factor_research.py の `calc_momentum` 等、ファクター計算モジュールの一部が未完（途中で切れている）。実運用前に実装完了が必要。
- apply_sector_cap 内の price 欠損時の扱い（price が 0.0 の場合にエクスポージャーが過少見積りされる点）に関する TODO 注記あり。前日終値などのフォールバック価格導入が望ましい。
- position_sizing の将来的拡張: 銘柄別単元（lot_size）マップ対応の TODO。
- ログディレクトリ作成やプロセス優先度設定など、権限不足や未対応 OS の場合はフォールバックするが、運用時は環境確認を推奨。

---

## [0.1.0] - 2026-04-20

初回リリース想定。リポジトリ内のスクリプト・ライブラリ実装に基づき、主要な機能を追加しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用 DB を使用（data/paper_trading.db がデフォルト）し、MockBrokerClient を使用する設計をサポート。
    - スレッドでエンジンをデーモン実行し、 data/stop_requested.flag による外部停止制御に対応。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。監視は常に本番用 sqlite_path を使用する旨を明示。

- 設定管理 & CLI
  - config.py
    - Settings クラスを実装し、環境変数経由で各種設定（DB パス、API トークン、Paper Trading 設定、閾値等）を取得。
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。.env.local は .env を上書き可能。ただし OS 環境変数は保護。
    - PAPER_FILL_MODE 等の検証（有効値チェック）を実装。
  - config_setup.py
    - .env を対話的に生成・更新するウィザード CLI を実装。シークレット入力や選択肢サポート、.env のフォーマット整形を行う。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば）を行う。
    - --strict モードで警告をエラー扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）: 既存ポジションのセクター別時価から上限超過セクターをブロック。
    - レジーム乗数算出（calc_regime_multiplier）: "bull"/"neutral"/"bear" に応じた乗数を返す（未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap によるスケールダウン（余剰キャッシュを用いた再配分）を実装。
    - cost_buffer により手数料・スリッページを保守的に見積る。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティ。stdout ストリームハンドラと日次ローテーションのファイルハンドラをルートロガーに設定。
    - ログディレクトリの自動作成と失敗時のフォールバック（コンソールのみ）をサポート。ローテーションは 30 日保持。
  - utils/process_priority.py
    - psutil を使ったプロセス優先度（nice / Windows priority class）および CPU affinity 設定を提供。Windows / POSIX の差分を吸収。
    - 権限不足や未対応 OS 時に安全にスキップする挙動。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB を解析し、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計・出力するレポート生成スクリプト。
    - P95 計算、日付フィルタ指定、閾値（稼働率/成功率/レイテンシ）に基づく PASS/FAIL 判定を実装。

- 研究用モジュール（初期実装）
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨子（モメンタム・ボラティリティ・流動性・ファンダメンタルなどを計画）を追加。モジュール設計と定数が定義されているが、一部実装は未完。

- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- （初回リリースにつき該当なし。今後のリリースで差分をここに記載します）

### Fixed
- .env 読み込みロジックを堅牢化
  - _parse_env_line においてクォートやエスケープ、インラインコメントの扱いを考慮したパーサを実装。export KEY=val 形式にも対応。
  - _load_env_file は OS 環境変数を保護する protected 引数を使用して意図しない上書きを防止。

### Security
- .env ファイルについて README 相当の注意書きを config_setup の出力に追加（.env を絶対に Git にコミットしない旨）。

### Documentation / UX
- 各 CLI スクリプトにヘルプ / 使用例コメントを追加（run_*.py、tools/*、config_setup.py、validate_config.py）。
- setup_logging のデフォルト動作・優先順位、ログ出力先の仕様を docstring に記載。

---

注:
- 上記はリポジトリ内のコードから推測して作成した CHANGELOG です。実際のリリース履歴や変更履歴と異なる場合があります。必要であれば、コミット履歴やタグに基づいて日付・内容を調整します。