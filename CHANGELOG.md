CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、日本語で記載しています。  
このリポジトリのバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

[0.1.0] - 2026-04-21
-------------------

Added
- 起動・運用用スクリプトを追加
  - run_monitoring.py
    - SystemMonitor を用いたポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - プロジェクト内 data/stop_requested.flag による外部停止フラグ検知対応。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、本番 DB と完全に分離して data/paper_trading.db を使用。
    - data/execution.pid に PID を書く仕組み、stop フラグ監視による安全停止対応。
- 設定管理・ヘルパー
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）および .env 自動読み込み機能を追加（OS 環境変数の保護対応）。
    - .env のパース強化: export 句対応、シングル／ダブルクォートやエスケープ、インラインコメントの取り扱い、コメントのルールなど。
    - Settings クラスを導入し、環境ごとのプロパティ（duckdb/sqlite パス、paper_trading 用パス、各種閾値、env/log_level 判定等）を提供。
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject）を実装。
  - config_setup.py
    - .env を対話的に作成／更新するウィザードを追加。シークレット項目はマスク表示。
    - デフォルト値・選択肢・説明を備えた項目定義を持ち、既存 .env の読み書き機能を提供。
  - validate_config.py
    - 起動前チェック用 CLI を追加。必須環境変数やパス、config/*.yaml の存在とパース（PyYAML があれば内容の検証）を行う。
    - --strict を指定すると警告も失敗として扱える。
    - 本番環境（KABUSYS_ENV=live）時のガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）を追加。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用可能なログ設定を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、ログディレクトリ作成失敗時はファイル出力を安全に無効化する設計。
    - 既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（high/normal/low）を実装（psutil 使用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加（必要に応じて無効化）。
    - アクセス権限不足時は警告を出して安全にスキップ。
- Portfolio（銘柄選定・配分・サイズ計算）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、タイブレークルール）、等金額・スコア加重の重み計算を実装。スコア全0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中を回避する apply_sector_cap を実装。既存保有のセクター別エクスポージャーを計算し上限超過セクターの新規候補を除外。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング）を実装。未知のレジームはログ警告の上でフォールバック。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じて risk_based / equal / score をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を反映。
    - スケーリング時の端数処理（残余キャッシュに対して fractional 残差の大きい銘柄から lot 単位で追加配分）を実装。
- Research / Tools
  - research/factor_research.py
    - ファクター計算（Momentum, Value, Volatility, Liquidity）用のモジュール骨子を追加。DuckDB 接続を受ける設計。
    - モメンタム系の定数定義（窓長等）を追加（実装は部分的・継続的拡張予定）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH（または --db）からデータを集計して稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ、欠損時の N/A ハンドリング、閾値は定数として定義（稼働率 99% 等）。

Changed
- .env 読み込みの優先順位と安全性を改善
  - OS 環境変数 > .env.local > .env の順でロード。既存 OS 変数は保護され、.env.local は上書き可能。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能（テスト用）。
- ロギング
  - ログ出力先を stdout に統一（StreamHandler）し、外部ジョブ管理（cron 等）でのリダイレクト運用を考慮。
  - ログディレクトリ作成失敗時でも起動を妨げず、ファイル出力のみを無効化する堅牢化。
- 実行時の優先度設定
  - run_monitoring と run_execution 起動時に set_process_priority("high") を実行して優先度を上げるよう統一。
- DB 接続
  - run_monitoring は環境にかかわらず production 用 sqlite_path を使用する旨を明確化（監視は本番データを参照する想定）。
  - run_execution は paper_trading モードで専用の SQLite（paper_sqlite_path）を使用し、本番 DB と分離。

Fixed
- 環境変数パースの不整合を修正
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応して .env パーサの堅牢性を向上。
- validate_config の検出強化
  - 必須環境変数がプレースホルダのまま（末尾 _here、your_value 等）である場合に警告を出すように改善。
  - config/*.yaml の読み込みで PyYAML がない場合はパース検証をスキップして警告出力に留める。

Security
- .env の取り扱いに関する注意書きを config_setup の生成ファイルに明示（.env を絶対に Git にコミットしないこと）。
- config_setup の対話式 UI でシークレット項目はマスク表示。

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- research/factor_research.py はファイル冒頭に主要ロジックの骨子と定数があり、実装は継続的に拡張予定（現状一部関数が未完）。
- position_sizing.calc_position_sizes における価格欠損（price が 0 の場合）の扱いは TODO コメントあり。将来的に前日終値や基準価格でのフォールバックを検討中。
- P95 の計算は簡易実装（ソートして位置を取る）であり、大規模データや正確な統計ライブラリが必要な場合は改善の余地あり。
- run_monitoring が本番 sqlite を参照する仕様は意図的（監視対象は本番状態）だが、開発時に誤って本番 DB を操作しないよう運用上の注意が必要。

参考
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0"

もしリリースノートをセクション分け（Unreleased / 0.1.0 のように今後の変更を分ける）したい、あるいは各 PR/コミットへの紐付け（変更元の詳細）を追加したい場合は教えてください。