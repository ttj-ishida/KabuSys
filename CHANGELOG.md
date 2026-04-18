# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従い、セマンティックバージョニングを想定します。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-18
初回リリース。本リポジトリの主要機能・CLI・ユーティリティを実装しました。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止はプロジェクト内 data/stop_requested.flag ファイルを検知して行う。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介して本番 / モックブローカーを切り替え可能。
    - エンジンの停止は data/stop_requested.flag の検知で行う。実行中は data/execution.pid に PID を管理。

- 設定関連
  - config.py
    - Settings クラスを追加。環境変数から各種設定値を取得するためのプロパティを提供（DB パス、API トークン、監視閾値等）。
    - 自動 .env ロード機能を実装（プロジェクトルートの判定: .git または pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースの強化: export 構文やクォート内のバックスラッシュエスケープ、行内コメントの扱いなどに対応。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘匿項目は入力時にマスク表示し、保存前に確認を行う。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL 値検証、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が存在する場合）などを実装。
    - --strict オプションで警告を失敗扱い（exit(1)）にできる。

- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルのスコア順ソートと上位 N 件選択。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限の適用（既存保有のセクター別エクスポージャーを計算し、上限超過セクターの候補除外）。"unknown" セクターは上限除外対象外として扱う。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームは警告を出して 1.0 にフォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数計算、単元株（lot_size）丸め、per-stock・aggregate のキャップ適用、コストバッファ対応、スケールダウン時の端数処理（残差に応じた追加配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）をデフォルトで設定。ログディレクトリは環境変数 LOG_DIR または既定の logs/。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。ファイル出力はディレクトリ作成失敗時にフォールバックで無効化。
  - utils/process_priority.py
    - set_process_priority(level) を追加し、Windows / POSIX の差を吸収してプロセス優先度（nice / Windows priority class）を設定。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアに固定する機能を提供（権限不足や未サポート環境では警告を出してスキップ）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（data/paper_trading.db）を集計して検証レポートを出力する CLI を追加。
    - --from / --to / --db オプション対応。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - デフォルトの閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms。

- リサーチ
  - research/factor_research.py
    - DuckDB 接続を受け取りモメンタム / バリュー / ボラティリティ / 流動性などの定量ファクターを計算するためのモジュール骨格を追加（prices_daily / raw_financials テーブル参照）。モメンタム計算などの定数とユーティリティが実装済み（実装途中ファイルあり）。

- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 として設定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 実装上の留意点
- .env 自動ロードはプロジェクトルートが検出できない場合は無効化されます（パッケージ配布後に安全に動作するよう設計）。
- MONITOR_POLL_INTERVAL に 0 以下や不正な値が設定された場合はデフォルト（60 秒）にフォールバックし、警告ログが出力されます。
- process_priority と CPU affinity は権限や OS に依存するため、設定に失敗した場合は警告を出して処理を継続します（失敗は致命的でありません）。
- portfolio の関数群は純粋関数（副作用なし）を旨とし、DB 等の外部リソースにはアクセスしません。将来的な拡張箇所（銘柄別 lot_size マスタや価格フォールバックなど）は TODO コメントで明記しています。
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ行われます。未インストール時は警告を出してスキップします。
- paper_trading モードでは発注・約定ロジックは MockBrokerClient を使用し、記録は完全に分離された paper_trading DB（デフォルト: data/paper_trading.db）へ保存されます。

### セキュリティ (Security)
- （該当なし）

---

参考: Keep a Changelog — https://keepachangelog.com/（本 CHANGELOG は日本語で要点をまとめています）