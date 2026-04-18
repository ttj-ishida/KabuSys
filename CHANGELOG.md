# Changelog

すべての重要な変更を保持するために Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、このCHANGELOGは与えられたコードベースの内容から推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-18

### Added
- 基本的なアプリケーション骨組みを追加
  - パッケージ初期バージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（data/paper_trading.db など）を使用して本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを生成。設定に応じて MockBrokerClient を利用可能。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による外部停止をサポート。
    - 実行中 PID を data/execution.pid に保存する仕組みを統合。
  - システム監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出：.git または pyproject.toml ベース）。
    - .env/.env.local の読み込み順・上書きルールを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 必須/任意の環境変数、パス、Paper Trading 関連設定、監視閾値や pid/kil_flag 関連のプロパティを提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証を含む。
- 設定関連 CLI ツール
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の基本的な存在チェックおよび簡易検証。
    - --strict オプションで警告をエラー扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
  - 環境設定ウィザード（対話式 .env 作成/更新）を追加（src/kabusys/config_setup.py）。
    - 対話的プロンプト、既存 .env の読み込み、保存ロジックを実装。
    - デフォルト値やシークレットマスク表示、保存前の確認などを実装。
- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout ストリームハンドラと日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / app_name による設定。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX 差分を吸収して優先度（high/normal/low）を設定。
    - CPU affinity を指定コア数に固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は安全にスキップして警告を出力。
- ポートフォリオ構築関連モジュール（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点は signal_rank でタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア比率配分、全スコア0 の場合は等金額にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存ポジションのセクター比率を計算して新規候補を除外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく資金乗数）
  - 株数決定・単元丸め・集計キャップ（src/kabusys/portfolio/position_sizing.py）
    - allocation_method="risk_based" / "equal" / "score" をサポート
    - lot_size（単元株）に基づく丸め、コストバッファを考慮した aggregate cap のスケーリング
    - price 欠損や上限チェックに対するログ出力やフォールバックを実装
  - ポートフォリオモジュールのエクスポートを定義（src/kabusys/portfolio/__init__.py）
- Paper Trading 検証レポート
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間（--from/--to）または DB 全期間で Paper Trading の健全性を検証し、稼働率・注文成功率・送信率・レイテンシ（P95）等を集計してレポート出力。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95レイテンシ 200ms）による PASS/FAIL 判定。
    - DB が存在しない場合のエラーメッセージや、テーブル欠如時に安全に N/A を返す処理を備える。
- 研究用ファクター計算モジュール（初期実装）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数定義を追加。Momentum 関連の計算関数 calc_momentum の実装開始（途中まで）。DuckDB の prices_daily テーブルを参照する設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （該当なし）

---

注記:
- 上記はソースコードから推測した機能一覧と振る舞いをまとめたものであり、実行環境や外部依存（psutil, duckdb, PyYAML など）の有無により一部機能は起動時に振る舞いが異なる場合があります。
- config/*.yaml の実際の内容や ExecutionEngine / Broker 実装の詳細（注文ロジック、マッチング等）はこのコードスニペットからは参照できないため CHANGELOG には含めていません。必要であれば該当ファイル群を解析して追記します。