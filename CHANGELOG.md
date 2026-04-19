# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

※ バージョンは src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 基本パッケージ構成と主要モジュールを追加
  - kabusys パッケージ本体（__version__ = 0.1.0）。
- 設定管理
  - kabusys.config
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
    - 複雑な .env 構文パース対応（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスで各種環境変数をラップ（J-Quants / kabuAPI / DB パス / Paper Trading 関連 / 監視閾値 等）。
    - 必須値未設定の場合は _require() が ValueError を送出して起動時に明確に通知。
    - PAPER_FILL_MODE の値検証、PAPER_TRADING_SQLITE_PATH の明示的設定をサポート。
- 設定ユーティリティ・検証
  - kabusys.config_setup
    - 対話式 .env ウィザード（既存値の再利用、シークレットのマスク表示、保存機能）。
    - .env ファイルを書き出すテンプレート機能。
  - kabusys.validate_config
    - .env と config/*.yaml の起動前検証ツール。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック。
    - PyYAML が未インストール時は YAML 検証をスキップして警告を出力。
    - --strict モードで警告を FAIL 扱いにできるオプション。
- 実行系スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動エントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（data/paper_trading.db）を使用し本番 DB と分離（コメントに MockBrokerClient の使用を明記）。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）によるプロセス制御。
    - BrokerClientFactory 経由のブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager の既定設定と初期ポートフォリオ値を broker.get_available_cash() から取得して設定。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（監視データは一貫した DB に蓄積）。
    - 停止フラグの検出によるループ終了処理と例外ハンドリング（check_once() の例外はログ出力して継続）。
- ログ・プロセス管理ユーティリティ
  - kabusys.utils.logging_setup
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数での上書き対応、ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout へフォールバック。
    - 既存ハンドラを安全に flush/close して再構成。
  - kabusys.utils.process_priority
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収したプロセス優先度設定 (high/normal/low)。
    - CPU affinity 設定ユーティリティ（最初の N コアにピン留め）。
    - 権限不足や未対応環境では警告を出してスキップする安全設計。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコア全0 の場合のフォールバックログ出力あり。
  - kabusys.portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap（既存保有を考慮し、売却予定銘柄除外、"unknown" セクターは上限対象外）。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing
    - 複数の配分方式（risk_based / equal / score）に対応した株数算出。
    - 単元株（lot_size）丸め、ポジション上限・投下資金上限の考慮、cost_buffer を用いた保守的なコスト計算。
    - aggregate cap 超過時にスケールダウンと残差処理（lot 単位での再配分）を実装。
  - kabusys.portfolio パッケージの __all__ を公開。
- 研究・ファクター計算スタブ
  - kabusys.research.factor_research
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計（calc_momentum 等の実装開始、DuckDB の prices_daily / raw_financials を参照する方針）。
- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成ツールを追加（SQLite DB を読み取り、稼働率・注文成功率・送信率・P95 レイテンシ等を算出）。
    - デフォルトの DB パスは data/paper_trading.db。--db / 環境変数で上書き可能。
    - P95 計算、複数の安全性チェック（データ存在チェック・SQL エラー時のフォールバック）を実装。
    - 判定基準（閾値）を定義: 稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms。
- その他ユーティリティ
  - kabusys/utils パッケージの基本ファイルを追加。

### Changed
- （初回リリースのため該当なし）

### Fixed / Hardened
- .env ファイルのパースを堅牢化（クォート内エスケープやインラインコメントの扱いを改善）。
- ロギング・ファイル作成失敗時のフォールバックと既存ハンドラの適切なクローズを実装してログの二重出力やファイルエラーを回避。
- プロセス優先度 / CPU affinity 設定で発生しうる権限例外をキャッチして安全にスキップするようにして、起動失敗を防止。
- run_monitoring のポーリング間隔指定で 0 以下や非整数値を指定した場合にデフォルトにフォールバックして ValueError を回避。
- run_execution / run_monitoring での DB 接続・init/close を try/finally で確実にクローズするように実装。

### Security
- .env ファイルのコメントに「.env は絶対に Git にコミットしないこと」を明記。
- config_setup による .env 書き出し時にシークレット項目は画面上でマスク表示（保存時はフル値を .env に書き込むので取り扱いに注意）。

### Notes / Known limitations
- factor_research の calc_momentum 等は DuckDB 上のテーブル構成（prices_daily / raw_financials）を前提としており、テーブルが存在しない場合は未実装・例外や None が返る可能性があります（設計ドキュメントに従ってテーブルを準備してください）。
- apply_sector_cap の露出計算で価格が 0.0 の場合に過小見積りになる注意書きあり（将来的に前日終値や取得原価でのフォールバック検討）。
- position_sizing は現状 lot_size を全銘柄共通としている（将来的に銘柄別 lot_map への拡張を想定）。

---

開発者向けの補足:
- 起動スクリプトは個々に setup_logging() と set_process_priority("high") を呼んでおり、運用環境でのログ出力・プロセス設定が統一されています。
- Paper Trading は物理 DB を分離しており、本番データと完全分離した検証が可能です。