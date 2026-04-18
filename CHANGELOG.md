# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回リリース。主要機能と実装の要点を以下に列挙します。

### Added
- 基本アプリケーション
  - パッケージ基盤を追加。バージョンは `kabusys.__version__ = "0.1.0"`。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV に応じた DB 分離（paper_trading モードでは専用 SQLite を使用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全なシャットダウン処理。
    - 起動時プロセス優先度設定と pid ファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（監視は本番 DB を参照）。
    - 停止フラグ検知・例外捕捉・ログ出力を備えたループ実装。
- 設定管理
  - config.py: .env 自動読み込み（.env → .env.local、OS 環境変数保護、無効化フラグあり）。
    - .env パース処理の強化（export 形式、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスを導入し、J-Quants / kabu API / DB /監視閾値等のプロパティを提供。
    - paper_trading 用パス、PAPER_FILL_MODE 検証、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
- 設定検証
  - validate_config.py: 起動前に .env と config/*.yaml の存在・妥当性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスと config YAML の検査、live 環境向けの追加警告。
    - `--strict` オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順＋タイブレーク）、等金額配分、スコア加重配分（スコアが全て0なら等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有を考慮して同一セクターの新規エントリを制限。
    - レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py
    - risk_based / equal / score の各配分方式に対応した発注株数算出ロジック。
    - 単元株（lot_size）の丸め、1銘柄上限、aggregate cap（投下合計が利用可能現金を超える場合のスケールダウン）、コストバッファ考慮。
  - portfolio/__init__.py: 上記関数を外部公開。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決ルール、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py
    - Windows/Linux（POSIX）差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供。
    - psutil を用い、アクセス権が無い場合は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力する CLI を追加。
    - 判定閾値（稼働率 99% 等）を定義し PASS/FAIL を出力。
- 研究用モジュール（骨格）
  - research/factor_research.py
    - DuckDB 接続を受けるファクター計算モジュールの骨格を追加（モメンタム、Value、Volatility、Liquidity 等）。Pandas/SQL による計算を予定。

### Changed
- ログ出力
  - コンソール出力は stderr ではなく stdout を使用（シェルからのリダイレクトや Task Scheduler 対応のため）。
  - ログディレクトリ作成に失敗した場合もアプリは継続するように堅牢化（ファイルハンドラをスキップ）。
- .env 自動読み込み
  - プロジェクトルートの検出を `.git` または `pyproject.toml` に基づく方式に変更。これにより CWD に依存せず振る舞いが安定。
  - 自動ロードを無効にするための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途想定）。
- DB 設定
  - run_monitoring は監視用に常に本番の sqlite_path を参照する仕様（監視は本番 DB を対象とするため）。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用（本番 DB と完全分離）。
- 設定検証
  - config/*.yaml の有無チェック時、PyYAML 未インストールならパース検証をスキップして警告を出すように変更。

### Fixed
- シャットダウン処理の堅牢化
  - run_execution / run_monitoring ともに停止フラグ（data/stop_requested.flag）を監視して安全に停止するロジックを追加。
  - run_monitoring のポーリングループで check_once() の例外を捕捉してログ出力し、次のポーリングに続行するように改善。
- .env パースのバグ回避
  - クォート内のエスケープや export 形式、インラインコメントの扱いを改善して、.env のパース誤りによる不正読み込みを防止。

### Security
- .env は絶対にリポジトリへコミットしない旨を config_setup.py のヘッダに明記。
- Settings._require() により必須のシークレット環境変数が未設定の場合に起動前に明確なエラーを出すようにした。

### Deprecated
- なし

### Removed
- なし

補足:
- 一部モジュール（例えば research/factor_research.py の実装末端）はスナップショットの都合で途中までの実装となっています。今後のリリースでファクター計算の詳細実装・テスト・ドキュメント化が予定されます。