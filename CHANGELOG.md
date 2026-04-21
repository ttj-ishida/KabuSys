CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」準拠の形式で記載しています。  
バージョン付けは semantic versioning に準拠します。

[0.1.0] - 初回リリース
---------------------

リリース日: (初回リリース)

Added
- 基本機能群の実装（日本株自動売買システム KabuSys の初期実装）。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離（MockBrokerClient 使用想定）。
      - 起動時にプロセス優先度を "high" に設定し、停止フラグ (data/stop_requested.flag) および PID ファイル (data/execution.pid) を扱う。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視用 DB は実行環境にかかわらず本番用 sqlite_path を使用（監視は本番 DB を参照）。
  - 設定管理
    - config.py
      - Settings クラスを追加。環境変数から各種設定（DB パス、API トークン、KABUSYS_ENV、ログレベル等）を取得・検証。
      - .env 自動ロード機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env パース処理が export プレフィックス、クォート値、エスケープ、インラインコメントなどに対応。
      - PAPER_FILL_MODE の妥当性チェック、paper_sqlite_path のサポートなど。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加（secret のマスク表示、選択肢・デフォルトの提示など）。
    - validate_config.py
      - 起動前の設定検証 CLI を追加（必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパースチェック、live 環境用ガードなど）。
      - --strict モードにより警告を FAIL 扱いで exit(1) にできる。
  - ポートフォリオ構築モジュール（pure function、DB 非依存）
    - portfolio/portfolio_builder.py
      - 銘柄候補選定（select_candidates: スコア降順、タイブレークに signal_rank）を追加。
      - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分へフォールバック）を実装。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap を追加（既存保有を加味して候補を除外、"unknown" セクターは除外対象外）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング）を実装。未知レジームは警告して 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - 発注株数決定ロジック calc_position_sizes を実装（allocation_method: risk_based / equal / score、lot_size による丸め、max_position_pct/ max_utilization 等の制約、cost_buffer を考慮した aggregate cap スケーリング、残差処理による追加配分）。
      - 将来の拡張点（銘柄別 lot_size のサポート等）に関する TODO コメントあり。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一的なログ設定ユーティリティを実装。
      - コンソール出力は stdout に出力（cron 等で stdout/stderr を一本化しやすくするため）。
      - 日次ローテーションの TimedRotatingFileHandler を追加（デフォルト logs/、30 日保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
      - 既存ハンドラは再設定時に一旦 flush/close して置換。
    - utils/process_priority.py
      - Windows / POSIX を吸収するプロセス優先度設定を追加（high/normal/low）。
      - CPU affinity 設定用の set_cpu_affinity を提供（任意）。
      - 権限不足や未対応 OS は警告し安全にスキップ。
  - モニタリング DB 初期化 API
    - monitoring/monitoring_db.py（参照されているが実装ファイルは本 changelog 外）：起動スクリプトから呼び出される初期化関数 init_monitoring_db の使用を確保（冪等で監視テーブルを存在させる）。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py
      - paper_trading 用 SQLite DB からレポートを集計して標準出力に検証レポートを生成する CLI を追加。
      - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、リスク却下数、平均/最大/P95 レイテンシ等。
      - P95 計算関数、期間フィルタ、閾値（デフォルト: 稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200 ms）による PASS/FAIL 判定を実装。
  - リサーチ（解析）基盤（骨組み）
    - research/factor_research.py
      - DuckDB を用いたファクター計算モジュールの骨組みを追加（Momentum/Value/Volatility/Liquidity 等の定義、calc_momentum の実装開始）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
  - パッケージメタ情報
    - __init__.py にて __version__= "0.1.0" を設定。

Changed
- 設計方針・実装メモの追加
  - 各モジュールに設計理由・制約・将来拡張の TODO コメントを多数追記（例: position_sizing の lot_size 拡張、risk_adjustment の price fallback についての注意など）。
- ログの扱い
  - ファイルハンドラ作成に失敗した場合に明示的にフォールバックし、実行継続を優先する挙動を採用。

Fixed
- （初回リリースのため API 追加・整備中心。既知の安全弁・エラーハンドリングを多数導入）
  - 環境変数パースの堅牢化（export 句、クォート内のエスケープ、インラインコメント処理）により .env 読み込みの誤解析を防止。
  - process_priority / logging_setup 等で権限不足や未対応環境でもクラッシュしないように例外処理を追加。

Deprecated
- なし

Removed
- なし

Security
- 機密情報（API トークン等）は .env に保存することを想定し、config_setup の出力内で README に「.env を Git にコミットしないこと」を明記。
- 実行時に secret を標準出力へダンプしない工夫（ウィザードでのマスク表示等）。

Notes / Known limitations / TODOs
- research/factor_research.py は計算ロジックの一部（calc_momentum の続き等）が未完の箇所があるため、完全なファクター計算実装は継続作業が必要。
- position_sizing.calc_position_sizes:
  - 銘柄ごとの単元（lot_size）を将来サポートする想定の TODO がある。
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の注記あり（apply_sector_cap）。
- monitoring_db 等の一部モジュールの詳細実装は本差分内で参照されるのみ（別ファイル実装想定）。
- 本番運用時の注意点:
  - validate_config により KABUSYS_ENV=live の場合は追加警告を表示。KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨。
  - run_monitoring は監視 DB として settings.sqlite_path を常に使用するため、監視用と発注用 DB の運用分離を行っていることを理解のこと。

作者・貢献
- コードベース内に記載の各ユーティリティ・モジュールの責任範囲に基づき実装。

ライセンス
- リポジトリ内の LICENSE（存在する場合）に従うこと。

--- 

今後の変更履歴（提案）
- research/factor_research のファクター実装完了とテスト追加
- テストスイート（ユニット・統合）および CI 設定
- broker/Mock と実ブローカークライアントのインターフェース統一・モック強化
- 銘柄別 lot_size 対応、価格フォールバックロジックの追加
- monitoring/監視・アラートの LINE 連携の実装（通知テンプレート等）

（必要であれば、各ファイルごとの細かい変更点やコミット単位の詳細な変更ログを推測して追記できます。）