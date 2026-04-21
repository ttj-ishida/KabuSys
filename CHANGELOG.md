Keep a Changelog に準拠した形式で、与えられたコードベースから推測した初期リリースの変更履歴を日本語で作成しました。リリース日には現在日付（2026-04-21）を使用しています。実際のプロジェクト履歴に合わせて日付や項目は調整してください。

CHANGELOG.md
=============
すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
----------
（未リリースの変更はここに記載）

[0.1.0] - 2026-04-21
-------------------
Added
- 基本アプリケーション初期実装を追加。
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV による paper_trading モード対応（本番 DB と分離し PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
    - BrokerClientFactory の利用によるブローカークライアント生成。
    - ExecutionEngine のスレッド起動、停止フラグ（data/stop_requested.flag）検知、PID ファイル管理。
    - RiskManager、OrderManager、Reconciler の組み立てとデフォルト設定（RiskConfig のデフォルト値を設定）。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor の初期化とポーリングループ実装（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能、デフォルト 60 秒）。
    - 停止フラグ検知での優雅な終了、例外ハンドリングでのログ出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の仕様。
- 設定管理
  - 環境変数読み込み・管理モジュールを実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出（.git / pyproject.toml を探索）に基づく .env 自動読み込み（.env → .env.local、OS 環境変数保護）。
    - 複雑な .env 行パース機能（export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントの扱い）を実装。
    - 各種設定プロパティ（DB パス、API トークン、閾値、環境種別判定、paper_trading 固有設定など）。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証、その他値検査。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - インタラクティブな .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - 対話形式で .env を生成・更新する CLI（シークレット入力マスク、デフォルト・選択肢サポート、保存確認）。
- 設定検証ツール
  - 起動前の設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DBパスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML 未インストール時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - --strict オプションで警告をエラー扱いにできる機能。
- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux/macOS/FreeBSD）の差異を吸収して優先度を設定（high/normal/low）。
    - CPU affinity 固定機能（最初の N コアにピン留め）を提供。
    - 権限不足や未対応プラットフォームに対する安全なフォールバックと警告出力。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順・タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計 0 のフォールバック）。
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存保有に基づくセクター上限判定、"unknown" セクター扱いのポリシー）。
    - calc_regime_multiplier（bull/neutral/bear 対応、未知のレジームはフォールバック1.0）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method（risk_based / equal / score）対応。
    - 損切り・リスクベース算出、単元株（lot_size）丸め、aggregate cap によるスケールダウン（端数処理で残差分の配分ロジック）。
    - cost_buffer による保守的コスト概算を考慮。
  - 上記をパッケージとしてエクスポート（src/kabusys/portfolio/__init__.py）。
- Paper Trading 検証ツール
  - 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs を参照して、稼働率、注文成功率、送信率、P95 レイテンシ等を集計。
    - しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
    - 日付フィルタ、DB パスの指定（オプション/環境変数）対応。
- リサーチ（ファクター計算）骨格
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数定義。
    - calc_momentum の実装開始（コメント・定数あり、実装途中のファイル切り出しあり）。

Changed
- （初回リリースのためなし）

Fixed
- .env パースの堅牢化（export 接頭辞・クォート内のバックスラッシュエスケープ・インラインコメント処理）を導入し、より柔軟な .env フォーマットに対応（src/kabusys/config.py）。
- ロギング設定: ログディレクトリ作成失敗時にプログラムが落ちないように StreamHandler のみで継続するフォールバックを追加（src/kabusys/utils/logging_setup.py）。
- プロセス優先度設定で未対応プラットフォームや権限不足に対して安全にスキップするよう改善（src/kabusys/utils/process_priority.py）。

Security
- （初回リリースのためなし）

Notes / Known issues
- src/kabusys/research/factor_research.py は現段階で実装が途中（calc_momentum の実装がファイル末尾で切れている）。今後のリリースで完成予定。
- position_sizing の価格欠損時の注記: price が欠損（0.0）の場合にエクスポージャーが過小評価される可能性があるため、将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO を残している（src/kabusys/portfolio/risk_adjustment.py）。
- PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など paper_trading 関連の挙動は設定に依存するため、本番運用前に validate_config と config_setup を用いて設定検証を行うことを推奨。

参考（主要ファイル）
- 起動/運用関連: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定関連: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ユーティリティ: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ポートフォリオ: src/kabusys/portfolio/*.py
- ツール: src/kabusys/tools/paper_verification_report.py
- リサーチ（未完）: src/kabusys/research/factor_research.py

--- 
この CHANGELOG は、提示されたコードの構成とコメントから推測して作成しています。実際のコミット履歴や開発ノートがある場合は、それに基づいて差分を反映してください。