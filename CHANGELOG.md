# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- 変更は主にコードベースから推測して記載しています（実装上の意図・振る舞いを要約）。
- 日付はこの CHANGELOG 作成日です。

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-19

初回公開リリース。自動売買システム KabuSys の基盤機能群を追加しました。主な追加点・設計上の注意点は以下の通りです。

### Added

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は Paper Trading 用の SQLite（`data/paper_trading.db` または環境変数で指定）を使用し、本番 DB と完全分離する設計。
    - BrokerClientFactory により paper_trading 向けに MockBrokerClient を選択する想定。
    - プロセス優先度を起動直後に "high" に設定。
    - エンジンはデーモンスレッド上で run_session を実行。停止フラグ（data/stop_requested.flag）による安全な停止処理を実装。
    - PID ファイルの取り扱い（`data/execution.pid` など）をサポート。

  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出力。
    - 監視（monitoring）は環境にかかわらず本番の `sqlite_path` を参照する設計。
    - 停止フラグ（data/stop_requested.flag）によりループを終了。

- 設定／環境読み込み
  - `config.py`
    - Settings クラスを導入し、環境変数から各種設定値を取得（J-Quants、kabu API、DB パス、監視閾値、環境種別等）。
    - 自動 .env 読み込み機能: プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` をロード。OS 環境変数の保護（上書き制御）を実装。
    - `.env` パースは以下をサポート: `export KEY=val`、シングル/ダブルクォート（バックスラッシュエスケープ対応）、インラインコメント処理等。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など）を提供。
    - 環境（KABUSYS_ENV）や LOG_LEVEL の検証ロジックを組み込み。

  - `config_setup.py`
    - 対話式ウィザードで `.env` の初期作成・更新を支援する CLI を追加。
    - シークレット項目はマスク表示、既存値の再利用、テンプレート書き出し機能を実装。

  - `validate_config.py`
    - 起動前チェック CLI を追加。必須環境変数の存在確認、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、`config/*.yaml` の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード等を実施。
    - `--strict` オプションで警告も失敗（exit 1）扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - アプリケーション共通で使用する logging 設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日分保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
    - 既存ハンドラをクリアして重複設定を防止。

  - `utils/process_priority.py`
    - psutil を用いてクロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity 設定を行うユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）での差分を吸収し、権限不足や未対応環境では警告を出してスキップする安全策を実装。

- ポートフォリオ構築・リスク調整・ポジションサイズ計算
  - `portfolio/portfolio_builder.py`
    - シグナル選定（score ソートとタイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。

  - `portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）：既存保有のセクター別エクスポージャーを計算し、上限を超えたセクターの新規候補を除外するロジックを実装（unknown セクターは除外対象外）。
    - レジーム乗数（calc_regime_multiplier）：market regime（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは警告を発して 1.0 にフォールバック。

  - `portfolio/position_sizing.py`
    - allocation_method（"risk_based"/"equal"/"score"）に応じた株数算出を実装。
    - 単元（lot_size）丸め、銘柄ごとの上限（max_position_pct）や全体の投入上限（max_utilization / available_cash）に対する aggregate scaling（スケールダウン）を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もり、残差配分ロジックで lot 単位の追加配分を行う。
    - 価格欠損時はスキップしてログ出力（将来のフォールバック価格に関する TODO コメントあり）。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計して PASS/FAIL レポートを生成する CLI を追加。
    - P95 算出、期間フィルタ（--from / --to）、テーブル存在しない場合のフォールバック（OperationalError を捕捉）を実装。
    - 既定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき判定。

- リサーチ（部分実装）
  - `research/factor_research.py`
    - DuckDB 接続を受けてファクター（Momentum / Value / Volatility / Liquidity）を計算するためのモジュール骨格を追加（Momentum 周りの定数と docstring を含むが実装途中の箇所あり）。

- パッケージ情報
  - `__init__.py` にてバージョン `0.1.0` を設定。

### Changed (設計上の重要点／既存実装からの挙動)

- .env 自動ロードの優先順位
  - OS 環境変数 > .env.local > .env。プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。

- ログ出力の標準ストリーム
  - StreamHandler は stdout を使用（stderr ではない）。cron 等で stdout/stderr を一本化してリダイレクトする運用を想定。

- 監視 DB の扱い
  - run_monitoring は KABUSYS_ENV にかかわらず常に `Settings.sqlite_path`（本番想定）を使用する設計であることを明示。

### Fixed / Defensive

- 環境変数パースの堅牢化
  - `config._parse_env_line` はクォートやバックスラッシュエスケープ、インラインコメント、`export` プレフィックス等に対応し、不正行は無視するよう改良。

- ポーリング間隔の不正値ハンドリング
  - `MONITOR_POLL_INTERVAL` が整数以外・1 未満の場合は警告を出してデフォルト（60 秒）へフォールバック。

- ロギングハンドラ作成のフォールバック
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合は警告を出し、コンソール出力のみで継続する。

- プロセス優先度／CPU affinity の安全化
  - 権限不足や未対応 OS でも例外を握りつぶさず警告ログを出して処理をスキップする実装で安全に運用可能。

- DB テーブル未作成時のツール耐性
  - `paper_verification_report` や起動時の `init_monitoring_db` 呼び出し等で、テーブルが存在しない場合に OperationalError を捕捉して適切にデグレード（N/A 表示等）するようにしている。

### Notes / TODO

- `research/factor_research.py` はモメンタム計算の実装途中（末尾が途中で切れている）。DuckDB を使ったファクター計算の具体実装が残っている。
- `position_sizing` の価格欠損時の挙動に関してはコメントに今後の改善案（前日終値や取得原価のフォールバック）が残されている。
- Paper Trading の Fill モードや MockBroker の振る舞いは設定（PAPER_FILL_MODE）に依存。実運用時は設定値の確認が必要。
- 本リリースではログ・プロセス制御・環境検証などの基盤整備に注力。実際のストラテジー実装や取引ロジックは別モジュールとして組み合わせて動作させることを想定。

---

以上。必要であれば、この CHANGELOG を英語版に翻訳したり、各項目をさらに細かいコミット単位に分割して記載することもできます。どの形式を優先しますか？