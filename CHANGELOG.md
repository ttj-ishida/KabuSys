CHANGELOG
=========

All notable changes to this project will be documented in this file.
フォーマットは "Keep a Changelog" に準拠します。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の注記
- その他の注記は必要に応じて追加します。

Unreleased
----------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-23
-----------------

Added
- 初期リリースを公開。
- 基本的な自動売買システム「KabuSys」のコア機能を追加。
  - パッケージ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
- 設定管理:
  - Settings クラスによる環境変数ベースの設定読み取りを追加（src/kabusys/config.py）。
  - .env 自動読み込み機能（プロジェクトルートに基づく検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パースの強化: export プレフィックス、クォート文字、エスケープ、行内コメントなどに対応。
  - 各種環境変数の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）やデフォルト値を提供。
- 環境設定ウィザード:
  - 対話式 .env 作成/更新ツールを追加（src/kabusys/config_setup.py）。
  - J-Quants / kabuAPI / DB パス / LOG_LEVEL / Kill Switch 等の入力項目をサポート。機密項目はマスク表示。
- 設定検証 CLI:
  - .env と config/*.yaml の存在・基本整合性をチェックするツールを追加（src/kabusys/validate_config.py）。
  - --strict オプションで警告を FAIL 扱いにできる。
- 起動スクリプト:
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用（完全分離）。
    - BrokerClientFactory を介したブローカークライアント生成（モック／本番切替）。
    - ExecutionEngine を別スレッドで実行し、停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - pid ファイル書き込みのサポート（data/execution.pid）。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor をポーリング実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計。
- データベース / 分析:
  - DuckDB と SQLite を併用する設計。設定でパス指定可能（DUCKDB_PATH, SQLITE_PATH）。
  - monitoring 用の DB 初期化ユーティリティ（init_monitoring_db）を利用（冪等性確保）。
- ポートフォリオ構築ライブラリ:
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順選択（タイブレークに signal_rank を利用）
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全 0 の際はフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター上限超過時に候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: レジームごとの投下資金乗数 ("bull"/"neutral"/"bear")、未知レジームはフォールバック
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の割当方式に対応
    - lot_size（単元株）に基づく丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積もり等を実装
- ユーティリティ:
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout ストリームハンドラ + 日次ローテートのファイルハンドラをルートロガーに設定
    - 既存ハンドラの重複防止のため一度クリアして再設定
    - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収し、"high"/"normal"/"low" レベルを指定可能
    - set_cpu_affinity により最初の N コアにプロセスを固定可能（権限不足は警告でスキップ）
- Paper Trading 向けレポート:
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
    - system_status / trade_logs / risk_logs を集計し稼働率、注文成功率、送信率、P95 レイテンシ等を算出
    - デフォルト閾値（稼働率 >= 99%、成立率 >= 90% 等）で PASS/FAIL を判定
    - --from / --to / --db オプションをサポート
- 研究用ファクター計算（初期実装 / 一部未完）:
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加（モメンタム等の設計、一部実装開始）
  - DuckDB を用いた prices_daily / raw_financials 参照を想定

Changed
- （初版のため該当なし）

Fixed
- 環境変数ロード・パースに関する堅牢性の向上:
  - export プレフィックスやクォート、エスケープ、行内コメント処理を実装し、柔軟な .env パースを実現。
- ロギング設定:
  - 起動スクリプト複数回呼び出し時のハンドラ二重登録を防止するため、既存ハンドラの flush/close と削除を追加。

Security
- .env ファイルは機密情報を含むため、config_setup にて ".env は絶対に Git にコミットしないこと" を注意喚起。
- Settings._require() は必須環境変数未設定時に ValueError を投げ、起動時に明示的に失敗するようにして誤った起動を防止。

Notes / Implementation details
- Paper Trading（ペーパートレード）は本番 DB と分離される設計（PAPER_TRADING_SQLITE_PATH / settings.paper_sqlite_path）。
- run_monitoring は監視 DB（sqlite）を本番 sqlite_path で常に使う点に注意。監視データは本番口座に依存しない想定。
- process_priority / cpu_affinity の適用は権限（root/admin）や OS の実装依存により失敗する可能性があり、その場合は警告でスキップされる。
- research/factor_research.py はモジュール設計・定数等が含まれるが、関数 calc_momentum の実装が途中で終わる（ファイル末尾が未完）。今後のリリースで完成予定。

今後の予定（期待される改善点）
- factor_research の完全実装（モメンタム・ボラティリティ・バリュー・流動性等）。
- ExecutionEngine / Broker クライアント関連の詳細実装・テスト整備（retry / error-handling 等）。
- 監視・アラート（LINE 通知）機能の追加・強化。
- 単体テストと CI の整備。

--- 

（補注）
この CHANGELOG は現在のソースコードの構造・コメント・仕様から推測して作成しています。実際のリリースノートとして採用する場合は、実装者による確認と必要に応じた修正を行ってください。