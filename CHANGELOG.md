# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、この変更履歴は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-25

初回リリース。自動売買システム KabuSys の基盤機能を実装しました。主な追加・仕様は以下の通りです。

### 追加 (Added)

- アプリケーション構成・起動スクリプト
  - Settings / config モジュールを追加し、.env ファイルおよび環境変数からの設定読み込みを実装。
    - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パーサは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント等に対応。
    - 必須環境変数の取得関数 `_require()` を提供。
  - 設定ウィザード CLI (`kabusys.config_setup`) を追加。
    - 対話式で .env を初期作成 / 更新可能。複数のキー（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL 等）を扱う。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。
    - .env および config/*.yaml の存在・基本妥当性チェック。`--strict` オプションで警告も失敗扱いにできる。

- 実行系 & 監視系エントリポイント
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用（settings.paper_sqlite_path）して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) と pid 管理 (data/execution.pid) に対応。
  - `run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。値が不正（1 未満や整数変換不能）の場合はデフォルトにフォールバックして警告出力。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する仕様。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/<app>.log、30 日分保存）を設定。
    - 既存ハンドラのクリーンアップ処理を行い二重設定を防止。
    - LOG_DIR / LOG_LEVEL の解決順を実装。
  - `kabusys.utils.process_priority`
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - アクセス権限不足等は警告を出して静かにスキップ。

- ポートフォリオ構築モジュール (pure functions)
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 (apply_sector_cap) と市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
    - 未知セクターは "unknown" 扱いで上限適用を除外。未知レジームは 1.0 でフォールバック（警告）。
  - `kabusys.portfolio.position_sizing`
    - allocation_method に応じた株数計算を実装（"risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮。
    - スケールダウン時の端数処理では残余キャッシュで fractional 残差が大きい順に lot 単位で追加配分するロジックを実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加。DuckDB 接続を受け取り prices_daily / raw_financials を用いて Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を実装（calc_momentum などの関数群の実装を含むが、一部実装が続きになる箇所あり）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、API レイテンシ (avg/max/P95) など。
    - デフォルトの合格閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms

- パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

### 変更 (Changed)

- なし（初回リリースのため新規実装が中心）

### 修正 (Fixed)

- なし（初回リリース）

### 注意点 / 既知の問題 (Known issues)

- factor_research.calc_momentum の実装が提供コード上で途中で切れている箇所があり（ファイル末尾の継続欠落）、完全なファクター計算実装は追加作業が必要です。
- apply_sector_cap の評価で price_map による price が 0.0 の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来は前日終値や取得原価をフォールバック価格として使う検討が必要です。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に設定できない可能性があるため、その際は警告を出してスキップします。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラをスキップしてコンソール出力のみで継続します。

### セキュリティ (Security)

- .env ファイルには機密情報（API トークン / パスワード 等）を含めるため、config_setup での README および .env を絶対に Git にコミットしない旨の注意喚起を出しています。

---

開発・運用上の補足:
- 多くの CLI スクリプト・ユーティリティは環境変数に依存します。デプロイ前に `python -m kabusys.config_setup` と `python -m kabusys.validate_config` で設定内容を作成・検証することを推奨します。
- ペーパートレード用 DB と本番監視 DB は分離される設計（paper_trading モードでは data/paper_trading.db を使用）です。