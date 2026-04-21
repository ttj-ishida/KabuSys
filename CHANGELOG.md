CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初期リリース用の変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在差分なし）

[0.1.0] - 2026-04-21
-------------------

Added
- 基本パッケージの初期実装を追加。
  - パッケージ版番号を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 実行/監視の起動スクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、本番 DB と分離。
    - プロセス優先度を high に設定し、停止フラグファイル（data/stop_requested.flag）を監視して安全に停止可能。
    - エンジンはデーモンスレッドで run_session を実行し、停止フラグで engine.stop() を呼び出す。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告の上フォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する実装。
- 設定/環境管理ユーティリティを追加。
  - src/kabusys/config.py
    - .env / .env.local の自動ロード（プロジェクトルート検出ロジック付き）。
    - Settings クラスにより環境変数をラップ（DB パス、paper_trading 用パス、各種閾値、KABUSYS_ENV 判定等）。
    - PAPER_FILL_MODE のバリデーション・デフォルト、KABUSYS_ENV / LOG_LEVEL の検証ロジックを提供。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI。
    - デフォルトや既存値を尊重しつつ、シークレット項目はマスク表示して編集可能。
  - src/kabusys/validate_config.py
    - 起動前の設定検証ツール (.env と config/*.yaml の存在／妥当性チェック)。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構成・ポジション決定ロジック（純粋関数群）を追加。
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの選択（スコア降順、signal_rank によるタイブレーク）、等重み・スコア重みの計算。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - 未知レジーム時のフォールバックと警告。
  - src/kabusys/portfolio/position_sizing.py
    - 複数の配分方式（risk_based / equal / score）に対応した発注株数計算。
    - 単元株（lot）丸め、1銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer による保守的見積もり。
    - 各種引数でリスク率、損切り率、上限等を調整可能。
- 監視・実行のためのユーティリティ群を追加。
  - src/kabusys/utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name による設定、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで動作。
    - stdout を利用する点は cron 等からのリダイレクトを考慮。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ（psutil 利用）。
    - CPU affinity 設定関数も提供。
- モニタリング DB 初期化を行う仕組みを導入（init_monitoring_db が参照されている）。
- 実行関連コンポーネントのスケルトン（BrokerClientFactory、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository）への参照を実装（ファイルは省略または別モジュールとして存在想定）。
- Paper Trading の検証レポート生成ツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）で PASS/FAIL 判定。
    - --from / --to / --db オプションに対応。
- 研究モジュール（factor_research）を追加（prices_daily/raw_financials を用いたファクター算出の設計を含む。実装は一部省略・継続中）。
  - src/kabusys/research/factor_research.py（モメンタム等の定義・定数を含む）

Changed
- n/a（初回リリース相当の初期実装）

Fixed
- MONITOR_POLL_INTERVAL の不正値に対する安全処理を追加（不正値は警告しデフォルト 60 秒にフォールバック）。
- ロギング設定で既存ハンドラの二重登録を防ぐため、再設定時に既存ハンドラをフラッシュ/クローズして削除する実装を導入。

Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組みを導入（.env 読み込み時の protected set）。
- .env を生成する際に注意喚起ヘッダを出力（.env を絶対に Git にコミットしない旨の注意）。

Notes / Known issues / TODO
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる旨の TODO コメントあり。前日終値等のフォールバック価格を使う拡張が検討対象。
- position_sizing: 将来的に銘柄ごとの単元サイズ（lot_size）の拡張を検討するコメントあり（現在は一律 lot_size 引数を使用）。
- research/factor_research.py はファイル末尾で実装が途切れている（start_da…）。ファクター算出の続き実装が必要。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する設計のため、ペーパートレード環境で監視を完全に分離したい場合は注意が必要。
- 実行・監視の停止制御はファイルベースのフラグ（data/stop_requested.flag, data/kill.flag 等）に依存している。運用手順でフラグの扱いに注意。

開発者向け補足
- デフォルトのファイルパス:
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数で制御。既定は INFO。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。無効値は起動時に ValueError を発生させる（Settings.env）。

脚注
- この CHANGELOG は提供されたソースコードの内容から推測して作成したものであり、実際のコミット履歴に基づくものではありません。実際の変更履歴を反映する場合は Git のコミットログを使用して差分を精査してください。