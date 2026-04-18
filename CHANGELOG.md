CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回リリース（v0.1.0）に含まれる主要な機能・追加点をコードベースから推測してまとめています。

フォーマット:
- Added: 新機能や追加
- Changed: 変更点（互換性に影響する可能性のあるもの）
- Fixed: 修正（バグ修正）
- Notes: 運用上の注意や移行メモ

Unreleased
----------
（現在未リリースの項目はありません）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本機能
  - パッケージ初期リリース。バージョンは __version__ = "0.1.0"。
  - 環境設定管理モジュール（kabusys.config）
    - .env/.env.local 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env ファイルのパース実装（export 形式、クォート、インラインコメント対応）。
    - Settings クラスでアプリケーション設定をプロパティ経由で取得（J-Quants / kabu API / DB パス /運用フラグ等）。
    - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を含む。
  - 環境設定ウィザード CLI（kabusys.config_setup）
    - 対話式で .env を作成・更新。デフォルト値やシークレット入力をサポート。
    - 出力は .env に安全な形式で書き込む（コミット禁止メッセージ付き）。
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数チェック、DB パスの親ディレクトリ確認、config/*.yaml の簡易検証（PyYAML があればパースも実行）。
    - --strict オプションで警告も失敗扱いにできる。
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
    - stdout StreamHandler（標準出力）と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログレベル / ログディレクトリの解決順、ファイルハンドラ作成失敗時にフォールバックする実装。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアに固定する機能を提供。権限不足時は安全にスキップ。
  - 実行系 & 監視起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用（本番 DB から完全分離）。
      - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler などの組み立て・起動。
      - 停止フラグ（data/stop_requested.flag）検知で安全に停止。実行 PID ファイル出力サポート。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録する仕様（意図的な設計）。
  - Paper Trading 検証ツール（kabusys.tools.paper_verification_report）
    - ペーパートレード用 SQLite DB（デフォルト: data/paper_trading.db）から指標（稼働率、注文成功率、送信率、レイテンシ等）を集計して検証レポートを出力。
    - コマンドライン引数で期間指定（--from / --to）や DB パス（--db）が可能。
    - P95 計算、閾値判定（稼働率 >= 99%, 成功率 >= 90% など）を備えた PASS/FAIL 判定を実装。
  - ポートフォリオ構築モジュール（kabusys.portfolio）
    - 銘柄選定: select_candidates（スコア降順、同点は signal_rank によりタイブレーク）。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化。全スコアが 0 の場合は等金額にフォールバック）。
    - リスク調整: apply_sector_cap（セクター集中上限チェック。unknown セクターは制限対象外）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
    - 株数決定: calc_position_sizes
      - risk_based / equal / score の配分方式に対応。
      - 単元株（lot_size）単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap（スケーリング）ロジックを実装。
      - 価格未取得銘柄はスキップする安全ロジック。
  - 研究用ファクター計算（kabusys.research.factor_research）
    - DuckDB 接続を受けてモメンタム / ボラティリティ / バリュー等のファクターを計算する設計。prices_daily / raw_financials を参照する想定（設計記述あり）。

Changed
- 初期リリースのため該当なし（最初の公開に含まれるすべてが「追加」）。

Fixed
- 初期リリースのため該当なし。

Notes / 運用上の注意
- 環境変数の必須項目
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config で事前チェックを推奨。
- データベースの分離
  - paper_trading モードでは paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用し、本番監視 DB（data/monitoring.db）とは分離される設計。
  - ただし、監視（run_monitoring）は常に sqlite_path（デフォルト data/monitoring.db）を使用するため運用上の注意が必要。
- Kill / Stop フラグ
  - 停止制御はプロジェクトルート/data 内の stop_requested.flag や kill.flag を用いる設計。KILL_FLAG_CLEAR_ON_START 環境変数は本番で 1 を設定すると危険（自動クリアされてしまう）ため、デフォルト 0 を推奨。
- ログ出力
  - ログディレクトリの作成に失敗した場合はコンソール出力のみで継続する実装。cron 等で起動する際はログディレクトリの書き込み権限を確認すること。
- 権限依存の機能
  - process priority / cpu affinity の設定は権限不足やプラットフォーム差分でスキップされる場合がある（警告ログあり）。
- PAPER_FILL_MODE
  - Paper Trading の fill モードは instant / partial / never / reject のいずれか。有効値でない場合は起動時に ValueError を送出する。

今後の検討事項（コードコメントより）
- position_sizing: 銘柄ごとに単元株数を持たせる拡張（stocks マスタに lot_size を持たせる）。
- apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）導入。
- research モジュール: 実働データに基づくテスト・ベンチマークとファクター正規化ユーティリティの統合。

作者注
- 本 CHANGELOG は提供されたコードの内容・コメントから推測して作成しています。実際のリリースノートやリリース日付はプロジェクトのリリース管理に合わせて調整してください。