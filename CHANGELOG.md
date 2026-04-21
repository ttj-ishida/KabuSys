# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-21
初期リリース。

### Added
- 全体
  - パッケージ初期版を追加。パッケージ名: KabuSys（日本株自動売買システム）。
  - バージョン情報を `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - 実行エンジン起動スクリプト `src/kabusys/run_execution.py` を追加。
    - ExecutionEngine の起動、Broker クライアント生成（paper_trading 時は Mock を想定）、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - KABUSYS_ENV=paper_trading の場合は専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出で Engine 停止機構を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプト `src/kabusys/run_monitoring.py` を追加。
    - SystemMonitor のポーリングループを起動。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。0 以下や不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定管理
  - `src/kabusys/config.py` を追加。
    - .env 自動ロード機能（OS 環境変数 > .env.local > .env の優先順位）。プロジェクトルートを .git / pyproject.toml で探索して決定。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env のパースロジックはシングル/ダブルクォート、エスケープ、コメント処理を考慮。
    - Settings クラスを提供し、各種環境変数（J-Quants / kabu API / DB パス / 監視しきい値 / システムフラグ 等）をプロパティ経由で取得。値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。
    - `settings = Settings()` を公開。

  - 対話式設定ウィザード `src/kabusys/config_setup.py` を追加。
    - .env の初期作成・更新を支援する CLI。
    - ユーザープロンプト、既存 .env の読み込み、保存機能を備える。

  - 設定検証 CLI `src/kabusys/validate_config.py` を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース（PyYAML が存在する場合）などをチェック。
    - --strict オプションにより警告を FAIL 扱いで終了可能。
    - 開発・本番の安全ガード（本番環境での LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング・プロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 共通のログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決をサポート。
  - `src/kabusys/utils/process_priority.py`
    - プロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定（最初 N コアに固定）を提供。psutil を利用しアクセス拒否等は警告でスキップ。

- ポートフォリオ構築モジュール
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）を実装。
    - 重み計算 calc_equal_weights（等金額） / calc_score_weights（スコア正規化。全スコア 0 の場合は警告のうえ等金額へフォールバック）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中対策 apply_sector_cap（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームはログ警告のうえ 1.0 でフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - ポジションサイズ計算 calc_position_sizes を実装。
    - allocation_method により "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）、per-stock 上限、aggregate cap、cost_buffer（手数料・スリッページ見積）を考慮。投下金額が available_cash を超えた場合にスケールダウンし、余りは残差順に lot_size 単位で追加配分するロジックを実装。

- モニタリング / DB 初期化
  - monitoring DB 初期化呼び出しを run_monitoring/run_execution で行う（`init_monitoring_db` を利用）。監視テーブルの存在を保証する形で冪等に対応。

- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py` を追加。
    - Paper Trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH / --db オプション）から集計し、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出してレポート出力。
    - 判定基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を実装し PASS/FAIL を算出。
    - P95 計算、日付フィルタ（YYYY-MM-DD）対応。

- 研究モジュール（スケルトン）
  - `src/kabusys/research/factor_research.py` を追加（ファクター計算のスケルトン）。
    - モメンタム・ボラティリティ・バリュー等を想定した設計方針と定数を実装（DuckDB を用いた prices_daily / raw_financials 参照）。
    - calc_momentum の実装が含まれる（ファイル途中まで実装）。将来的なファクター計算パイプラインの土台を提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の秘密値（トークン等）は .env に保存する想定で、config_setup にて生成される .env に対して「Git にコミットしない」旨を明記。

### Notes / Behavioral details
- MONITOR_POLL_INTERVAL は不正値（整数変換失敗や 0/負値）で警告しデフォルト 60 秒にフォールバックする実装。
- run_monitoring は監視データベース接続において KABUSYS_ENV に関係なく本番用 sqlite_path を使用する仕様。run_execution は paper_trading 時に paper_sqlite_path を使用して発注履歴を本番 DB と分離する。
- process_priority の優先度設定は psutil に依存し、権限不足や未サポート環境では警告出力してスキップする（安全にフォールバック）。
- logging_setup はログディレクトリの作成に失敗してもコンソール出力で運用を継続するよう堅牢に設計。

---

今後の予定（例）
- factor_research の各種指標（Momentum / Value / Volatility / Liquidity）の完全実装とユニットテスト追加。
- Strategy / Execution コンポーネント（ExecutionEngine, BrokerClient 実装など）の拡張と外部インテグレーションテスト。
- 監視・アラート（LINE等）連携の実装強化。

もし CHANGELOG に追記してほしい点（リリース日を変更する、より詳細な差分表記、カテゴリ分けの変更など）があれば教えてください。