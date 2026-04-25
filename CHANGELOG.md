CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-25
-------------------

Added
- 基本アプリケーション骨格を追加
  - パッケージ初期バージョンを 0.1.0 としてリリース（src/kabusys/__init__.py）。
- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアントのファクトリ経由で実行環境に応じたクライアントを生成。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による安全な停止処理、実行中 PID ファイル（data/execution.pid）管理を含む。
  - システム監視起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を参照して監視テーブルを初期化。
    - stop フラグファイル検知によるループ終了、例外発生時のログ保護。
- 設定・環境変数ツール
  - Settings クラス（src/kabusys/config.py）を実装して環境変数を型安全に取得。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。
    - Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）、監視しきい値や PID/killswitch 関連設定を含む。
    - 環境名（KABUSYS_ENV）や LOG_LEVEL の妥当性チェック。
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）を追加。
    - 各設定項目の説明・デフォルト表示・シークレットマスクに対応し .env を生成/更新。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数の有無、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML がある場合）。
    - --strict モードで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX (Linux, macOS, FreeBSD) を抽象化して優先度設定（high/normal/low）を行う。
    - CPU affinity を最初 N コアに固定する機能を提供。
    - 権限不足や未対応 OS 時は警告を出して安全にフォールバック。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + signal_rank によるタイブレーク
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重（スコア全て 0 の場合は等分にフォールバック）
  - セクター集中制限とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率に基づいて当日の新規候補をフィルタ
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）
  - ポジションサイズ算出（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score ベースの株数算出、単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）調整、コストバッファ考慮、端数補正ロジックを実装
  - これらをまとめたモジュール公開（src/kabusys/portfolio/__init__.py）
- Paper Trading 検証用ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。
    - PAPER_TRADING_SQLITE_PATH（または --db 引数）からデータを読み、稼働率・注文成功率・送信率・レイテンシ等を算出して PASS/FAIL 判定するレポートを生成。
    - P95 の算出、期間指定（--from / --to）に対応。閾値はソース内定義で調整可能。
- 研究（Factor）モジュール（開始実装）
  - factor_research（src/kabusys/research/factor_research.py）を追加（モメンタム等ファクターの計算設計、DuckDB 経由での prices_daily / raw_financials 参照を想定）。一部実装が継続中。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- 監視用 DB 初期化関数 init_monitoring_db を起動時に呼び出し、監視テーブルが存在することを冪等的に保証。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）を使った外部制御に対応しており、長時間デーモン運用を想定。
- ロギング設定は既存ハンドラを一度クリアしてから再構成することで二重出力を避ける設計。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされるため、パッケージ配布後も安全に動作する。

今後の予定（例）
- factor_research の完全実装（全ファクター計算の完成）
- テスト・CI の追加、型チェック・型ヒントの強化
- 個別銘柄ごとの lot_size 管理（stocks マスタの導入）
- モジュール間のドキュメント（API ドキュメント、設計書）整備

---
この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートやユーザー向けドキュメントを作成する際は、差分履歴（git log /タグ）や実際の変更記録を参照してください。