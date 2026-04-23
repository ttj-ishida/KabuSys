# Keep a Changelog
すべての変更はセマンティックバージョニングに従います。  
このファイルはプロジェクトの重要な変更点を人間が読める形式で時系列にまとめたものです。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

<!-- Unreleased セクションを将来の変更用に残します -->
## [Unreleased]

---

## [0.1.0] - 2026-04-23
初回リリース。

### Added
- 基本アプリケーションパッケージ `kabusys` を追加。
  - __version__ = 0.1.0 を設定。
  - パッケージトップで主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。

- 設定関連
  - `kabusys.config`:
    - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env と .env.local の読み込みルール（OS 環境変数を優先、.env.local は上書き）を実装。
    - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い）。
    - Settings クラスで環境変数をラップ：J-Quants / kabu API 設定、DB パス（DuckDB/SQLite）、PID/kill flag パス、監視スレッショルド、環境（development/paper_trading/live）やログレベルの検証ロジックなどを提供。
    - Paper Trading 用の設定（PAPER_FILL_MODE の検証、paper_sqlite_path）を追加。

  - `kabusys.config_setup`:
    - インタラクティブな .env 作成/更新ウィザード CLI を追加。
    - デフォルト値・選択肢・シークレット入力対応・既存 .env 読み込みのサポート。
    - 書き込みフォーマットを固定化し、.env の生成を自動化。

  - `kabusys.validate_config`:
    - 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml ファイル存在および（PyYAML がある場合）パース検査、KABUSYS_ENV=live 用の追加ガードを実装。
    - --strict オプションを実装（警告を FAIL 扱いにする）。

- 実行 / 監視エントリポイント
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を高く設定するユーティリティを起動直後に呼び出し。
    - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離するよう実装。
    - BrokerClientFactory を通じて適切なブローカクライアントを生成（Paper 用モックを想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。stop flag（data/stop_requested.flag）と PID ファイルの連携を実装。
  - `run_monitoring.py`:
    - SystemMonitor（監視ループ）起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動を明確化（監視は運用 DB を参照）。
    - stop flag ファイル検出でループ終了、例外はログに記録して次ポーリングへ継続。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - シグナルの選定ロジック（スコア降順、同点時は signal_rank でタイブレーク）select_candidates を追加。
    - 等金額配分 calc_equal_weights とスコア加重 calc_score_weights を追加（スコア合計が 0 の場合は等金額にフォールバックして警告）。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap: セクター集中上限チェック（既存保有を時価換算して上限超過セクターの新規候補を除外）を実装。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を実装（未知レジームは 1.0 にフォールバックし警告）。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes を実装。allocation_method として "risk_based", "equal", "score" をサポート。
    - リスクベースのポジションサイズ計算（risk_pct, stop_loss_pct に基づく）、1 銘柄上限（max_position_pct）、単元株（lot_size）丸め、aggregate cap（利用可能現金 available_cash を超える場合のスケーリング）を実装。
    - cost_buffer を導入し手数料/スリッページを保守的に見積もる。スケールダウン後の端数処理を残差法で分配。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - モメンタム / MA / ATR / 流動性などを計算するための設計と定数を追加。DuckDB を用いた prices_daily/raw_financials 参照方針および calc_momentum の骨組みを実装（詳細実装は継続）。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等の集計を行い、しきい値に基づく PASS/FAIL 判定を行う。デフォルトしきい値を設定（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）。
    - --from / --to / --db オプションで期間・DB 指定をサポート。PAPER_TRADING_SQLITE_PATH 環境変数も参照。

- ユーティリティ
  - `kabusys.utils.logging_setup`:
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーへ設定。既存ハンドラのクリアを実装。
    - LOG_DIR / LOG_LEVEL 環境変数や関数引数で挙動を上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`:
    - プラットフォーム差を吸収するプロセス優先度設定を実装（Windows の PRIORITY_CLASS、POSIX の nice 値に対応）。
    - CPU affinity 設定補助（最初の N コアに固定）を実装。
    - psutil を利用し、権限不足・未対応環境での例外をログ警告に変換して安全にスキップ。

- 監視用 DB 初期化フック
  - monitoring 用 DB 初期化関数 init_monitoring_db を参照して各起動スクリプトから呼び出し（冪等性を確保）。

### Changed
- 初期リリースのため該当なし（新規追加が主体）。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

---

注記:
- ここに記載した振る舞いはソースコードから推測したもので、実運用時の挙動（外部 API インテグレーション、DB スキーマ、ExecutionEngine の詳細実装など）は実際の他モジュールや設定ファイルに依存します。
- 将来的なリリースでは、monitoring と execution の DB 分離ルール、paper_trading の動作、レポートしきい値、ロギング/優先度設定の動作に関する後方互換性に注意してください。