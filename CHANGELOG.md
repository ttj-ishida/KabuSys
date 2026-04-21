# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このプロジェクトはセマンティック バージョニング (SemVer) を採用しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回リリース。主要な機能と CLI、ユーティリティ類を追加しました。

### Added
- コア設定管理
  - `kabusys.config.Settings` を追加。環境変数から各種設定（API トークン、DB パス、監視閾値、環境種別など）を取得するプロパティを提供。
  - 自動 `.env` 読み込み機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から検出）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` でオフ化可能。
  - `.env` 行パーサーの実装（引用符・エスケープ・インラインコメント対応、`export KEY=val` 形式対応）。
  - `PAPER_FILL_MODE` のバリデーション（有効値: `"instant"|"partial"|"never"|"reject"`）。
  - 本番/ペーパートレード用の SQLite パス分離（`SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH`）。

- 起動スクリプト / 実行系
  - `run_execution.py` を追加。`ExecutionEngine` の起動ロジックを実装。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB（`data/paper_trading.db` 等）へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を高 (`high`) に設定。
    - PID 管理 (`data/execution.pid`) と停止フラグ (`data/stop_requested.flag`) をサポート。停止フラグ検出時に安全に停止。
    - 注文管理、リスク管理、リコンシリエーション等の依存コンポーネントを組み立てて `ExecutionEngine.run_session` を別スレッドで実行。

  - `run_monitoring.py` を追加。`SystemMonitor` のポーリングループを実装。
    - 環境に関わらず監視は本番用の `sqlite_path` を使用（監視用 DB を共通で利用する設計）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正な値は警告の上デフォルトへフォールバック。
    - 停止フラグ (`data/stop_requested.flag`) 検出でループを終了。
    - 例外発生時は例外をログに残して次ポーリングへ継続。

- 設定支援 CLI
  - `kabusys.config_setup`（対話式ウィザード）を追加。
    - `.env` の初期作成・更新を対話式に支援。シークレット項目はマスク表示。
    - 既存 `.env` 読み込み、デフォルト値・選択肢サポート、保存前の確認を実装。
  - `kabusys.validate_config`（設定検証 CLI）を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB ファイル親ディレクトリ存在確認、`config/*.yaml` の存在および YAML パース検証（PyYAML がある場合）等を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日分保管）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続。
    - ログレベル/ログディレクトリの解決順を提供（引数 > 環境変数 > デフォルト）。
    - stdout を使用することにより cron 等からの出力一元化に配慮。
  - `kabusys.utils.process_priority` を追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収するプロセス優先度設定 (`set_process_priority`) を実装。アクセス権限がない場合は警告を出してスキップ。
    - CPU コア固定 (`set_cpu_affinity`) をサポート。未対応環境や権限不足は警告でスキップ。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder` を追加。
    - シグナル選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。全スコアがゼロの場合は等金額配分へフォールバックし WARNING を出力。
  - `kabusys.portfolio.risk_adjustment` を追加。
    - セクター集中上限の適用 (`apply_sector_cap`)、市場レジームに応じた投下資金乗数 (`calc_regime_multiplier`) を実装。未知のレジームは 1.0 でフォールバックし WARNING を出力。
    - `apply_sector_cap` は "unknown" セクターを上限適用対象外にする設計（既知セクターのみ制限）。
  - `kabusys.portfolio.position_sizing` を追加。
    - 発注株数算出 (`calc_position_sizes`) を実装。`risk_based` / `equal` / `score` の配分方式、単元株（lot）丸め、1 銘柄上限・集計キャップ、コストバッファを考慮したスケーリング（端数処理の再配分ロジック）を備える。

- 解析・検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading の検証レポートを SQLite（デフォルト: `data/paper_trading.db`）から生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）で PASS/FAIL を判定。
    - P95 計算、日時フィルタ（ISO8601 UTC タイムスタンプ）対応。DB 存在チェックやテーブル欠如時のフォールバック処理あり。

- 研究用ファクター計算（基盤）
  - `kabusys.research.factor_research` を追加（モメンタム等のファクター計算モジュールの基盤）。
    - モメンタム / MA200 / ATR / 流動性等の計算方針と定数を実装（関数群の実装途中のファイルも含む）。

- パッケージ初期化
  - `kabusys.__version__ = "0.1.0"` を設定。
  - `kabusys` の public API を整理（portfolio 等をエクスポート）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- 監視（monitoring）は環境変数 `KABUSYS_ENV` に依らず本番用 `SQLITE_PATH` を使用する設計です。監視データを本番と分離したい場合は利用方法を再検討してください。
- ログは標準出力（stdout）へ出すようにしてあるため、ログ収集・リダイレクトの運用を想定した設定が容易です。
- `.env` 読み込みは OS 環境変数を保護するため既定で上書きしません。`.env.local` は `.env` を上書きする用途で利用できます。
- `config/*.yaml` のパース検証は PyYAML がインストールされている場合にのみ実行します（未インストール時は警告）。

### Known limitations / TODO
- `position_sizing` の lot_size は現状グローバル共通（将来的に銘柄別 lot_map を受け取る予定）。
- `risk_adjustment.apply_sector_cap` の価格欠損時（0.0）は過少見積りとなる可能性があるため、フォールバック価格（前日終値等）の導入を検討中。
- `research.factor_research` の一部関数はまだ実装途中（ファイル末尾に未完の箇所あり）。

---

配布パッケージのバージョンは `kabusys.__version__` を参照してください。問題や改善提案があれば issue を作成してください。