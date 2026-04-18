# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはリポジトリ内のコードから推測して作成しています（実装の意図・注記を含みます）。

フォーマット:
- 重大な変更はセクションごとに分類（Added / Changed / Fixed / Deprecated / Removed / Security）
- 各バージョンは日付を付記（リリース日: 本 CHANGELOG 作成日）

---

## [Unreleased]

### Added
- 監視・実行・検証のための起動スクリプト群を追加
  - run_execution.py: ExecutionEngine を起動するメインスクリプト（スレッド駆動、停止フラグ/ pid 管理、paper_trading 用 DB 分離）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ監視）。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数読み込みロジック（プロジェクトルート検出、.env / .env.local の自動読み込み、各設定値のバリデーション）。
  - config_setup.py: 対話式 .env 作成・更新ウィザード。
  - validate_config.py: 起動前チェック CLI（必須環境変数 / YAML ファイル / 本番ガード等）。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: stdout ストリームハンドラ + 日次ローテートファイルハンドラ（既存ハンドラのクリア、LOG_DIR/LOG_LEVEL 解決）。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定 & CPU affinity の簡易 API（Windows / POSIX の差分吸収）。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）
  - portfolio/portfolio_builder.py: 候補選択・等重/スコア加重の重み計算。
  - portfolio/risk_adjustment.py: セクター上限適用、レジーム乗数計算（bull/neutral/bear のマッピング）。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score、lot 単位丸め、aggregate cap のスケーリング）。
- Paper Trading 向け検証レポートツールを追加
  - tools/paper_verification_report.py: paper_trading SQLite DB から稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定レポートを出力。
- research/factor_research.py（ファクター計算基盤）を追加（Momentum 等の計算を含む設計・一部実装）。
- パッケージメタ
  - src/kabusys/__init__.py にバージョン (0.1.0) を追加。

### Changed
- .env パーサの挙動強化（config._parse_env_line）
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を実装。
  - クォートなし値に対するインラインコメント判定の改善（直前に空白/タブがある場合のみコメントとみなす）。
- 自動 .env 読み込みの挙動
  - プロジェクトルート (.git または pyproject.toml) を起点に .env/.env.local を読み込み。
  - OS 環境変数を保護しつつ .env.local で上書き可能（.env.local が優先）。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- logging_setup
  - 既存ハンドラを明示的に flush/close してから削除し、二重設定を防止。
  - StreamHandler は stdout を使用（cron 等で stdout/stderr を一本化する運用を想定）。
  - 日次ローテートファイルハンドラはログディレクトリ作成に失敗した場合はスキップし、コンソールのみで継続。
- process_priority
  - Windows / POSIX の差分を抽象化して API を提供。権限不足や未対応 OS の場合は警告ログでスキップするフェイルソフト挙動。
- run_execution / run_monitoring
  - 起動直後にプロセス優先度を "high" に設定する処理を追加。
  - DB 初期化（init_monitoring_db）を冪等に行い、monitoring 用テーブルの存在を保証。
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path（data/paper_trading.db）を使用して本番 DB と完全分離する設計（コメントで明記）。
  - run_monitoring は環境に関係なく production sqlite_path を使用する旨の仕様。
  - ポーリングループで monitor.check_once() が例外を投げた場合でもログ出力して次のポーリングに進む耐障害性を追加。
  - 停止フラグ（data/stop_requested.flag）を検知して安全に終了する処理を両スクリプトに実装。

### Fixed
- calc_score_weights: 全スコア合計が 0 の場合は等金額配分にフォールバックし、WARNING を出すようにした（極端なスコア分布への耐性向上）。
- apply_sector_cap: "unknown" セクターはセクター上限の判定対象外とし、既知セクターのみをブロックするようにした（データ欠損時に過剰な除外が発生しないように改善）。
- position_sizing: aggregate cap スケーリング時の丸めロジックを改善し、lot_size 単位で残余を再配分するアルゴリズムを導入（再現性のため安定ソートを使用）。

### Known issues / Limitations
- research/factor_research.py は実装途中の箇所が存在する（ファイル末尾で途中切れの目印あり）。完全実装とテストが必要。
- 一部 TODO コメントあり（価格欠損時のフォールバック価格、銘柄別 lot_size 対応など）。
- 実行には外部モジュール（psutil、duckdb、PyYAML など）が必要。PyYAML がない場合は config/*.yaml の検証はスキップされる仕様。

---

## [0.1.0] - 2026-04-18

初回リリース想定のまとめ（上記 Added の内容を含むリリース）。  
主なポイント:
- KabuSys のコア基盤を実装
  - 設定読み込み・ウィザード・検証ツール
  - 実行（ExecutionEngine）および監視（SystemMonitor）起動スクリプト
  - Paper Trading と本番 DB の明確な分離
  - ログ設定ユーティリティ（stdout+日次ローテート）
  - プロセス優先度 / CPU affinity ユーティリティ
  - ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算・リスク調整）
  - Paper Trading 検証レポート生成ツール
  - 初期のファクター計算モジュール（momentum 等。実装継続予定）

バグ修正・強化点:
- .env パースと自動読み込みの堅牢化
- position sizing / weighting のフォールバック・丸め処理改善
- 監視・実行ループでの例外耐性と停止フラグ処理

セキュリティ注意事項:
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも明記）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定などに注意するチェックを validate_config に実装。

---

注: 本 CHANGELOG は提示されたソースコードから推測して作成したものであり、実際のコミット履歴ではありません。必要であれば各ファイル変更の想定差分（個別のコミットメッセージ風）や追加のリリースノート（例: マイナー / パッチリリース案）も作成します。