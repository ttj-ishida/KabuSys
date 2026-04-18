# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [Unreleased]

- 現時点の差分は特になし（初期リリース 0.1.0 を参照してください）。

## [0.1.0] - 2026-04-18

初回公開リリース。自動売買システム「KabuSys」の基盤機能群を実装しています。以下はソースコードから推測される主要な追加・改善点の要約です。

### 追加 (Added)
- 全体
  - パッケージバージョンを `0.1.0` として定義。
  - パッケージ公開に必要な基本モジュール群を追加（execution, monitoring, portfolio, utils, research, tools 等）。

- 起動スクリプト / デーモン
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きに対応（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）による停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視用途の DB 初期化（init_monitoring_db）を行う。
    - Monitoring は環境にかかわらず本番用 `sqlite_path` を使用する設計。

  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を用い、Paper Trading 用 DB（data/paper_trading.db）を使用して本番 DB と分離。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知により安全に停止可能。
    - プロセス優先度を "high" に設定して起動。

- 設定管理 / CLI
  - config.py:
    - Settings クラスを導入し、環境変数のラップとバリデーションを提供。
    - .env 自動ロード機能を実装（プロジェクトルートの検出 -> .env -> .env.local の順、OS 環境変数を保護）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / DuckDB / SQLite / paper_trading パス / 各種閾値 / ログ設定 等）。
    - `PAPER_FILL_MODE` の入力検証、有効値チェックを追加。
    - `KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェックを実装。

  - config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - シークレットマスク、選択肢、デフォルト値提示、保存確認までサポート。

  - validate_config.py:
    - 起動前チェック用 CLI を追加（必須環境変数・KABUSYS_ENV・DB パス・config YAML 等の検証）。
    - `--strict` オプションで警告を失敗扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップする安全策を実装。
    - 本番環境（KABUSYS_ENV=live）時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告）。

- ポートフォリオ構築（純関数）
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全0 の場合は等配分へフォールバックし警告出力。

  - portfolio/risk_adjustment.py:
    - セクター集中制限を行う apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックで警告）。

  - portfolio/position_sizing.py:
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score" サポート）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金超過時のスケールダウン）、cost_buffer（手数料・スリッページの見積）による保守的評価、残余キャッシュを用いた端数分配ロジックを実装。
    - 将来の拡張（銘柄別 lot_size など）に関する TODO コメントあり。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一ログ設定ユーティリティを実装（StreamHandler → stdout、TimedRotatingFileHandler → 日次ローテート）。
    - 既存ハンドラのクリア処理、ログディレクトリ自動作成、ファイルハンドラ作成失敗時のフォールバックを実装。
    - ログレベル解決の優先順（引数 > 環境変数 > デフォルト）をサポート。

  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）向けプロセス優先度設定を実装（psutil を利用）。
    - CPU affinity 設定関数（set_cpu_affinity）を提供。
    - アクセス拒否や未実装 API に対して安全にフォールバックする警告処理を実装。

- モニタリング / DB 初期化
  - monitoring モジュール（初期化関数 init_monitoring_db を参照）により起動時に監視用テーブルの存在保証を行う（冪等）。

- 分析・レポートツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB を対象に検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う（閾値はソース内で定義）。
    - SQL クエリは欠損テーブルに対して例外を捕捉し安全に動作。

- 研究用モジュール（骨組み）
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity 等のファクター設計と計算方針（DuckDB ベース）を記述。モメンタム計算に必要な定数や関数雛形を追加。

### 変更 (Changed)
- 環境変数ロード順序を明確化:
  - OS 環境変数 > .env.local > .env（.env.local が .env を上書き）。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加してテスト等で制御可能。
  - .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

- .env パーシング強化:
  - export プレフィックス（export KEY=...）に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を実装。
  - クォートなし値のコメント認識時に、`#` の直前がスペースまたはタブの場合のみコメントとして扱う等、より厳密に解析。

- ログ設定の堅牢化:
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみにフォールバックする実装に変更。

- 実行環境分離:
  - ExecutionEngine は paper_trading 時に専用の SQLite を使用し、本番 DB と完全分離する挙動を明示。

### 修正 (Fixed)
- 複数のモジュールでエラー発生時に例外を捕捉してループやプロセスを継続する実装を追加（監視ループの check_once() 呼び出し等）。これにより一時的な内部例外でプロセス全体が落ちるのを防止。

### 既知の問題 / 注意事項 (Known issues / Notes)
- research/factor_research.py の calc_momentum 関数の実装が途中（スニペット末尾に途中文字列が見える）であるように見えます。完全実装は未完の可能性があるため、本番運用前に要確認・実装完了が必要です。
- position_sizing の価格欠損（price が 0.0 や None）の場合エクスポージャーが過少見積りされる旨の TODO コメントあり。前日終値等をフォールバックする拡張が推奨されています。
- process_priority / set_cpu_affinity は psutil の権限やプラットフォーム依存のため、権限不足時や未対応 OS では警告を残してスキップします。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラを作成しない挙動となるため、ログファイルを期待する運用環境では権限やパスの事前準備が必要です。

### セキュリティ (Security)
- シークレット値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存する前提だが、.env を決してリポジトリにコミットしない旨を README / ウィザードヘッダーに明記しています。運用時は OS 環境変数や安全なシークレット管理を推奨。

---

開発・運用チーム向け補足:
- 初回セットアップ手順:
  1. .env を作成（python -m kabusys.config_setup）
  2. 設定検証（python -m kabusys.validate_config）
  3. 必要な DB の作成（実行スクリプトが自動で親ディレクトリを作成するが DB スキーマ準備が必要な場合は別途スクリプトを実行）
  4. 実行: python -m kabusys.run_monitoring / python -m kabusys.run_execution

（必要に応じて各モジュールの詳細仕様・未実装部分を追ってドキュメント化してください）