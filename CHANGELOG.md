# Changelog

すべての notable な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日はコードベースから推測した公開日を記載しています。

最新: Unreleased — まだリリースされていない変更をここに記載してください。

## [Unreleased]
- （現在のコードスナップショットでは特に未リリースの差分はありません）

## [0.1.0] - 2026-04-18
最初の公開リリース。シンプルな日本株自動売買フレームワークのコア機能を実装しています。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを公開（`kabusys.__version__ = "0.1.0"`）。
  - モジュールのエクスポートを整理（`kabusys` の `__all__` に主要サブパッケージを含める）。

- 実行/監視スクリプト
  - run_execution: 実行エンジン起動スクリプトを追加。
    - プロセス優先度を高に設定して起動。
    - 環境に応じて Paper Trading 用 DB と本番 DB を分離（`settings.is_paper` を利用）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと起動処理（スレッド実行、停止フラグ対応、PIDファイルの利用）。
    - デフォルトの RiskManager 設定値を導入（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - プロセス優先度設定、SQLite/DuckDB 接続、監視 DB の初期化。
    - 停止フラグファイル（data/stop_requested.flag）を検知して循環終了。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトへフォールバック。

- 設定管理
  - `kabusys.config.Settings` を実装。
    - 環境変数から各種設定（J-Quants トークン、kabuAPI パスワード、DB パス、Paper Trading の動作モード等）を参照するプロパティを提供。
    - `KABUSYS_ENV` の妥当性チェック（development / paper_trading / live）。
    - `PAPER_FILL_MODE` の検証（"instant" / "partial" / "never" / "reject"）。
    - DB パスやログ設定、閾値（CPU/MEM/DISK）などの取得を簡素化。

  - 自動 .env ロード機能を実装
    - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込み（OS 環境変数優先）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサは `export KEY=val`、クォート、エスケープ、インラインコメント等に対応。

  - 対話式設定ウィザード（`kabusys.config_setup`）を追加
    - 初期 .env 作成/更新の対話支援。秘密値はマスク表示。
    - 保存前に設定確認ダイアログ・キャンセル可能。
    - `.env` は生成時にコミットしない旨のヘッダを付与して出力。

  - 設定検証 CLI（`kabusys.validate_config`）を追加
    - 必須環境変数のチェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 利用可否を判定してスキップ）など。
    - `--strict` オプションで警告をエラーとして扱う。

- ポートフォリオ構築（pure functions）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（score 降順 + tie-breaker）`select_candidates`。
    - 等金額 (`calc_equal_weights`) とスコア加重 (`calc_score_weights`) の重み計算。全スコアが 0 の場合は等分にフォールバックして警告を出す。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限を適用する `apply_sector_cap`（既存ポジションのセクター比率計算、上限超過セクターの候補除外、"unknown" セクターは除外無視）。
    - 市場レジームに応じた投入倍率 `calc_regime_multiplier`（bull/neutral/bear を定義、未知レジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数決定ロジック `calc_position_sizes` を実装。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - 単元株（lot_size）での丸め、1銘柄上限・aggregate cap（available_cash）を考慮したスケールダウン、cost_buffer（手数料・スリッページ想定）を考慮した保守的見積り、残余キャッシュを使った端数配分ロジックを実装。
      - 価格無しや価格<=0の銘柄はスキップしてログ出力。

- ユーティリティ
  - ロギング設定ユーティリティ `kabusys.utils.logging_setup.setup_logging`
    - stdout に StreamHandler（stderr ではなく stdout）と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーへ設定。
    - 既存ハンドラをクリアして二重登録を防止。
    - LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority`
    - Windows と POSIX (Linux/Mac/FreeBSD) に対応する優先度設定（`set_process_priority`）。
    - `set_cpu_affinity` によりプロセスを最初の N コアにピン留め可能（権限不足や未サポート環境では警告してスキップ）。
    - psutil を利用しつつ、存在しない定数へは安全にフォールバックする実装。

- モニタリング / データベース
  - DuckDB と SQLite を併用する設計（duckdb は分析用、sqlite は監視・注文ログ用）。
  - 監視 DB の初期化ユーティリティ `init_monitoring_db` を各エントリポイントで冪等に呼び出し。

- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - PASS/FAIL 判定用の閾値を定義（稼働率 99%、fill 90%、send 95%、P95 latency 200 ms）。
    - 日付フィルタ（--from/--to）、DB パス指定（--db）に対応。
    - P95 は単純なパーセンタイル実装を提供。

- リサーチ
  - ファクター計算モジュール `kabusys.research.factor_research` を追加（Momentum 等の計算を実装予定）。
    - Momentum 関連の定数・設計方針を実装（MA200、モメンタム期間等）。（一部実装途中）

### 変更 (Changed)
- （初版につき履歴なし）

### 修正 (Fixed)
- （初版につき履歴なし）

### セキュリティ (Security)
- 環境変数の秘密情報は .env に保存する設計だが、.env を Git にコミットしないよう生成ヘッダで明記。

### 注意事項 / 補足 (Notes)
- run_execution は Paper Trading 環境（KABUSYS_ENV=paper_trading）時に専用の SQLite DB（`data/paper_trading.db`）を使用することで、本番 DB と完全分離する設計です。
- `.env` 自動読み込みはプロジェクトルートの検出を行うため、配布後やテスト環境でもカレントディレクトリに依存しにくい実装になっています。
- ログはデフォルトで logs/<app_name>.log に出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- process priority / CPU affinity の設定は権限不足や未サポート環境で例外を出さず警告してスキップします。
- factor_research モジュールは設計方針と定数が整備されていますが、計算ロジックの実装が未完了の箇所があります（今後の拡張予定）。

---

この CHANGELOG はソースコードの構造・コメントから推測してまとめたものです。実際のリリースノートには実稼働での検証結果や既知の問題（バグ、互換性、必要な外部ライブラリ等）を追記してください。