# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

※ 本 CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際の変更履歴と差異がある可能性があります。

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーション骨格を追加
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` を定義。
- 実行/監視ランナーを追加
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI ランナー。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - 停止フラグ / PID ファイルのハンドリングを実装（`data/stop_requested.flag`, `data/execution.pid`）。
    - ブローカークライアントのファクトリ、注文管理、リスク管理、Reconciler を組み合わせてエンジンを起動。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用の sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了、例外時はロギングして次ポーリングへ継続。
- 設定管理・自動ロード
  - `src/kabusys/config.py`
    - .env 自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml`）。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env の読み込みルールを強化（`export KEY=` 形式、クォート/エスケープ、インラインコメントの取り扱い）。
    - 各種設定プロパティを集中管理（DB パス、ログレベル、ペーパートレード設定、監視しきい値など）。
    - `Settings` クラスを提供し、必要な環境変数の必須チェックや値のバリデーションを実装（例: `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL`）。
- 設定検証 CLI
  - `src/kabusys/validate_config.py`
    - .env と `config/*.yaml` の存在・基本妥当性を検証するコマンドラインツールを追加。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - YAML パーサがない場合は YAML 検証をスキップするが警告を出力。
    - 本番環境向けの追加ガードを実装（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告等）。
- 設定ウィザード CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を生成/更新するツールを追加。
    - シークレット項目をマスク表示し、既存値の再利用やデフォルトをサポート。
    - 保存前の確認および `.env` 書き出しロジックを実装。
- ロギングユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。
    - ログディレクトリ自動作成の処理および作成失敗時のフォールバック（コンソールのみ）を実装。
    - ログレベル決定順（引数 > 環境変数 > デフォルト）とログディレクトリ決定順を明確化。
- プロセス優先度 / CPU 固定ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
    - CPU affinity を最初 N コアに固定する `set_cpu_affinity` を提供（権限不足時は警告を出してスキップ）。
- Portfolio 構築ライブラリ
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定 (`select_candidates`) と重み計算（等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`）を追加。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap` を追加（当日売却予定銘柄の除外、"unknown" セクターの扱い）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を追加（`bull`/`neutral`/`bear` のマッピング、未知レジームはフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - 株数算出ロジックを実装（`risk_based`、`equal`、`score` の allocation_method をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に基づくスケールダウン）、残余キャッシュを用いた端数調整ロジックを実装。
  - エクスポートラッパー `src/kabusys/portfolio/__init__.py` を追加。
- Paper Trading 向け検証レポート
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード DB（デフォルト `data/paper_trading.db`）の集計から検証レポートを出力するツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。閾値による PASS/FAIL を判定。
    - コマンドライン引数で期間（--from/--to）や DB パス指定（--db）をサポート。
- 研究用ファクター計算（骨組み）
  - `src/kabusys/research/factor_research.py`
    - DuckDB を用いたモメンタム／ボラティリティ等のファクター計算モジュールの骨組みを追加（モメンタム計算等の定数・設計方針を含む）。
    - （注）ファイル末尾に計算関数の途中と思われる未完了の行が存在するため、一部実装が継続中。

### Changed
- DB/ファイルパスの分離設計
  - 実行系と監視系で DB を明確に分離:
    - 監視 (`run_monitoring.py`) は環境に関係なく `Settings.sqlite_path`（監視 DB）を使用。
    - 実行 (`run_execution.py`) は `KABUSYS_ENV=paper_trading` 時に `paper_sqlite_path` を使用してペーパートレードを本番 DB から分離。
- ログ出力: StreamHandler を stderr ではなく stdout に設定（cron/task からのリダイレクト運用を考慮）。
- .env 読み込み順: OS 環境 > `.env.local`（上書き可）> `.env`（未設定のみ）となる自動ロードロジックを導入。OS 環境変数は保護（上書き不可）。

### Fixed
- 環境値検証の強化
  - `Settings` と `validate_config.py` による環境変数の必須チェック・妥当性チェック（例: `KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` のバリデーション）。
- ログディレクトリ作成失敗時にファイルハンドラ作成でクラッシュしないようフォールバック処理を追加。

### Known issues / Notes
- `src/kabusys/research/factor_research.py` の末尾に未完了の代码片（`start_da` と途切れている）があり、ファクター計算関数（例: calc_momentum）の完全実装が継続中であることを確認しています。実運用前に該当実装の完成とテストが必要です。
- process priority / CPU affinity の設定は OS 権限に依存します。権限不足時はワーニングを出して処理をスキップします。
- 監視モジュールは監視用 sqlite を常に使用する仕様のため、意図せず本番 DB を参照しないよう .env の DB パス設定を確認してください。
- `config_setup.py` で生成する `.env` は機密情報を含むため、絶対にリポジトリへコミットしないでください（ファイルヘッダでも明記あり）。

## Unreleased
- なし（このリリースが初版の推測内容に相当）

-----------

今後のリリース案（候補）
- factor_research の完了とユニットテスト追加
- ExecutionEngine / SystemMonitor の統合テスト、モックブローカーのテストシナリオ拡充
- 各種 CLI の manpage / README 追加および例の拡充
- 銘柄別 lot_size 対応（stocks マスタからの取得）と手数料/スリッページモデルの明文化

もし実際のコミット履歴やリリース日付がある場合は、それに合わせて日付や項目を調整します。必要であれば各変更項目をより詳細に分解して記述します。