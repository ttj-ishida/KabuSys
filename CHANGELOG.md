CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
バージョン番号はパッケージの __version__ に合わせています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-21
--------------------

Added
- 起動スクリプト / 実行系
  - run_execution.py を追加。ExecutionEngine を起動する CLI/スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、スレッドでのエンジン実行と stop フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を導入。
    - 起動時に監視テーブルが存在することを保証する init_monitoring_db 呼び出しを追加（冪等）。
    - 停止フラグ・PID ファイルの扱いを追加。

- 監視系
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するスクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境設定にかかわらず本番 sqlite_path を使用する（監視 DB 用）。
    - stop フラグ検知でループを穏やかに終了し、例外発生時は例外情報をログに残して次ポーリングへ継続。

- 設定・環境変数管理
  - config.py を追加。.env 自動読み込み、環境変数の抽象化を提供する Settings を実装。
    - プロジェクトルートの自動検出（.git / pyproject.toml 基準）により、CWD に依存しない .env 自動ロードを実現。
    - .env の高度なパース（export プレフィックス、クォート内エスケープ、インラインコメント扱い）をサポート。
    - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 必須環境変数取得ヘルパー（_require）、各種設定プロパティ（DB パス、PID/kill flag、しきい値、paper_trading 関連）を実装。
    - PAPER_FILL_MODE 等の入力検証を実装（不正値は ValueError）。

  - config_setup.py を追加。対話式の .env 作成・更新ウィザードを提供。
    - シークレット入力はマスク表示、既存 .env の読み込み・利用、確認プロンプトと .env 書き出し機能を実装。

  - validate_config.py を追加。起動前に .env と config/*.yaml の妥当性検証を行う CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在確認と PyYAML を利用したパース検証（PyYAML 未インストール時は警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch の自動クリア設定に関する警告）。
    - --strict オプションで警告を FAIL として扱うモードを実装。

- ポートフォリオ構築ライブラリ
  - portfolio モジュールを追加（純粋関数群、メモリ内計算）。
    - portfolio_builder.py: シグナル選定 select_candidates、等金額/スコア加重の重み計算 calc_equal_weights / calc_score_weights。
      - score が全て 0 の場合は等金額配分にフォールバックし警告を出力。
    - risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに基づく乗数 calc_regime_multiplier（bull/neutral/bear マップ）。不明レジームは 1.0 でフォールバックし警告。
    - position_sizing.py: position size 計算 calc_position_sizes（risk_based / equal / score の allocation_method をサポート）。単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer を使った保守的推定、スケールダウンと残余の分配ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。
    - stdout に出す StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーへ設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック動作、LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度設定と CPU affinity 設定関数を実装。
    - Windows / POSIX（Linux/Mac/FreeBSD）向けの優先度マッピング、psutil を用いた実装。権限不足や未対応 OS 時は警告を出してスキップ。

- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポートを生成する CLI を実装。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し表示。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）による PASS/FAIL 判定を実装。
    - 日付フィルタ (--from / --to)、DB パスの上書き (--db) をサポート。

- 研究用機能（下準備）
  - research/factor_research.py を追加（未完の箇所あり）。
    - DuckDB を使用したファクター計算のための設計と定数、calc_momentum などの実装方針を追加（prices_daily / raw_financials 参照、結果は (date, code) ベースの dict リストで返す仕様）。

Changed
- ログ出力の標準化
  - すべての起動スクリプト/コンポーネントから utils.logging_setup.setup_logging を呼ぶ想定に統一。ログファイル名は app_name により分離（例: execution.log, monitoring.log）。

- DB/分析インフラの分離
  - 実行系は paper_trading モード時に paper_trading 専用 SQLite を使用する一方、監視系は環境にかかわらず本番 monitoring.db（settings.sqlite_path）を参照する設計とした（監視データは本番 DB に記録）。

Fixed
- 環境変数パースの堅牢化
  - .env パーサで export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの処理を正しく扱うようにし、誤った .env の読み込みを抑制。

- MONITOR_POLL_INTERVAL の安全化
  - run_monitoring のポーリング間隔取得で 0 以下や非整数が渡された場合に警告を出しデフォルトへフォールバック（time.sleep に渡して ValueError が出るのを防止）。

- position_sizing の aggregate cap スケーリングの精緻化
  - cost_buffer を考慮したコスト見積り、残余現金を利用した lot_size 単位の追加配分ロジックを実装し、スケール後の丸め誤差を改善。

Security
- シークレットの取り扱い
  - config_setup の UI でシークレット項目はマスク表示。README などで .env を Git にコミットしないよう注意喚起（.env ファイルヘッダにも明記）。

Notes / Other
- 多くの箇所でエラーハンドリングとフォールバック（ファイル作成失敗時、psutil の権限不足、PyYAML 未インストール等）を想定し、起動継続可能な設計としています。
- research/factor_research.py は途中までの実装（calc_momentum の冒頭まで）です。完全なファクター計算ロジックの実装は今後のリリースで追加予定です。

Acknowledgements
- 本リリースで導入した各 CLI やユーティリティは、ローカル開発・ペーパートレード・本番のそれぞれの運用モードを考慮して設計されています。今後はテスト補強、ドキュメント追加、欠損データに対するフォールバックロジック（例: 価格フェイルオーバー）等を進める予定です。