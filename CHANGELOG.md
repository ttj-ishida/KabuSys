# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: この CHANGELOG は提供されたコードベースの内容から推測して作成しています（実装ファイルやコメントを基に要約）。実際の変更履歴やコミットメッセージとは差異がある可能性があります。

## [0.1.0] - 2026-04-18

### 追加（Added）
- 全体
  - 初版リリース。基本的な自動売買フレームワークのコアユーティリティ、実行・監視スクリプト、ポートフォリオ構築ロジック、設定ユーティリティ、検証ツール、およびペーパートレード検証ツールを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用の paper_trading DB（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動ロジックを実装。
    - 停止フラグファイル（data/stop_requested.flag）チェックにより安全にシャットダウン可能。PID ファイル書き込み用パスをサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、1 秒未満の値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず（設計上）本番用の sqlite_path を使用して監視データを保持。
    - stop flag ファイルの検出でループ終了、例外発生時はログを出力して次のポーリングへ継続。

- 設定管理
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、`.env` / `.env.local` の自動ロードを行う（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能）。
    - `.env` のパースは export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理（クォートありはインラインコメントを無視、クォートなしは '#' の前が空白/タブであればコメント扱い）をサポート。
    - 各種設定プロパティを提供（DB パス、LINE トークン、KABU API、環境判定 helper: is_live/is_paper/is_dev、paper trading 用オプション等）。
    - `PAPER_FILL_MODE` の検証、有効値チェック（instant/partial/never/reject）を実装。

  - config_setup.py: 対話式 .env ウィザードを追加。
    - 既存 .env の読み込み・表示、シークレットのマスク表示、選択肢・デフォルトのサポート、保存確認、および .env 書き出しロジックを実装。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）、KABUSYS_ENV の値チェック、LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 設定の警告）を実装。
    - `--strict` フラグで警告も失敗扱いにして exit(1) を返すモードを追加。

- ログ/プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する関数 `setup_logging(app_name, log_dir, level)` を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を利用する設計（cron/Task Scheduler でのリダイレクトを考慮）。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収する `set_process_priority(level)` を実装（"high"/"normal"/"low"）。
    - `set_cpu_affinity(cpu_count)` によりプロセスを最初の N コアに固定する機能を提供。
    - psutil の例外（アクセス権限等）発生時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数、DB参照なし）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで上位 N を選択。
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア加重配分を実装。全銘柄のスコア合計が 0.0 の場合は等分配にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を適用し、上限を超えるセクターからの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた資金乗数を返す。未知レジームでは警告を出し 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数算出（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - リスクベース計算、単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer による保守的コスト見積り、残余キャッシュでの端数配分ロジックを実装。
    - 価格欠損時のスキップやログ出力を考慮。

- 解析／ツール
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。
    - 指定期間（--from/--to）や DB パス（--db / 環境変数）でフィルタリングして、システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計・出力。
    - PASS/FAIL 判定基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を導入。
    - レイテンシの P95 計算、データ不足時の N/A 表示を実装。

- 研究用モジュール（部分実装）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum, Value, Volatility, Liquidity の方針と定数を定義）。DuckDB を使用して prices_daily / raw_financials を参照する設計。

### 変更（Changed）
- 初版なので過去バージョンからの変更はなし（新規追加）。

### 修正（Fixed）
- 初版なので既知のバグ修正履歴はなし。

### 既知の制限 / TODO（From code comments）
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少に見積られてしまい、セクター制限が回避される可能性がある。将来的には前日終値や取得原価などのフォールバック価格を使用する改善を検討。
- position_sizing.calc_position_sizes:
  - lot_size は現状全銘柄共通の仮定（100）。将来的に銘柄別 lot_size を持たせる設計への拡張を想定（stocks マスタの導入）。
- research/factor_research.py:
  - ファイル末尾が途中で切れている（Momentum 計算の実装が途中まで）。完全実装が必要。

### セキュリティ（Security）
- 環境変数やシークレット（J-Quants トークン、kabu API パスワード）は .env に平文で記載されるため、.env をコミットしない旨を README / config_setup のヘッダで警告。運用時は適切な秘密管理を推奨。

---

今後の予定（推測）
- research モジュールの完全実装（ファクター計算の SQL 実装完了）。
- ExecutionEngine / SystemMonitor の詳細なテストとリファクタリング、エンドツーエンドのペーパートレード検証。
- 単元株/手数料モデルの銘柄別対応、価格フォールバックロジックの導入。
- ドキュメント整備（運用手順、デプロイ手順、監視アラート設定など）。

もし CHANGELOG に追記したい追加の変更点（実際のコミットや変更差分）があれば、差分情報を提供してください。それに基づいてバージョン別に詳細を反映します。