# Changelog

すべての重要な変更をここに記録します。  
このファイルは「Keep a Changelog」の形式に従います。  
リリースはセマンティックバージョニングを想定します。

※ 本履歴はソースコードから機能・変更点を推測して作成しています。

## [Unreleased]

### Added
- 今後の改善候補・未実装リストを追加
  - 銘柄ごとの単元（lot_size）を stocks マスタで管理する拡張
  - 価格欠損時のフォールバック（前日終値や取得原価）ロジック
  - research モジュールの残り実装（ファクター計算の続き）

### Changed
- 監視・実行関連の運用改善案を記載（ログ/フラグ/プロセス管理の追加改善）

### Fixed
- （将来対応予定の既知制約の明示）

---

## [0.1.0] - 2026-04-18

初回公開リリース。以下の主要機能を実装・提供します。

### Added
- アプリケーション基盤
  - パッケージ初期化（kabusys.__version__ = 0.1.0）
  - Settings クラスによる環境変数/設定値集中管理（config.py）
    - 自動 .env ロード（.env / .env.local、OS 環境変数優先）
    - 必須変数検証ヘルパー（_require）
    - 各種パス・フラグ・閾値・モードのプロパティ（duckdb/sqlite/paper_trading 等）
    - PAPER_FILL_MODE の妥当性チェック
    - 環境モード判定ヘルパー（is_live / is_paper / is_dev）
- 起動スクリプト
  - 実行エンジン起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と分離
    - BrokerClientFactory を使用したブローカークライアント生成
    - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）
    - ストップフラグ（data/stop_requested.flag）検知で安全停止
    - 起動時にプロセス優先度を High に設定
  - 監視ループ起動スクリプト（run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を参照して監視データを記録
    - SystemMonitor を用いた単一チェックループ（check_once）と例外耐性
- 設定サポートツール
  - 対話式 .env 作成ウィザード（config_setup.py）
    - 各種設定項目の入力支援、既存 .env 読込、ファイルへの安全な書き出し
  - 設定検証 CLI（validate_config.py）
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml 存在チェック
    - PyYAML がない場合は YAML 検証をスキップして警告
    - 本番環境時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）
    - --strict オプションで警告を失敗扱いにできる
- ロギング・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ（utils/logging_setup.py）
    - stdout ストリームハンドラと日次ローテートファイルハンドラを設定
    - LOG_DIR 作成失敗時はファイル出力をスキップし、コンソール出力のみで継続
    - 環境変数/引数からログレベル・ログディレクトリを決定
  - プロセス優先度・CPU affinity 設定（utils/process_priority.py）
    - Windows / POSIX を吸収する抽象化
    - set_process_priority(level)（high/normal/low）と set_cpu_affinity(n)
    - 権限不足や未対応 OS の場合は安全にスキップして警告ログ
- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークの実装
    - calc_equal_weights, calc_score_weights（スコア全0時は等配分へフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の既存保有比率チェックと候補除外
    - calc_regime_multiplier: レジーム別乗数（bull/neutral/bear）と未知レジームのフォールバック
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数計算
    - aggregate cap（available_cash を超えた場合のスケーリング）と lot_size（単元）丸め
    - cost_buffer を用いた保守的なコスト見積もりと再分配ロジック
    - TODO コメントで将来の拡張点を明示（銘柄別単元マップ、価格フォールバック等）
- リサーチ・ファクター計算基盤
  - research.factor_research の骨組み（モメンタム等の定数・calc_momentum の冒頭実装）
    - DuckDB 接続を受け、prices_daily / raw_financials に基づくファクター計算設計
- Paper Trading 向け検証ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から指標を抽出してレポート出力
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等
    - 日付フィルタ、P95 計算、閾値を満たすかの PASS/FAIL 判定を実装
    - DB が存在しない・テーブル不足時のフォールバックとエラーメッセージ

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を検知してデフォルトにフォールバックする（0 以下や非整数を拒否）。
- run_execution は paper_trading モードと本番モードの DB を明確に分離する（paper_trading は PAPER_TRADING_SQLITE_PATH）。
- logging_setup はログディレクトリ作成失敗時に安全にフォールバックし、stderr ではなく stdout にストリーム出力する設計。
- process_priority は権限やプラットフォーム差分を考慮して安全にスキップ可能。
- validate_config は PyYAML 未導入環境でも graceful に警告を出しつつ実行できるよう設計。

### Known issues / TODO
- position_sizing: price が欠損した場合にエクスポージャーが過少見積りされる可能性あり（コメントに取り扱い注意・将来のフォールバック実装予定）。
- research.factor_research の実装が途中で切れている（ファクター計算ロジックの継続実装が必要）。
- 銘柄別の単元（lot_size）や手数料・スリッページのより精緻な取り扱いは今後の拡張対象。
- config/*.yaml が存在しない場合の自動生成スクリプトが参照されているが、運用時の整備が必要。

---

（補足）
- 本 CHANGELOG はソースコードのコメント・関数名・設計意図から推測して作成しています。実際のリリース日やバージョン方針はプロジェクトの運用に合わせて調整してください。