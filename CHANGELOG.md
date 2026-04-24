CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注記
----
- 本 CHANGELOG はリポジトリ内のコード構成および実装から推測して作成しています。コミット履歴そのものではありません。
- バージョンは src/kabusys/__init__.py の __version__（0.1.0）に基づいています。

Unreleased
----------
（現時点の作業中や次回リリースで予定している変更点をここに記載してください。）

0.1.0 - 2026-04-24
------------------

Added
- 基本アーキテクチャを実装
  - 自動売買システム「KabuSys」の初期機能群を追加。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループ終了。
    - 監視用 DB は環境に依らず本番 sqlite_path を利用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB から分離。
    - BrokerClientFactory によりブローカークライアントを切替可能（モック/実環境対応）。
    - 実行中は PID ファイルを管理し、停止フラグでセッション停止を行う。

- 設定管理・検証・ウィザード
  - config.py
    - 環境変数/ .env の読み込みと Settings クラスを実装。
    - プロジェクトルート自動探索（.git / pyproject.toml）に基づく .env 自動読み込み（無効化フラグあり: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パースはクォート・エスケープ・インラインコメントに対応。
    - 各種設定プロパティ（DB パス、API トークン、監視閾値、環境判定など）を提供。
  - validate_config.py
    - .env および config/*.yaml の起動前検証用 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス・YAML の存在とパース（PyYAML 利用可否に対応）、本番環境向けガードを実装。
    - --strict オプションで警告も失敗扱いにするモードを提供。
  - config_setup.py
    - インタラクティブな .env 作成・更新ウィザードを実装。
    - セクション毎の説明、シークレット値のマスク、デフォルト値のサポート、保存確認および .env 生成機能を提供。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を統一設定するユーティリティを実装。
    - 環境変数 LOG_LEVEL / LOG_DIR との連携、既存ハンドラのクリア、ファイルハンドラ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac等）を吸収してプロセス優先度を設定する機能を実装。
    - CPU affinity 設定ユーティリティも提供（指定コア数に固定）。
    - 権限不足や未サポート OS に対する安全なフォールバック（警告出力）あり。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、同点は signal_rank）と最大保有数トリミングを実装。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を実装。全スコアが 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有を基にセクター別エクスポージャーを計算し、上限超過セクターの候補を除外。
    - レジームに応じた投資乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピングと未知値のフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ計算ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap、コストバッファ（手数料・スリッページ概算）を考慮したスケーリング、残差処理を実装。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード実行結果の検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を行う。
    - CLI 引数 --from / --to / --db に対応。環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能。
    - デフォルトの合格基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。

- 研究・因子計算基盤（未完だが基盤実装あり）
  - research/factor_research.py
    - Momentum 等のファクター計算に必要な定数と calc_momentum の骨格を実装（DuckDB 接続を受け prices_daily / raw_financials を利用する設計）。
    - 計算ハイパーパラメータ（窓長、スキャン範囲等）を定義。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （該当なし）

Security
- （該当なし）

Notes / 実装に関する補足
- DB 分離
  - ペーパートレードは paper_sqlite_path による専用 DB を使用し、本番用 monitoring DB（sqlite_path）と完全に分離する設計。
- 設定の安全性
  - .env はデフォルトで Git にコミットしない旨を README/ウィザードのヘッダに明記する設計。
- フォールバックと堅牢性
  - 各種ユーティリティは（ファイル作成失敗、権限不足、必要ライブラリ未インストール等）に対して警告を出しつつ安全にフォールバックする実装になっている。
- 今後の拡張候補（コード内コメントより推測）
  - position_sizing の銘柄別 lot_size 対応（stocks マスタとの連携）。
  - apply_sector_cap の価格欠損時のフォールバック（前日終値等）。
  - factor_research の各ファクター計算（Value, Volatility, Liquidity）の実装完了。

作者・貢献
- 実装はリポジトリ内の各モジュール（src/kabusys 以下）に含まれる機能に基づき推測してまとめています。

----- 
（以降のリリースでは、各コミット / チケット番号・差分リンク等を添えて詳細に履歴を残してください。）