# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下のとおりです。

### Added
- 基本パッケージとバージョン情報
  - src/kabusys/__init__.py にバージョン `0.1.0` を追加。

- 実行用エントリスクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor を用いたポーリング型監視ループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）に関わらず production 用の sqlite_path を使用する挙動。
    - プロセス起動時に優先度を "high" に設定（set_process_priority を呼び出し）。
    - 停止制御はプロジェクト直下の data/stop_requested.flag を参照。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Mock ブローカクライアントを使用し、paper_trading 用 DB に記録して本番 DB と分離。
    - プロセス優先度を "high" に設定し、実行中に data/stop_requested.flag を検知して安全に停止。
    - PID ファイル管理（data/execution.pid）をサポート。
    - 依存コンポーネント（Broker、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）の組み立てを行う。

- 設定・環境関連
  - src/kabusys/config.py
    - 環境変数読み込み／ラッパー Settings クラスを実装。
    - プロジェクトルート自動検出（.git / pyproject.toml を基準）に基づき .env / .env.local を自動ロード（OS 環境変数優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env のパースは export 付き、クォート、エスケープ、インラインコメントなどの一般的な形式に対応。
    - 各設定（J-Quants トークン、kabu API、DB パス、paper_trading 用 DB パス、PID/kill flag、しきい値や環境名/ログレベルの検証等）をプロパティ経由で提供。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。
    - KABUSYS_ENV と LOG_LEVEL の妥当性検証を実装。

  - src/kabusys/config_setup.py
    - .env 作成・更新を支援する対話式ウィザードを追加。
    - J-Quants や kabu API パスワード等のシークレット入力、選択肢・デフォルト提示、既存 .env 読み込み、最終確認・保存機能を提供。
    - 保存先はデフォルトでプロジェクト直下の .env。--env-file オプションで変更可能。

  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が無い場合は警告）を実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- 運用ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順と引数による上書きに対応。

  - src/kabusys/utils/process_priority.py
    - Windows / POSIX(Linux/Mac/FreeBSD) の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) によりプラットフォームに応じた優先度（high/normal/low）を設定。権限不足等は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定可能（サポート環境のみ）。

- ポートフォリオ構築・リスク調整・ポジションサイジング
  - src/kabusys/portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（select_candidates: スコア降順・同点は signal_rank でタイブレーク）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコアが 0 の場合は等金額配分にフォールバックして警告を出す。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）:
      - 既存保有のセクター別時価合計を計算して、1セクター上限（max_sector_pct）を超えるセクターの新規候補を除外。
      - "unknown" セクターは上限適用外。
    - 市場レジームに応じた乗数（calc_regime_multiplier）:
      - bull:1.0 / neutral:0.7 / bear:0.3、未知は警告して 1.0 にフォールバック。

  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック（calc_position_sizes）:
      - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。
      - risk_based: risk_pct, stop_loss_pct に基づくポジションサイズ計算。
      - equal/score: weight に基づく配分。単元株（lot_size）で丸め、1銘柄上限（max_position_pct）や投下資金上限（max_utilization）を考慮。
      - aggregate cap を超過した場合のスケールダウンと残差の整数配分ロジックを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

  - src/kabusys/portfolio/__init__.py
    - 上記機能をパッケージ公開（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）など。
    - デフォルト DB は data/paper_trading.db。--db, 環境変数 PAPER_TRADING_SQLITE_PATH、期間指定 --from / --to をサポート。
    - PASS/FAIL 判定基準（稼働率 99%, fill_rate 90%, send_rate 95%, P95 latency <= 200ms）を実装。
    - DB 内のテーブル欠如や OperationalError を丁寧に扱い、Unavailable な指標は N/A と表示。

- リサーチ（ファクター算出：着手）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、流動性、バリュー等のファクター設計を記述。DuckDB を使った prices_daily / raw_financials 参照を想定。
    - モメンタム計算（calc_momentum）関数骨子を追加（実装は継続中）。パラメータや設計方針をコメントに明記。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

補足・運用メモ:
- デフォルトのデータファイル配置:
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログ: logs/<app_name>.log
- 自動 .env ロードはプロジェクトルートが特定できない場合はスキップされる（パッケージ配布後の安全対策）。
- 実行スクリプトは停止フラグ（data/stop_requested.flag）による外部制御を想定。Production 運用時には Kill Switch 等の運用手順を整備してください。