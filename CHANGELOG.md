CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

v0.1.0 - 2026-04-25
-------------------

### Added
- 初期リリース：
  - パッケージメタ情報を追加（__version__ = 0.1.0）。
- 環境設定 / 起動補助
  - 設定管理モジュール（kabusys.config）
    - .env 自動読み込み（.env, .env.local）を実装。プロジェクトルート検出は .git / pyproject.toml を基準に行われ、CWD に依存しない方式に。
    - .env の堅牢なパーサを実装（export プレフィックス対応、クォート文字列とエスケープ処理、インラインコメント処理）。
    - 各種設定プロパティ（DB パス、Paper Trading 用設定、監視閾値、環境判定など）を提供。
  - 対話式設定ウィザード（kabusys.config_setup）
    - .env の初期作成・更新を対話的に支援する CLI を実装。
  - 設定検証 CLI（kabusys.validate_config）
    - 必須環境変数・パス・config/*.yaml の存在と基本的なパース検査（PyYAML があれば内容検証）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。
- 起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - プロセス優先度を高く設定して起動（set_process_priority を利用）。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を使用（本番 DB と完全分離）。
    - BrokerClientFactory を通したブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル管理をサポート。スレッドで実行し、フラグ検知で安全に停止。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor をポーリングで定期実行。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path（monitoring DB）を使用する設計。
    - 停止フラグ検知でループ終了、例外を捕捉してログ出力後に次ポーリングへ復帰。
- ロギング / プロセス制御ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - stdout への StreamHandler（標準出力）と日次ローテーションするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。LOG_DIR 環境変数や引数でログ保存先を指定可能。ファイルハンドラ作成失敗時はコンソール出力のみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差分を吸収してプロセスの優先度設定（high/normal/low）を実装。
    - CPU affinity を最初の N コアに制限する set_cpu_affinity を実装。権限不足時は警告を出してスキップ。
- ポートフォリオ構築関連（pure function 群）
  - kabusys.portfolio.portfolio_builder
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。
  - kabusys.portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装。
  - kabusys.portfolio.position_sizing
    - position sizing ロジック（risk_based / equal / score、単元株丸め、aggregate cap スケーリング、cost_buffer の考慮）を実装。
    - 投下金額が available_cash を超える場合のスケールダウンと端数処理（lot 単位での追加配分）の実装。
- 分析 / 研究ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - 稼働率、注文成功率、送信率、レイテンシ指標（P95 など）、リスク却下数を算出し Pass/Fail を判定する CLI。
    - 日付レンジ指定、DB パス指定をサポート。閾値はソース内定義（デフォルト）。
  - 研究用ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum / Value / Volatility / Liquidity 系ファクターの計算方針と実装（DuckDB を用いて prices_daily / raw_financials を参照する設計）。（実装途中の箇所あり）
- DB 初期化補助
  - 監視用テーブルを初期化する init_monitoring_db を起動時に呼び出す箇所を追加（run_execution / run_monitoring）。冪等で監視テーブルの存在を保証。

### Changed
- （新規リリースのため該当なし）

### Fixed
- 環境変数読み込み周りの堅牢性向上：
  - .env パーサが export プレフィックスやクォート内のエスケープ、インラインコメントに対応。
- ロギング初期化で既存ハンドラを適切に flush/close してから削除するようにして、二重ログ出力を防止。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- （このリリースで特に報告するセキュリティ修正はありません）

Notes / 既知の制限・ TODO
- research/factor_research モジュールに未完成の箇所（ソースが途中で切れている部分）があり、さらなる実装・テストが必要です。
- position_sizing / risk_adjustment:
  - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を利用する改善案が TODO コメントとして残っています。
  - 将来的に銘柄毎の lot_size を管理する拡張（stocks マスタの導入など）を想定。
- 実行・監視スクリプトは停止フラグ（data/stop_requested.flag）や kill フラグの挙動に依存します。特に run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用するため、テスト時には注意してください。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームで処理をスキップし、警告ログを出力します。運用環境の権限設定に留意してください。

次のステップ（開発者向け）
- factor_research の完成、テストケースの追加
- 単体テスト（ユニットテスト）と CI の整備
- ドキュメント（API 仕様・設定項目一覧・運用手順）の充実

========================================
（以降の変更履歴はここに追記してください）