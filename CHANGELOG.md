# Changelog

すべての重要な変更点をこのファイルに記載します。フォーマットは “Keep a Changelog” に準拠しています。  
バージョニングは SemVer に従います。

## [Unreleased]

## [0.1.0] - 2026-04-18

Added
- 初期リリースとして以下の主要機能を追加。
  - 基本アプリケーション情報
    - パッケージバージョンを src/kabusys/__init__.py にて `0.1.0` として定義。
  - 環境設定 / 起動支援
    - 対話式 .env ウィザード（CLI）を追加（src/kabusys/config_setup.py）。
      - .env の初期作成・更新をサポート。シークレット項目のマスク表示、選択肢・デフォルト提示、既存値の再利用。
      - 書き出しフォーマットが固定化され、.env の Git コミット禁止コメントを含む。
    - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
      - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DBパスや config/*.yaml の存在チェック。
      - `--strict` オプションで警告をエラー扱いにできる。
      - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出す。
    - 環境変数自動ロード機能（src/kabusys/config.py）。
      - プロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を読み込み。OS 環境変数は保護。
      - LOAD ロジックは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
      - .env パーサは `export KEY=val`、クォート文字列、エスケープ、インラインコメント処理をサポート。
    - Settings クラス（src/kabusys/config.py）を追加。
      - 各種環境変数（J-Quants, kabuAPI, DuckDB/SQLite パス、Paper Trading 設定、監視閾値 等）をプロパティ経由で取得・検証。
      - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL などの妥当性チェックを実装。

  - 起動スクリプト / デーモン系
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）。
      - プロセス優先度を高く設定して起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視 DB は環境にかかわらず本番 sqlite_path を使用して初期化。
      - 停止フラグ（data/stop_requested.flag）による安全停止をサポート。
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
      - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
      - 停止フラグと PID ファイル管理、デーモン（スレッド）での実行・停止処理を実装。

  - ロギング / プロセス制御ユーティリティ
    - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
      - stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
      - ログディレクトリの自動作成処理、既存ハンドラのクリーンアップ、LOG_LEVEL / LOG_DIR の解決を行う。
    - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
      - Windows / POSIX（Linux, macOS 等）差分を吸収して優先度設定を試みる。失敗時は警告出力でフォールバック。
      - CPU affinity 固定機能を提供（指定コア数の先頭 N コアにピン留め）。
      - psutil を利用し、アクセス権限や未サポート環境でも安全に動作。

  - ポートフォリオ構築ライブラリ（純粋関数群）
    - 候補選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
      - select_candidates（スコア降順、signal_rank によるタイブレーク）
      - calc_equal_weights（等金額配分）
      - calc_score_weights（スコア加重、全スコアが 0 の場合は等金額にフォールバック）
    - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
      - apply_sector_cap（既存保有のセクター比率に基づき新規候補を除外）
      - calc_regime_multiplier（"bull" / "neutral" / "bear" に対する投下比率乗数）
      - unknown セクターの扱い、ログ出力によるデバッグ情報を含む
    - 株数決定・投下資金制御（src/kabusys/portfolio/position_sizing.py）
      - allocation_method（"risk_based", "equal", "score"）対応
      - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）の考慮
      - aggregate cap によるスケーリング（残余キャッシュに応じたロット単位での追加配分アルゴリズム）
    - これらのエクスポートをまとめたパッケージインターフェース（src/kabusys/portfolio/__init__.py）。

  - Paper Trading 検証ツール
    - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
      - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から期間フィルタでデータを集計してレポート出力。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
      - 閾値を超えた場合は FAIL、そうでなければ PASS として判定。
      - P95 算出、日付フィルタ、コマンドライン引数（--from/--to/--db）をサポート。

  - Research（ファクター計算）基盤
    - ファクター計算モジュールの骨格（src/kabusys/research/factor_research.py）を追加。
      - Momentum / Value / Volatility / Liquidity 系の計算を想定。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
      - モメンタム計算（calc_momentum）のインターフェース・定数を導入（実装は継続中 / 一部未完）。

Changed
- なし（初期リリース）。

Fixed
- なし（初期リリース）。

Notes / Implementation details
- 監視（run_monitoring）は MONITOR_POLL_INTERVAL によるポーリング間隔の上書き、0 以下の不正値はデフォルト（60 秒）にフォールバックする実装。
- run_execution は paper_trading と live を明確に分離し、paper_trading 時は別 DB を利用することで本番データと完全分離。
- .env の自動ロードでは既存 OS 環境変数を上書きしない（.env.local は上書き可だが OS 環境は保護）。
- logging_setup はログファイル出力に失敗した場合でも stdout のみで動作を継続するよう設計。
- process_priority / set_cpu_affinity は権限不足や未サポート OS の場合は警告を出して処理をスキップする安全対策あり。
- factor_research モジュールはファクター計算の方針とスケルトンを提供。未完成の関数・注記が残っているため利用時は注意。

Known issues / TODO
- position_sizing の価格フォールバック処理（price が欠損時の扱い）が TODO としてコメントあり。将来的に前日終値や取得原価で補完する予定。
- factor_research の実装が一部未完（ファイル末尾で途切れている）ため、フルファクター計算は今後の実装を要する。
- 一部の機能（例: DuckDB に依存する分析、PyYAML を用いる構成検証）は外部パッケージのインストール有無により挙動が変わる点に注意。

---

（今後のリリースでは bugfix / change / security / deprecated 等のカテゴリを適宜追加してください。）