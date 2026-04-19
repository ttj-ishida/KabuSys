# Changelog

すべての注記は Keep a Changelog の形式に従います。慣例に従い重要な変更点・追加機能・修正をバージョン単位で記載しています。

リリースノートではコードベースから推測できる機能・挙動をまとめています（実装内コメントや API を根拠に記載）。日付はリポジトリの現状解析日です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回リリース。本リポジトリは日本株自動売買システム「KabuSys」の基盤コンポーネント群を含みます。主な追加内容は以下のとおりです。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加: `kabusys.__version__ = "0.1.0"`。

- 環境設定管理
  - Settings クラスを実装（`kabusys.config`）
    - 環境変数から各種設定を取得・検証するプロパティ群（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、環境種別 など）。
    - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - production/paper_trading 別の SQLite パスや DuckDB パスを取得可能。
  - .env ファイルの自動読み込みを実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - .env パース機能を実装（引用符・エスケープ・インラインコメント対応）。

- 環境設定ウィザード CLI
  - `kabusys.config_setup`：対話式で `.env` を作成／更新するウィザードを追加。
    - デフォルトや選択肢、シークレット入力に対応し、生成テンプレートを `.env` に保存。
    - J-Quants / kabu / DB パス / LINE 通知など主要設定項目をサポート。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に環境変数や config/*.yaml の存在・簡易妥当性を検証するコマンドを追加。
    - 必須環境変数未設定検出、KABUSYS_ENV の妥当性チェック、DB パス親ディレクトリ存在チェック、YAML パース検証（PyYAML があれば実施）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行用スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を設定（`high`）。
    - 環境が `paper_trading` の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止に対応。
    - PID ファイル管理（data/execution.pid）を行う。

  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境に依らず本番の sqlite_path を監視 DB に利用（監視は production DB を参照する設計）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグファイル検出でループを終了。
    - SystemMonitor の単発チェックで例外が発生してもループ継続（例外はログ出力）。

- モニタリング DB 初期化ユーティリティ
  - `monitoring.monitoring_db.init_monitoring_db` を利用して監視用テーブルの整備（冪等に初期化）。

- ロギング設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリを自動作成し、失敗時はファイル出力をスキップして stdout のみで継続。
    - 環境変数 LOG_LEVEL / LOG_DIR、引数での上書きに対応。
    - 既存ハンドラは再設定時に安全にクローズして二重登録を防止。

- プロセス優先度・CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収して優先度（high/normal/low）を設定可能。
    - CPU affinity 固定機能（最初の N コアに固定）。
    - 許可がない場合や未対応 OS の場合に安全にスキップして警告ログ出力。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：候補選定と重み計算
    - select_candidates（スコア降順、タイブレーク処理）、calc_equal_weights、calc_score_weights（スコア合計 0 の場合に等配分へフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：セクター上限適用・レジーム乗数
    - apply_sector_cap（既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外）。
    - calc_regime_multiplier（regime に応じて投下資金乗数を返す。未知のレジームは 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`：株数決定ロジック
    - risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を加味した安全なスケーリングアルゴリズムを実装。

- 研究向けファクター計算スケルトン
  - `kabusys.research.factor_research` を追加（Momentum / Value / Volatility / Liquidity を想定した設計、DuckDB 接続を受け取る設計）。モジュール内に計算定数と calc_momentum の初期実装が含まれる（未完部分あり）。

- ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレーディングの検証レポート生成ツールを追加。
    - Paper Trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH / 引数 --db）から統計を集計し、稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）を算出して PASS/FAIL 判定を出力。
    - デフォルトの合格閾値を設定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- DB 関係
  - 実行エンジンは環境が paper_trading の場合、本番の monitoring DB とは別に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して完全分離する設計。
  - 監視（run_monitoring）は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用する旨がコメントに明記されている。

- 設定の安全性
  - .env 自動読み込みは OS 環境変数を保護（既存 OS 環境変数を上書きしない）し、`.env.local` は上書き可能だが protected によって OS 環境変数は保持される。
  - validate_config による事前検証 / config_setup による対話的生成により初期設定ミスの低減を図る。

- ロギング / プロセス制御
  - setup_logging は stdout を用いる設計（cron 等で stdout/stderr をリダイレクトしやすくするため）。
  - set_process_priority / set_cpu_affinity は権限不足や未対応 OS を考慮して例外を抑止し、警告ログで通知する堅牢性を持つ。

- フォールバック挙動
  - 各所で不正入力やデータ不足・例外発生時にフォールバックする実装（MONITOR_POLL_INTERVAL が不正な場合のデフォルト復帰、score_weights の total==0 フォールバック、レイテンシ P95 計算でデータなしは N/A 等）。

### Known / TODO
- research.factor_research の実装は途中で切れている箇所がある（コメントに続きの処理が想定される）。完全なファクター計算ロジックの実装が今後の作業。
- position_sizing の lot_size を銘柄ごとに変えられるよう stocks マスタとの連携や拡張設計予定（コメント参照）。
- apply_sector_cap の price 欠損時のフォールバック（前日終値や取得原価を用いる等）が TODO コメントとして残る。
- 一部モジュール（例: monitoring.system_monitor, execution.Engine 等）は本 CHANGELOG の対象コード内に定義は見えるが、詳細実装は別ファイルに依存するため別途テストと検証が必要。

---

この CHANGELOG は現行のソースコードから推測して作成したものであり、実際の設計意図やドキュメントと差異がある場合があります。必要であれば、各機能ごとに差分を細かく分けたリリースノート（例: パッチ / マイナー / メジャー）に展開します。