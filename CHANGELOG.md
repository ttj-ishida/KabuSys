# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した変更履歴（機能追加・仕様・既知の制限など）です。

## [Unreleased]

### 注意・既知の制限
- run_monitoring は KABUSYS_ENV にかかわらず常に本番用の sqlite_path を使用します（コード設計上の仕様）。
- 一部モジュールに TODO コメントあり（例: position_sizing の銘柄ごとの lot_size 拡張、price 欠損時のフォールバック）。将来的な拡張/改修を検討してください。
- ログディレクトリの作成やプロセス優先度設定は権限不足などで失敗する場合があり、その場合はフォールバック（コンソール出力のみや設定スキップ）します。

---

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義 (src/kabusys/__init__.py)。

- 設定管理
  - 環境変数自動読み込み機能を実装。
    - プロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を読み込む（OS 環境変数優先、`.env.local` は上書き可能）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パース実装: `export KEY=val`、クォート内のエスケープ、インラインコメント処理などをサポート（src/kabusys/config.py）。
  - `Settings` クラスを提供し、アプリケーション設定（DB パス、API トークン、閾値、環境種別、ログレベルなど）をプロパティ経由で取得・検証可能にした。
    - valid 値チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）と必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）。

- 設定ウィザード CLI
  - `.env` を対話式に生成・更新する `config_setup.py` を追加。
  - 秘匿項目のマスキング表示、選択肢、デフォルト値、保存確認を実装。
  - `.env` のテンプレート書き込み（注意: .env は Git にコミットしないようヘッダ記載）。

- 設定検証 CLI
  - 起動前に環境変数・config/*.yaml の存在/妥当性を検証する `validate_config.py` を追加。
  - `--strict` オプションにより警告を失敗扱いにできる。
  - YAML のパース検証は PyYAML が存在する場合に実行、未インストール時は警告でスキップ。

- 起動スクリプト
  - 監視用ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で間隔を上書き可能。無効値はデフォルトにフォールバック。
    - stop フラグファイル `data/stop_requested.flag` の検出で安全終了。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite（monitoring DB）と DuckDB へ接続し SystemMonitor を利用して単一チェックを繰り返す。
  - Execution エンジン起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成（paper/live 切替）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立て実行。エンジンはバックグラウンドスレッドで実行、stop フラグ検出で安全停止。
    - デフォルトの RiskConfig（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。初期ポートフォリオ値は broker.get_available_cash() を使用。

- ロギングユーティリティ
  - `utils/logging_setup.py` を追加。
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト "logs/"。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。

- プロセス優先度ユーティリティ
  - `utils/process_priority.py` を追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して優先度（high/normal/low）を設定。
    - CPU affinity 固定関数 `set_cpu_affinity` を提供。
    - 権限不足や未サポート環境では警告を出してフォールバック。

- ポートフォリオ構築ライブラリ
  - `portfolio/portfolio_builder.py`
    - シグナル候補の選別（スコア降順、signal_rank によるタイブレーク）。
    - 等重配分 (`calc_equal_weights`) とスコア加重配分 (`calc_score_weights`)。全スコアが 0 の場合は等重配分へフォールバック。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap`（既存ポジション評価、売却予定銘柄除外、"unknown" セクターは制限適用外）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（"bull", "neutral", "bear" をマッピング、未知値は警告の上 1.0 フォールバック）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数を決定する `calc_position_sizes` を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株丸め（lot_size、デフォルト 100）、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料・スリッページの保守的見積り）を考慮。
    - スケールダウン時の再配分ロジック（fractional 残差に基づき lot_size 単位で追加配分）を実装。
    - TODO: 将来的な銘柄別 lot_size サポート用の注記あり。

  - `portfolio/__init__.py` で上記 API をエクスポート。

- 解析/研究モジュール（着手）
  - `research/factor_research.py` を追加（ファクター群の計算設計を実装）。
    - Momentum, Value, Volatility, Liquidity の設計方針と計算用定数を定義。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する想定。
    - calc_momentum の実装開始（コードベースの一部が含まれる）。

- ツール
  - Paper Trading 検証レポート生成スクリプト `tools/paper_verification_report.py` を追加。
    - Paper Trading DB（デフォルト `data/paper_trading.db`）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して人間向けレポートを出力。
    - デフォルトの合格基準（稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義。
    - P95 計算、日付フィルタ、テーブル存在チェック、各種例外時のフォールバック処理を実装。

- 監視テーブル初期化
  - `monitoring.monitoring_db`（参照）を介して SQLite 監視テーブルの初期化を起動スクリプト内で保証（冪等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- `.env` ファイル生成時の注意書きを明記（.env を絶対に Git にコミットしないこと）。

---

メンテナンスや今後の課題（推奨）
- position_sizing: 銘柄ごとの単元情報（lot_size）を stocks マスタに持たせ、銘柄別 lot_map を受け取る拡張。
- apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価）の導入検討。
- research モジュール: calc_momentum 等の未完部分を完成させ、Value/Volatility/Liquidity の実装とテストを追加。
- テストカバレッジ: 設定パーサ、ウィザード、position sizing、risk adjustments などの単体テストを整備。
- 運用面: run_monitoring/run_execution のコンテナ化や systemd ユニット化、信号処理（SIGTERM 等）対応の強化。

もし特定のリリースノート形式（日付を過去のリリース日へ合わせる等）や、さらに細かい差分（ファイル単位の変更箇所一覧）を希望される場合は教えてください。