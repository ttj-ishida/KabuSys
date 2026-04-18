CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

未リリース
---------


0.1.0 - 2026-04-18
------------------

初回公開リリース。コードベースから推測される主要な実装内容を以下にまとめます。

追加 (Added)
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - プロセス優先度を設定し（high）、BrokerClientFactory を用いてブローカークライアントを生成。
    - paper_trading 環境時は専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。
    - スレッドで ExecutionEngine を実行・監視し、停止フラグ検知で安全に停止。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込み。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正値はデフォルトにフォールバックして警告。
    - Monitoring は環境に関係なく本番 sqlite_path を使用する（監視データは共通 DB）。
    - 停止フラグ検知、例外捕捉によるループ継続などの堅牢化を実装。
- 設定関連
  - config.py: Settings クラスを導入し、環境変数経由の設定取得を集中管理。  
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。  
    - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。  
    - .env パースはシングル/ダブルクォートやエスケープ、インラインコメントなどを考慮した堅牢実装。  
    - 各種プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境判定 helpers）。
    - 値検証 (KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など) を行い、不正な値では例外を送出。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援。  
    - J-Quants / kabu API などの必須項目を含む複数項目を対話的に設定可能。  
    - 既存 .env の読み込み・マスク表示 / 確認プロンプト / ファイル書き込み機能を備える。  
    - .env 書き出しのテンプレートは Git にコミットしない旨の注意文を含む。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数の存在チェック、KABUSYS_ENV, LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）を実施。  
    - --strict モードで警告も失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選択と重み計算関数を追加。  
    - select_candidates: スコア降順で上位 N を選択。タイブレークは signal_rank で。  
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。スコア全て 0 の場合は等金額へフォールバック（警告）。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム係数を実装。  
    - apply_sector_cap: 既存保有をもとにセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。将来の価格フォールバックに関する TODO 記載あり。  
    - calc_regime_multiplier: market レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）を実装。  
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer による保守的見積り、スケールダウンと remainder による再配分処理を含む。
    - 価格欠損時のスキップやログ出力。将来の銘柄別 lot_size 管理の拡張 TODO を含む。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。  
    - ログレベル・ログディレクトリの解決順序を明示。ログディレクトリ作成失敗時はファイル出力をスキップして安全に継続。stdout を使用する点を明記（cron タスク等向け）。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を提供（psutil ベース）。  
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収。権限不足や未サポート時は警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率・注文成立率・送信率・レイテンシ（P95 含む）を集計して PASS/FAIL 判定を出力。閾値はソース内定義（稼働率 99% 等）。  
    - DB パスを --db / 環境変数で指定可能。DB が存在しない場合やテーブル欠損時の耐性あり。
- リサーチ / ファクター群
  - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算の基盤を実装（DuckDB 接続前提）。  
    - calc_momentum 等の関数・定数を開始。prices_daily / raw_financials を参照する方針を明記。  
    - ファイルは途中（末尾が途中で切れている）であり、実装継続の余地あり（WIP）。
- パッケージ情報
  - __init__.py: パッケージ名と __version__="0.1.0" を設定。

変更 (Changed)
- なし（初回リリースのため新規追加が中心）。

修正 (Fixed)
- なし（初回リリースにおける既知の設計上の注意点や TODO はソース内に注記）。

非推奨 (Deprecated)
- なし。

削除 (Removed)
- なし。

セキュリティ (Security)
- .env に秘密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を含むため、config_setup.py では「.env は絶対に Git にコミットしないこと」を出力。運用時には .env の取り扱いに注意してください。

既知の問題 / TODO
- research/factor_research.py はファイル末尾が途中で終わっており、いくつかの関数実装が未完（WIP）。継続実装が必要。  
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる旨の TODO メモあり。将来的に前日終値や取得原価でのフォールバックが検討される予定。  
- position_sizing: 現状は全銘柄共通の lot_size（100）を想定。将来的に銘柄別 lot_map の導入を検討中。  
- run_monitoring は monitoring に本番 sqlite_path を常に使用する設計（監視データの分離要件に応じて見直しが必要な場合あり）。

参考
- 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1  
- 設定検証 CLI: python -m kabusys.validate_config  
- 環境設定ウィザード: python -m kabusys.config_setup  
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report

---