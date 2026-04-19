# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のリリース: 0.1.0（初期リリース）

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

初期公開リリース — KabuSys 自動売買フレームワークのベース機能を実装しました。

### Added（追加）
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db 等）を使用し MockBrokerClient を利用する想定。
    - 起動前に process priority を "high" に設定し、PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止に対応。
    - エンジンはバックグラウンドスレッドで実行し、停止フラグ検知でエンジン停止処理を実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
    - 停止フラグの検知・例外ハンドリング・KeyboardInterrupt による安全終了対応。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。

- 設定・環境管理
  - config.py: Settings クラスを実装。
    - .env 自動ロード機構（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env/.env.local の読み込みルール（OS 環境変数保護、override の扱い）。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）の取得・検証ロジックを提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証や便利なプロパティ（is_live/is_paper/is_dev）を実装。

  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。
    - 既存 .env の読み込み、秘密項目のマスク表示、保存確認、テンプレート生成（.env に注意喚起）を実装。

  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ検証、config/*.yaml の存在・（PyYAML があれば）パース検証。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソートと上位選択（score 降順、signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重重み算出（全スコア 0 の場合は等分配へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックによる候補除外機能（sell_codes を考慮、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
      - 単元（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を織り込んだ保守的見積り、残差処理による追加配分ロジックを実装。
      - 欠損価格のスキップやログ出力でのデバッグ情報を提供。

- ユーティリティ
  - utils/logging_setup.py: 共通ロギングセットアップを追加。
    - stdout (StreamHandler) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR の解決順、ディレクトリ作成失敗時にファイル出力をスキップするフォールバック実装。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差を吸収した nice/priority 設定。
    - set_cpu_affinity によるプロセス CPU 固定機能。
    - 権限不足や未サポート環境での安全なフォールバックと警告出力。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を呼び出す初期化フローを実装（監視テーブルが存在することを保証）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数など。
    - P95 計算ユーティリティ、日付フィルタ (--from/--to)、DB パス指定（--db / 環境変数）対応。
    - 既定の閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定と詳細出力。

- 研究用モジュール（骨格）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。
    - DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照して結果を返す設計。
    - calc_momentum の実装を開始（モジュールの一部が途中まで実装）。

### Changed（変更）
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__="0.1.0" を設定。

- 環境変数読み込みの挙動
  - .env/.env.local の自動ロードは OS 環境変数が存在するキーを保護（protected）して上書きしない挙動。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

### Fixed（修正）
- ロバストネスの向上
  - .env パーサーで export プレフィックス・クォート・エスケープ・インラインコメントへの対応を実装し、より多様な .env フォーマットに対応。
  - logging_setup: ログディレクトリ作成やファイルハンドラ作成失敗時のフォールバックを明確にし、起動失敗を回避。
  - process_priority: 権限不足や未サポート OS の場合に警告を出して処理をスキップするように改善。
  - run_monitoring/run_execution: 停止フラグを使った安全停止、例外キャッチでループ継続、DB 接続の確実なクローズを実装。

### Deprecated（非推奨）
- なし

### Removed（削除）
- なし

### Security（セキュリティ）
- 秘密情報（J-Quants / kabu API パスワード等）は .env に保存する運用を想定。config_setup で .env を生成する際に Git へコミットしないよう注意喚起を追加。

---

注意事項・既知の制約
- research/factor_research.py はファクター計算の設計方針と一部実装が存在しますが、完全実装ではありません（calc_momentum が途中で終わっている）。今後の実装・テストが必要です。
- Paper Trading 実行時は本番 DB とは分離される設計ですが、DB パス設定ミスにより混在しないよう環境変数（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）の設定に注意してください。
- process priority / CPU affinity の設定は環境や権限に依存します。権限不足等で設定できない場合は警告のみ出力され、処理は継続します。
- config/*.yaml のパース検証は PyYAML がインストールされている場合にのみ実行されます。PyYAML 未導入時は警告を出してスキップします。

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の数式とテスト）。
- ExecutionEngine / Broker 周りの詳細実装と E2E テスト。
- 監視・アラート（LINE 通知）機能の実装強化と実際の運用通知テスト。