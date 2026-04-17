# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語）

現在のバージョン: 0.1.0 — 初期リリース

## [Unreleased]
- なし

---

## [0.1.0] - 2026-04-17
初期リリース。KabuSys のコア機能群を追加。

### 追加 (Added)
- 基本パッケージとバージョン定義
  - package メタ情報: `src/kabusys/__init__.py` に `__version__ = "0.1.0"` を追加。

- 環境設定・読み込み
  - `kabusys.config.Settings` による環境変数ベースの設定管理を追加。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを実装。
  - .env の自動読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサ（_parse_env_line）を実装。以下に対応:
    - コメント行 / 空行の無視
    - export KEY=val 形式
    - シングル/ダブルクォートの取り扱い（バックスラッシュによるエスケープ対応）
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみ）
  - _load_env_file による保護された上書き（OS 環境変数を protected として保持）と override 制御を実装。
  - 環境読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式 .env 作成/更新ウィザードを追加。
  - 機密値は表示をマスク（****）。デフォルト値や既存値の再利用をサポート。
  - 書き出しフォーマットを整形して `.env` に保存。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前の設定チェックツールを追加。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリチェックを実装。
  - config/*.yaml の存在確認と（PyYAML が利用可能な場合の）パース検証。
  - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行/監視プロセス起動スクリプト
  - `kabusys/run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory に基づくブローカークライアント生成（paper/live を透過的に扱う想定）。
    - ExecutionEngine の起動とデーモンスレッド管理、停止フラグ（data/stop_requested.flag）監視、PID ファイル管理。
    - 初期プロセス優先度を high に設定（set_process_priority を呼び出し）。
    - RiskManager の既定設定（max_position_pct / max_utilization / rate_limit_per_sec 等）を組み込み。
  - `kabusys/run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（monitoring 専用テーブル初期化を実行）。
    - 停止フラグ（data/stop_requested.flag）で優雅にループを抜ける。
    - check_once() 実行中の例外をキャッチしてログに記録し、次ポーリングに継続。

- 監視 DB 初期化ユーティリティ
  - `kabusys.monitoring.monitoring_db.init_monitoring_db`（起動前に監視用テーブルを冪等に作成する呼び出しを run_execution/run_monitoring から行う想定）。

- データベース連携
  - DuckDB 接続サポート（設定から DUCKDB_PATH を取得して接続）。
  - SQLite（監視/ペーパートレード用 DB）との組み合わせを想定。

- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加。
    - paper trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標を集計して標準出力にレポートを生成。
    - 集計項目: システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - P95 計算、日付フィルタ（--from/--to）、閾値による PASS/FAIL 判定（稼働率/成功率/送信率/P95 レイテンシ）。
    - DB が存在しない場合のエラーメッセージを実装。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (select_candidates)：score 降順・同点は signal_rank でタイブレーク。
    - 等配分 / スコア加重重み計算（calc_equal_weights / calc_score_weights）。全スコアが 0 の場合は等配分にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap：セクター集中上限判定（max_sector_pct）と候補除外ロジック。sell_codes（当日売却予定）を除外してエクスポージャー計算。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 をフォールバック。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジック。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（スリッページ/手数料見積り）対応。
    - 利用可能現金に応じたスケーリングと残差処理（fractional remainder を lot 単位で配分）。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）差を吸収してプロセス優先度（high/normal/low）を設定。アクセス権限がない場合は警告してスキップ。
    - set_cpu_affinity(cpu_count): 最初 N コアに固定する機能。未対応 OS や権限不足は警告してスキップ。

- 研究用ファクター計算（DuckDB ベース）
  - `kabusys.research.factor_research`
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: ATR (20日)、相対 ATR、20日平均売買代金、volume_ratio 等（実装途中のクエリ断片を含む）。
    - 日付レンジのバッファや NULL 処理に配慮し、データ不足時は None を返す。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更はなし（新規追加が主体）。

### 修正 (Fixed)
- 初期リリースにつき既知のバグ修正はなし。

### 注意事項 / 既知の制約 (Notes / Known issues)
- position_sizing 内で価格が欠損（0.0）の場合にエクスポージャーや発注量が過小見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバックを検討する必要あり。
- psutil を使った優先度・CPU affinity 設定は権限（root 等）やプラットフォームに依存し、失敗時は警告を出して処理を続行する設計。
- `kabusys.research.factor_research.calc_volatility` はファイル末尾が途中で切れている構成（このリリースのコード断片は継続実装が想定される）。
- Paper Trading と本番 DB を分離することでデータ混在を防止しているが、設定ミス（環境変数の指定漏れ等）は validate_config で事前に検出することを推奨。

### セキュリティ (Security)
- 機密情報（API トークンやパスワード）は .env に平文で保存される設計。`.env` を Git 等にコミットしない旨を config_setup のヘッダに注記。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定等の必須性を validate_config が警告する。

---

今後の予定
- factor_research のボラティリティ/流動性モジュールの完成。
- ExecutionEngine / BrokerClient 周りの統合テスト、MockBroker の充実。
- 単元株サイズを銘柄ごとに持てるように拡張（stocks マスタ参照）。
- 監視・レポート機能の追加メトリクス、SNS 通知連携（LINE/Slack）強化。