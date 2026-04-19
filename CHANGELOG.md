CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 基本機能を実装した初期リリース。
  - 実行コンポーネント
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
      - KABUSYS_ENV=paper_trading の場合、MockBrokerClient/ペーパートレード用 SQLite（data/paper_trading.db）を利用する分離動作をサポート。
      - 起動時にプロセス優先度を設定（high）。停止フラグ（data/stop_requested.flag）を検出して安全に停止。
      - 実行用 PID ファイル出力の仕組みをサポート。
  - 監視コンポーネント
    - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
      - ポーリングループ、MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動を実装。
      - 停止フラグ検知でループ終了、例外発生時のログ出力とリトライ継続。
  - 設定管理 / ユーティリティ
    - 環境設定読み込みと Settings クラス（src/kabusys/config.py）
      - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から探索）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
      - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / ログ設定 等）。
      - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）や KABUSYS_ENV の有効値検査を実装。
      - paper_sqlite_path / sqlite_path / duckdb_path 等デフォルトパスを定義。
    - 対話式設定ウィザード（src/kabusys/config_setup.py）
      - .env の初期作成・更新を対話式に支援。シークレット入力や既存値の再利用、.env 保存機能を実装。
    - 設定検証 CLI（src/kabusys/validate_config.py）
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config/*.yaml の存在・パース確認（PyYAML がない場合は警告）。
      - --strict オプションで警告を失敗扱いにするモードを追加。
  - ポートフォリオ構築（純粋関数群、DB 非依存）
    - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
      - 候補選定（スコア降順 + タイブレーク）、等金額・スコア加重配分を実装。スコア全0 の場合は等分にフォールバック。
    - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
      - セクター集中上限適用ロジック（既存保有の時価計算・除外売却銘柄対応）。
      - レジームに応じた投下資金乗数（bull/neutral/bear）。
    - 口数決定・制約処理（src/kabusys/portfolio/position_sizing.py）
      - risk_based / equal / score 方式の発注株数計算、lot_size（単元）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積り）考慮。
  - 研究用ファクター計算（部分実装）
    - ファクター計算フレームワーク開始（src/kabusys/research/factor_research.py）― DuckDB を用いた momentum 等の計算を意図した実装。
  - ツール
    - Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
      - ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し、PASS/FAIL 判定付きのレポートを標準出力に生成。
      - デフォルト DB パスは data/paper_trading.db、コマンドラインで日付範囲や DB を指定可能。
  - ログ / プロセス管理ユーティリティ
    - 統一ロギング設定（src/kabusys/utils/logging_setup.py）
      - コンソール (stdout) と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、30日バックアップ、LOG_LEVEL/LOG_DIR 環境変数対応。
    - プロセス優先度 / CPU アフィニティ（src/kabusys/utils/process_priority.py）
      - Windows / POSIX の差分を吸収して nice / priority_class を設定。例外時は警告でスキップ。CPU affinity 固定関数も提供。
  - DB 初期化サポート
    - init_monitoring_db を実行して監視テーブルの存在を保証（冪等）。

Changed
- 初期公開版として、開発設計文書（コメントや docstring）に沿った実装を多数追加。コード中に将来仕様や TODO が記載されている部分あり（例: price フォールバック、lot_size の銘柄別拡張など）。

Fixed
- N/A（初期リリース）

Deprecated
- N/A

Removed
- N/A

Security
- 環境変数の自動読み込み時、既存の OS 環境変数は保護される仕組みを実装（.env の override 動作と protected set の採用）。
- .env ファイル生成時に「絶対に Git にコミットしないこと」を強調するヘッダを追加。

Notes / Implementation details（実装上の注記）
- .env パーサは export プレフィックス／クォート内エスケープ／インラインコメント処理等に対応し、より堅牢な読み込みを目指しています。
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（整数でない、0以下等）な場合に警告してデフォルト 60 秒にフォールバックします。
- run_execution は起動前に停止フラグが既に立っている場合は起動を中止し、安全に終了します。
- validate_config は PyYAML 非インストール時にも graceful に警告を出して処理を続行します。
- position_sizing の aggregate cap スケーリングでは単元（lot_size）単位での丸めと残余配分ロジックを実装して、利用可能資金に合わせた再配分を行います。

今後の予定（例）
- research/factor_research.py の完全実装と単体テスト追加。
- 戻り値・例外に対する詳細なユニットテストの充実。
- 銘柄ごとの lot_size サポートや価格フォールバックロジックの実装。
- monitor / execution のコンフィグパラメータ化（CLI あるいは YAML 設定）を検討。

----------------------------------------
このファイルはコードベースの内容から推測して作成しました。追加の変更履歴やリリース日、既知の問題などがある場合は適宜更新してください。