# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
リリースは逆順（最新を上）で記載しています。

すべての注記は、提供されたコードベースの内容から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 全体
  - パッケージ初期リリース。モジュール構成、CLI、ユーティリティ、ポートフォリオ構築ロジック、実行・監視ランナーなどの基盤機能を導入。

- 設定・起動関連
  - 環境変数読み込み/管理モジュールを追加（kabusys.config）。
    - プロジェクトルート（.git または pyproject.toml）を自動検出して `.env` / `.env.local` を読み込む自動ロードを実装（無効化オプションあり）。
    - 複雑な .env 行のパースをサポート（export プレフィックス、クォート文字、インラインコメントの扱い等）。
    - 環境設定を取得する Settings クラスを提供（J-Quants / kabu API / DB パス / ログレベル / 環境判定等）。
    - PAPER_FILL_MODE の妥当性チェック、paper_trading 用 DB パス、kill/ pid ファイルパス、閾値設定などのプロパティを実装。

  - 対話式 .env 作成ウィザードを追加（kabusys.config_setup）。
    - 初期 .env の作成・更新を対話形式で行う CLI を提供。
    - デフォルト値、選択肢、シークレット入力、保存前の確認を実装。

  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在とパース検証（PyYAML がある場合）等の事前検証を実装。
    - --strict オプションで警告を fail 扱いにする機能を追加。

- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock 実装を含む想定）。
    - ExecutionEngine を別スレッドで起動し、stop フラグ（data/stop_requested.flag）で安全に停止できる仕組みを実装。
    - 起動時にプロセス優先度を high に設定し、pid ファイルの取り扱いを行う。

  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - SystemMonitor を定期ポーリング（デフォルト 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
    - 監視は環境にかかわらずプロダクション用 sqlite_path を使用（設計上の意図）。
    - 停止フラグの検出、例外時のログ保存とループ継続、KeyboardInterrupt のハンドリングを実装。

- モニタリング / レポート
  - monitoring DB の初期化ユーティリティ（init_monitoring_db）参照（監視テーブルの冪等初期化処理を想定）。
  - ペーパートレード検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs 等から稼働率、注文成功率、送信率、P95 レイテンシを集計。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。
    - 日付レンジ指定オプション（--from/--to）と DB パス指定（--db）をサポート。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選定・重み計算機能を追加
    - select_candidates（スコア降順・タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合はフォールバック）を実装。
  - risk_adjustment: セクター集中制限とレジーム乗数を追加
    - apply_sector_cap（既存ポジションからセクター別エクスポージャ計算、上限超過セクターの新規候補除外ロジック）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" で乗数を返す。未知のレジームは警告して 1.0 にフォールバック）。
  - position_sizing: 発注株数計算ロジックを追加
    - allocation_method による株数計算（"risk_based" / "equal" / "score"）。
    - lot_size 単位で丸め、per-position および aggregate（available_cash）キャップ、cost_buffer（手数料・スリッページ見積もり）を考慮したスケールダウンアルゴリズムを実装。
    - スケールダウン時に残余で lot 単位を追加配分するフェアな割当ロジックを実装。

- ユーティリティ
  - ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR 環境変数 / 引数でログディレクトリを解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX を吸収して優先度（high/normal/low）設定を行う set_process_priority。
    - CPU affinity 設定用 set_cpu_affinity（利用可能コア数チェック、権限エラーの安全ハンドリング）。

- リサーチ
  - factor_research（kabusys.research.factor_research）の初期実装を追加（モメンタムや MA200 乖離、ATR、ボリューム系指標の計算を想定した定数と関数スケルトンを導入）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計。

### 変更 (Changed)
- n/a（初期リリース）

### 修正 (Fixed)
- n/a（初期リリース）

### 既知の制限・TODO
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャが過少見積りされる可能性があり、将来的に前日終値や取得原価でフォールバックすることを検討する旨のコメントを残しています。
- position_sizing: 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size を受け取れるように拡張予定。
- research/factor_research: ファイル末尾が途中で切れている（実装継続が必要な箇所あり）。
- process_priority / set_cpu_affinity: 権限不足や未実装のプラットフォームでは警告を出して安全にスキップします（root / 管理者権限が必要な場合あり）。
- monitor は環境にかかわらず本番 sqlite_path を使用する設計になっているため、paper_trading と分離したい場合は注意が必要。

### セキュリティ (Security)
- n/a（初期リリース）

------------------------------------------------------------
注: 上記はソースコード内のコメントや構造から推測して作成した変更履歴です。実際のリリース日や詳細はプロジェクトの運用方針に合わせて調整してください。