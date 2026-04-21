# Changelog

すべての重要な変更点を Keep a Changelog の形式で日本語で記載します。

フォーマットの方針:
- 「Added / Changed / Fixed / Deprecated / Removed / Security」の見出しを使用しています。
- リリースはパッケージ内の __version__ = "0.1.0" を基準にしています。

## [Unreleased]
（現時点で未リリースの差分はありません）

## [0.1.0] - 2026-04-21
最初の公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構成関係、監視・実行の起動ロジック、および検証／設定支援ツールを収録しています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて `0.1.0` として定義。

- 起動スクリプト
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60秒）。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用。
    - stop フラグファイル（data/stop_requested.flag）で終了検知。
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBroker を利用して本番 DB と完全分離。
    - 実行中は PID ファイル管理と stop フラグ検出で安全に停止可能。

- 設定・環境管理
  - Settings クラス: `src/kabusys/config.py`
    - 環境変数を抽象化したプロパティ群を提供（DB パス、API トークン、各種閾値、環境判定など）。
    - `.env`/.env.local の自動読み込み機能を実装（プロジェクトルートの自動検出: `.git` または `pyproject.toml` を基準）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - `PAPER_FILL_MODE` のバリデーション、有効値チェック。
    - `env`, `log_level` の値検証とユーティリティプロパティ（is_live/is_paper/is_dev）。
  - 環境設定ウィザード: `src/kabusys/config_setup.py`
    - `.env` を対話式に生成・更新する CLI を追加（シークレット入力、選択肢、既存値の利用が可能）。
    - `.env` 書き込み時のテンプレートと注意書きを出力。

- 設定検証ツール
  - validate_config: `src/kabusys/validate_config.py`
    - 起動前に .env と config/*.yaml の存在や基本整合性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の妥当性確認、DB パスの親ディレクトリチェック、YAML パース（PyYAML インストール時）、
      live 環境に対する追加警告などを実装。
    - `--strict` オプションで警告も FAIL 扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio_builder: `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（スコア降順・タイブレーク）と重み計算（等分配・スコア重み）を実装。
  - risk_adjustment: `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - 未知レジームでのフォールバック挙動とログ警告を実装。
  - position_sizing: `src/kabusys/portfolio/position_sizing.py`
    - 各銘柄の発注株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積もり。
    - 残余キャッシュ分の分配アルゴリズム（fractional remainders を用いた lot_size 単位での追加配分）を実装。

- モニタリング・実行支援
  - monitoring_db 初期化呼び出し（init_monitoring_db を起動スクリプトで使用）で監視テーブルの存在を保証（冪等）。

- ログ・プロセスユーティリティ
  - logging_setup: `src/kabusys/utils/logging_setup.py`
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - ログディレクトリの自動作成、失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル・ログディレクトリの解決順を明確化。
  - process_priority: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX（Linux, Darwin, FreeBSD）間の差分を吸収してプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ツール類
  - Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB から各種指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポート出力。
    - P95 算出、閾値による PASS/FAIL 判定、期間フィルタ（--from / --to）をサポート。
    - DB が見つからない場合のエラーメッセージを実装。

- 研究用モジュール（骨組み）
  - factor_research: `src/kabusys/research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity などのファクター計算を行う方針と定数を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算関数 calc_momentum の骨格（設計・定数）を追加（実装の一部が続く／未完）。

### Changed
- ログ関連の振る舞い
  - コンソール出力に stdout を使用するよう統一（cron 等で stdout/stderr を一本化する運用を想定）。

### Fixed
- 起動時の安全対策と堅牢性向上
  - MONITOR_POLL_INTERVAL の不正（非整数／0以下）値をログで警告してデフォルト値へフォールバック（run_monitoring）。
  - run_execution/run_monitoring 両方で DB 接続を finally ブロックで確実にクローズ。
  - init_monitoring_db 呼び出しは冪等に動作する前提で起動時に呼ぶことでテーブル未作成時の安全化。
  - validate_config が PyYAML 未インストールの環境でも警告を出して YAML 検証をスキップするように変更（起動失敗防止）。
  - process_priority/set_cpu_affinity は権限不足や未対応環境で例外を握り潰し、警告を出すように修正（プラットフォーム差分吸収）。

### Known issues / Notes
- position_sizing の TODO
  - price が欠損（0.0）の場合、現在は単純にスキップしており、将来的に前日終値や取得原価などのフォールバックを検討中（コード内 TODO 注記あり）。
  - lot_size の将来的拡張（銘柄ごとの単元株情報を stocks マスタで管理する）を想定しているが未実装。
- risk_adjustment の挙動
  - "unknown" セクターはセクター制限を適用しない仕様。必要に応じて運用ルールを見直してください。
- research.factor_research
  - ファイルは設計と定数が揃っているが、一部関数実装が続き（未完）です。運用前に完全実装とテストが必要です。
- logging_setup
  - ログディレクトリの作成に失敗した場合はファイル出力が無効になります（この場合でもコンソールログは出るため致命的ではありませんが注意が必要です）。

### Security
- 本リリースでは特にセキュリティ修正はありません。API シークレット（J-Quants, kabuステーション, LINE 等）は .env に格納する設計のため、.env の漏洩防止（Git への混入禁止）に注意してください（config_setup のヘッダにも注意書きあり）。

---

備考:
- 各 CLI/スクリプトはモジュールとして直接実行可能です（`python -m kabusys.validate_config` 等）。
- 環境依存の挙動（プロセス優先度設定、CPU affinity、ファイルシステム権限など）は実行環境により動作が制限される可能性があります。ログの警告を参考にしてください。