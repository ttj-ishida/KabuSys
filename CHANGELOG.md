# Changelog

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に従います。
セマンティックバージョニングを採用します。

## [Unreleased]

### 注意 / 既知の事項
- 一部モジュールに TODO コメントや将来的な拡張の注記があります（例: price のフォールバック処理、銘柄ごとの lot_size 対応など）。
- research/factor_research.py は一部（ファイル末尾）で実装が途切れているように見えます。実行前に該当箇所の実装確認を推奨します。

---

## [0.1.0] - 2026-04-18

### Added
- 基本アーキテクチャとコア機能を実装（初期リリース）。
  - 日本株自動売買システム "KabuSys" パッケージを導入。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 環境設定・読み込み
  - .env ファイルと環境変数から設定を自動読み込みする機能。
    - プロジェクトルートの探索は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。
  - .env ファイルのパーシングは以下に対応:
    - コメント行、`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い（クォート内は無視）。
    - 上書き動作を制御する `override` と OS 環境変数を保護する `protected` をサポート。

- 設定用 CLI ウィザード
  - `kabusys.config_setup`（python -m kabusys.config_setup）を提供。
    - 対話式に .env を初期作成 / 更新可能。
    - J-Quants トークン、kabuAPI パスワード、DB パス、ログレベル、KABUSYS_ENV 等の項目を扱う。
    - シークレット値は表示をマスクして取り扱う。
    - 保存前の確認プロンプトあり。

- 設定検証ツール
  - `kabusys.validate_config`（python -m kabusys.validate_config）を実装。
    - 必須環境変数・環境値の妥当性確認。
    - DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 本番環境（KABUSYS_ENV=live）における追加ガード（LINE 設定や kill フラグのクリア設定等）を実装。

- 実行系スクリプト
  - `run_execution.py`
    - プロセス優先度を起動時に "high" に設定（utils.process_priority）。
    - 環境に応じて DB を切り替え:
      - `KABUSYS_ENV=paper_trading` の場合、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成を利用。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をスレッドで起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポートし、安全停止を実装。

- 監視系スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（デフォルト data/monitoring.db）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
    - 例外発生時にログ出力し、次ポーリングまで待機して継続する堅牢化。

- ロギング／プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを提供。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみ継続。
    - ログレベルとログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
  - `kabusys.utils.process_priority`
    - Windows / POSIX の差分を吸収してプロセス優先度を設定。
    - CPU アフィニティ設定関数も提供。
    - 権限不足や未サポート OS の場合は警告を出してスキップする堅牢な実装。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額配分にフォールバックし warning を出力。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する apply_sector_cap を実装。
      - 既存保有のセクター時価総額に対する上限（max_sector_pct）を超える場合、そのセクターの新規候補を除外。
      - unknown セクターは上限適用対象外。
      - 当日売却予定銘柄（sell_codes）をエクスポージャー計算から除外可能。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。
      - 未知レジームは 1.0 でフォールバックし警告を出力。
  - `kabusys.portfolio.position_sizing`
    - position sizing の calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）によるスケーリングと残余キャッシュによる優先配分ロジックを実装。
    - cost_buffer による保守的コスト見積りを考慮。
    - price 欠損時はスキップする安全ロジック。

- 研究/ファクター計算
  - `kabusys.research.factor_research`
    - Momentum / Value / Volatility / Liquidity 等のファクター計算の設計と一部実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルに依存する設計。
    - モメンタム指標（mom_1m, mom_3m, mom_6m, ma200_dev）計算ロジックを実装し、データ不足時の扱いを明記。
    -（注）ファイル末尾の実装が途中になっている可能性あり。

- ユーティリティ / ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 指標:
      - 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg / max / P95）など。
    - Pass/Fail しきい値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db)、環境変数 PAPER_TRADING_SQLITE_PATH での指定をサポート。
    - P95 は集合データからパーセンタイルを計算して算出。
    - DB にテーブルが存在しない場合は該当指標を N/A 扱いにして耐障害性を確保。

- API / パッケージ公開
  - `kabusys.portfolio` パッケージエクスポートを提供（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

### Changed
- 初期リリースのため、変更履歴は該当なし。

### Fixed
- 初期リリースのため、修正履歴は該当なし。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注: 本 CHANGELOG は現行コードベースの内容から推測して作成しています。実際の変更履歴やコミットログに基づく正確な差分は、バージョン管理履歴（git log 等）を参照してください。