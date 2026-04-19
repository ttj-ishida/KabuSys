# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog 準拠の形式で記載しています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- その他は該当箇所を使用

最新リリース
=============

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション骨格を初回リリース。
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト: 60秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイル検出で行う。
    - Monitoring は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Mock ブローカ（分離された data/paper_trading.db）を使用する挙動をサポート。
    - スレッドでエンジンを実行し、stop flag による安全停止処理を実装。
    - PID ファイル出力サポート。
- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定（DBパス、APIトークン、ログレベル、しきい値等）を提供。
    - .env/.env.local の自動読み込み（プロジェクトルート検出）と KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
    - .env のパースは export プレフィックス、クォート文字、インラインコメント等に対応。
    - is_live / is_paper / is_dev 等のユーティリティプロパティを提供。
- 設定ツール / 検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目はマスク表示。
    - デフォルト値と選択肢を提示し、最終確認後に .env を書き出す。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、PyYAML が有れば YAML のパース検証を実施。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決やハンドラの二重設定防止、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）を行う set_process_priority を追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（利用できない環境では安全にスキップ）。
- ポートフォリオ構築（純粋関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄の除外、unknown セクター扱いの挙動を明記）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジックを実装。
    - 単元株丸め（lot_size）、max_position_pct / max_utilization による上限、cost_buffer を考慮した aggregate cap スケーリング（端数処理のための remainder 分配ロジック）を含む。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB を読み、稼働率、注文成功率、送信率、P95 レイテンシなどを集計するレポート生成 CLI を追加。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）による PASS/FAIL 判定を実装。
    - 日付範囲指定（--from / --to）や DB 指定（--db）に対応。
- データリサーチ基盤（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの枠組み（モメンタム、移動平均乖離、ATR、流動性等）を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針で実装開始（モジュール途中まで実装）。

Changed
- プロジェクト構成
  - 複数の実行スクリプトとユーティリティを統合し、アプリケーションの起動と環境構築を容易にした。

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details
- run_monitoring と run_execution の両方で起動直後に set_process_priority("high") を呼び、重要プロセスの優先度を上げる設計。
- Settings による設定取得は遅延評価（プロパティ）で行い、必要時にのみ環境変数の存在や妥当性チェックを行う。
- .env パーサは実運用でありがちなケース（export プレフィックス、クォート文字、エスケープ、インラインコメント）に対応しており、自動読み込みはプロジェクトルートの検出に依存する。
- Paper Trading は本番 DB と完全分離する設計（settings.paper_sqlite_path を利用）。
- ログは stdout に出力することで cron / systemd などでのリダイレクト運用を想定。

開発予定 / TODO
- research/factor_research.py の完全実装（コメントにあるファクター群の計算ロジックの完成）。
- position_sizing の lot_size を銘柄別にサポートする拡張（stocks マスタに単元情報を持たせる等）。
- price 欠損時のフォールバック価格（前日終値や取得原価）の導入（risk_adjustment 内の TODO）。
- 単体テスト・ E2E テストの整備（現状はロジック実装が中心）。
- ドキュメント（PortfolioConstruction.md など参照に記載されている外部ドキュメントの公開）。

未収録 / 開発中
- 一部モジュールはコメントに「将来拡張」や「TODO」が残っています。実運用前にこれらの点を確認してください。

-- END --