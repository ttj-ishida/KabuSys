# Changelog

すべての重要な変更は Keep a Changelog 規約に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を追加しました。主な内容は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを追加。`__version__ = "0.1.0"` を含む。
  - プロジェクトルート自動検出ロジックを実装（.git / pyproject.toml を探索）。これにより .env 自動読み込みが CWD に依存せず動作。

- 設定・環境関連
  - 環境変数/.env を読み込むユーティリティを追加（`kabusys.config`）。
    - `.env` と `.env.local` の読み込み順 (OS 環境変数 > .env.local > .env) を実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - `.env` パースの堅牢化（export プレフィックス対応、シングル/ダブルクォートやエスケープ、インラインコメント処理）。
    - OS 環境変数を保護するための上書き制御（protected set）。
  - `Settings` クラスを実装し、主要設定をプロパティとして提供（J-Quants・kabu API・DB パス・監視閾値・環境判定等）。
    - `PAPER_FILL_MODE` のバリデーション（allow: instant|partial|never|reject）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の許容値チェック。
    - `is_live` / `is_paper` / `is_dev` ヘルパーを追加。

- 設定支援 CLI
  - 対話式 .env 作成/更新ウィザード（`kabusys.config_setup`）。
    - シークレット入力対応、既存値の再利用、ファイル書き込みフォーマット。
    - 推奨設定・説明文を含む複数項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）。

- 設定検証 CLI
  - 起動前設定検証ツール（`kabusys.validate_config`）。
    - 必須環境変数の存在チェック、プレースホルダ検出、KABUSYS_ENV のチェック、LOG_LEVEL のチェック、DB パスの親ディレクトリ確認。
    - config/*.yaml の存在確認と（PyYAML がある場合は）パース検証。
    - `--strict` オプションで警告も失敗扱いにできる。
    - KABUSYS_ENV=live の際の追加ガード（LINE 設定の未設定検出、KILL_FLAG_CLEAR_ON_START の警告）。

- ログ・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ（`kabusys.utils.logging_setup`）。
    - stdout への StreamHandler と、日次ローテーションを行う TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL 環境変数 / 引数からのレベル解決。
  - プロセス優先度・CPU affinity 設定ユーティリティ（`kabusys.utils.process_priority`）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して優先度設定を行う。
    - cpu_affinity 設定関数を追加（最初 N コアに固定）。
    - セキュアなフォールバックと AccessDenied/未実装時の警告処理。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（`src/kabusys/run_execution.py`）。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合、専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / default data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory を利用して paper_trading では MockBroker を使用する想定（実装と分離）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動。停止フラグ（data/stop_requested.flag）により安全停止。
    - 監視テーブルの初期化を冪等に保証（`init_monitoring_db` 呼び出し）。
    - PID ファイル管理（execution.pid）をサポート。
  - 監視ポーリング起動スクリプト（`src/kabusys/run_monitoring.py`）。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - ポーリング間隔の環境変数上書き: `MONITOR_POLL_INTERVAL`（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバックし警告）。
    - 停止フラグファイル検出でループ終了。`check_once()` 実行中の例外はキャッチしてログに出力し、次サイクルへ継続。
    - sqlite3 / duckdb 両方の接続を利用。

- ポートフォリオ構築（純関数群）
  - 銘柄選定・重み計算（`kabusys.portfolio.portfolio_builder`）。
    - 候補選定: スコア降順、同点は signal_rank 小さい方を優先（`select_candidates`）。
    - 等配分（`calc_equal_weights`）・スコア加重（`calc_score_weights`）を提供。全スコア 0 の場合は等配分にフォールバックして警告。
  - セクター集中制限・レジーム乗数（`kabusys.portfolio.risk_adjustment`）。
    - セクター上限チェック（既存保有のセクター別時価から max_sector_pct を超えるセクターの新規候補を除外）。"unknown" セクターは除外対象外。
    - レジーム乗数計算（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバックして警告）。
  - 株数計算・リスク制限・単元丸め（`kabusys.portfolio.position_sizing`）。
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で切り捨て・追加配分ロジック、per-position 上限・aggregate cap（available_cash）に基づくスケーリング。
    - cost_buffer を用いた保守的なコスト見積り、スケーリング後の端数（fractional remainder）を優先度付きで lot 単位で配分するアルゴリズムを実装。

- リサーチ / ファクター計算（骨格）
  - ファクター計算モジュール（`kabusys.research.factor_research`）を追加。
    - Momentum / Value / Volatility / Liquidity 系ファクターを計画。DuckDB の prices_daily / raw_financials を参照して計算する設計。
    - モメンタム指標（1M/3M/6M、MA200 乖離）等の定義と計算方針を実装予定（モジュールは骨格まで、実装継続を想定）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - P95 計算、日付フィルタリング（ISO8601 UTC 文字列化）、閾値判定と PASS/FAIL 出力を実装。
    - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- （初回リリースにつき該当なし）

---

注:
- 各モジュールは意図的に「本番 DB とテスト/ペーパートレード DB の分離」を考慮して設計されています。環境変数で DB パスや挙動を切り替えられます。
- 実装の一部（例: BrokerClientFactory の具体実装、factor_research の詳細計算）は別モジュールに依存または未完の箇所があります。運用前に設定検証（`python -m kabusys.validate_config`）とローカルでの動作確認を推奨します。