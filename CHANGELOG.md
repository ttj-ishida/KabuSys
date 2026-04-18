Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
セマンティックバージョニングに従います。

[Unreleased]
-------------

（現時点では未リリースの変更はありません）

0.1.0 - 2026-04-18
-----------------

初回リリース。以下の機能群とユーティリティを追加しました。

Added
- 基本アプリケーション骨組みを追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - エクスポート対象モジュール: data, strategy, execution, monitoring

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
    - プロセス優先度設定、監視 DB 初期化、duckdb 接続を行う
    - 停止制御はプロジェクト内 `data/stop_requested.flag` による
    - 例外発生時のロギングと継続処理を実装（障害に強いループ）
  - run_execution.py: ExecutionEngine 起動スクリプトを追加
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 DB を使用（`data/paper_trading.db` がデフォルト）
    - Broker クライアントの抽象化（BrokerClientFactory）
    - ExecutionEngine をスレッドで実行し、停止フラグ検知で安全に停止する
    - PID ファイルおよび停止フラグの取り扱い

- 設定管理・補助ツール
  - config.py: 環境変数 / .env 自動読み込みと Settings クラスを実装
    - プロジェクトルート自動検出 (.git または pyproject.toml)
    - .env / .env.local の読み込み順序と、OS 環境変数の保護（上書き禁止）を実装
    - 複雑な .env パース対応（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い）
    - Settings に多くのプロパティを定義（J-Quants, kabu API, DB パス、ログ・監視閾値、paper_trading 用設定等）
    - 入力値検証（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）
  - config_setup.py: 対話式 .env 作成ウィザード
    - 多数の設定項目を対話で入力・確認して .env を生成
    - 秘匿項目はマスク表示、既存 .env の読み込みと再利用対応
  - validate_config.py: 設定検証 CLI を追加
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ存在チェック
    - config/*.yaml の存在確認（PyYAML があればパース検証も実行）
    - `--strict` で警告を FAIL 扱いにできるモード

- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティを追加
    - stdout に StreamHandler、日次ローテーションで TimedRotatingFileHandler を追加
    - ログディレクトリ作成失敗時にファイル出力をスキップしてコンソール出力のみで継続
    - デフォルト: ログディレクトリ `logs/`、バックアップ 30 日
  - utils/process_priority.py: プロセス優先度および CPU affinity ユーティリティを追加
    - Windows と POSIX（Linux, macOS など）を吸収
    - `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全ゼロ時は等配分にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有を考慮して上限超過セクターから候補除外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング）
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: risk_based / equal / score）
    - 単元株丸め、per-stock 上限・aggregate cap、cost_buffer を考慮したスケーリングと端数配分

- リサーチ / ファクター計算
  - research/factor_research.py: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）を追加（DuckDB 接続を受ける設計）
    - モメンタム計算の定数・設計概要を実装（関数 calc_momentum の骨格を含む）

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: ペーパートレード結果を集計してレポート出力する CLI を追加
    - 稼働率, 注文成功率, 送信率, リスク却下数, レイテンシ (avg/max/P95) を算出
    - デフォルトで環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db` を参照
    - 合格基準（閾値）を定義して PASS/FAIL 判定を出力

Changed
- 監視/実行系の DB 取り扱いポリシー
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず "本番" の sqlite_path（Settings.sqlite_path）を使用する設計に変更（監視データは一元管理）
  - run_execution は `paper_trading` 環境時に専用の paper_sqlite_path を使用して本番 DB と分離

- ロギングの振る舞い
  - ログは標準エラーではなく標準出力 (stdout) に出すように統一（cron 等のリダイレクト運用を考慮）

Fixed
- .env パースの堅牢化
  - export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理を実装して .env の誤読を軽減
  - .env 自動ロード時に OS 環境変数を保護し、意図しない上書きを防止

- 監視ループの安定性向上
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数）に対してデフォルト値へフォールバックし、警告ログを出すように修正（time.sleep に渡す不正な値を防止）
  - check_once() 呼び出し時の例外をループ内で捕捉してログ出力し、次のポーリングへ継続するように改善
  - KeyboardInterrupt や停止時の DB 接続クローズを finally ブロックで安全に実行

- ログファイル出力の耐障害性
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合に StreamHandler のみで継続して動作するようにした（起動失敗を回避）

- process_priority のフォールバックと例外ハンドリング
  - 未対応プラットフォームや権限不足時に警告を出してスキップすることで起動失敗を回避

Notes / Known limitations
- research/factor_research.py の calc_momentum 関数以降は実装途中（本スナップショットでは途中で切れている）。本格運用前に各ファクター計算の完成・検証が必要です。
- portfolio モジュール内では price が欠損（0.0）だった場合のフォールバック戦略がコメントで示されている（将来的な拡張の余地あり）。
- 一部の機能は外部モジュール（psutil, duckdb, PyYAML 等）に依存します。これらが存在しない場合は機能が限定される箇所があります（validate_config の YAML 検査など）。

Security
- 重要なシークレット（J-Quants トークン、kabu API パスワード）は .env に保存する設計だが、config_setup で「.env を絶対に Git にコミットしないこと」を明示しています。運用時にはシークレット管理ポリシーの適用を推奨します。

Authors
- 初版コードベース（kabusys 0.1.0）

(注) 本 CHANGELOG は与えられたコードから推測して作成しています。実際の変更履歴やリリースノートが別にある場合はそちらを優先してください。