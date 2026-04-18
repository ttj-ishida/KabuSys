# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルは、ソースコードから推測される機能追加・仕様・修正点を基に作成した変更履歴です。

最新リリース
=============

Unreleased
----------

- （将来用のプレースホルダ）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション構成を提供
  - パッケージ初期バージョンとしての公開（`__version__ = "0.1.0"`）。
- 起動スクリプト / CLI
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）を監視して安全停止。
    - PID ファイル出力（data/execution.pid）。
    - プロセス優先度を起動時に "high" に設定。
    - 環境が `paper_trading` の場合は専用のペーパートレード用 SQLite（`data/paper_trading.db`）を使用し、本番データベースと分離。
    - Broker クライアントの抽象化を行う `BrokerClientFactory` によるブローカー切替。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager の既定設定をコード内で定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - SystemMonitor を定期的にポーリングして状態を記録。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き（デフォルト: 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境に関係なく本番用の SQLite パス（Settings.sqlite_path）を使用して初期化。
    - 停止フラグファイルの検知でループ終了。
- 設定管理
  - 環境/設定読み込みモジュール: `src/kabusys/config.py`
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env の自動読み込みを行う（`.env` → `.env.local` の順、OS 環境変数を保護）。
    - 文字列パーサーはシングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理（クォート無しの場合の '#' 処理）などに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
    - Settings クラスで多数の設定プロパティを提供（J-Quants/KabuAPI/LINE/DB/監視閾値/環境判定等）。
    - `is_live` / `is_paper` / `is_dev` 判定プロパティ。
    - Paper Trading 用の `PAPER_FILL_MODE` 検証（許可値: instant|partial|never|reject）。
- 設定ユーティリティ / バリデーション / ウィザード
  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、DB パス・YAML ファイル存在チェック、production 向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の注意喚起）を実施。
    - `--strict` オプションで警告を失敗扱いにできる。
  - 環境設定ウィザード: `src/kabusys/config_setup.py`
    - 対話式で .env の初期作成 / 更新を支援。シークレット項目はマスク表示。
    - 既存 .env の読み込み、保存用フォーマット出力を実装。
- 解析 / ツール
  - Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計・判定してレポートを出力。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - コマンドライン引数で期間指定および DB パス指定が可能。
- ポートフォリオ構築モジュール
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（スコア降順＋同点時の tie-break）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限の適用（既存保有を考慮して上限を超えるセクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返すユーティリティ。
  - `src/kabusys/portfolio/position_sizing.py`
    - 等配分/スコア配分/リスクベースの複数配分方式に対応した発注株数算出。
    - 単元株（lot_size）丸め、1銘柄上限・集合上限（aggregate cap）や cost_buffer（手数料・スリッページ推定）を考慮したスケーリング・再配分ロジックを実装。
- ユーティリティ
  - ログ設定ユーティリティ: `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定する共通セットアップ。
    - LOG_DIR 作成失敗時にファイル出力をスキップしてコンソールのみ継続するフェイルセーフ。
    - ログレベル解決（引数 > 環境変数 > デフォルト）を実装。
  - プロセス優先度 / CPU affinity ユーティリティ: `src/kabusys/utils/process_priority.py`
    - Windows/Linux/macOS 等を吸収した優先度設定（psutil 利用）。アクセス権限不足等は警告してスキップ。
    - CPU affinity を最初の N コアに固定する機能を提供（存在しない環境では警告してスキップ）。
- 研究モジュール（部分実装）
  - `src/kabusys/research/factor_research.py`
    - モメンタム、移動平均乖離、ATR、流動性などファクター計算の設計を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。
    - 実装は一部（ファイル末尾での断片的なコード）であり、継続実装が必要。

Changed
- 初期リリースに伴うアーキテクチャ上の決定とデフォルト値の明示
  - Execution / Monitoring が DuckDB および（Paper 用・本番）SQLite を併用するデータフローを採用。
  - ログ出力は stdout をメインにしつつファイルローテーションを付与する方式に統一。

Fixed
- （初回リリースのため該当なし、実装上での既知の失敗ハンドリングは警告ログで扱う実装を採用）

Security
- 機密情報取り扱い
  - .env の対話式ウィザードはシークレット項目をマスク表示。ただし .env は Git にコミットしない旨を README に注意喚起している（.env の扱いに注意）。

Notes / その他
- 設計上の注意点や TODO
  - `apply_sector_cap` はセクター不明 ("unknown") を除外しない設計。price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に価格フォールバックの導入を検討する旨のコメントあり。
  - `calc_regime_multiplier` は未定義レジームに対して 1.0 でフォールバックし、警告ログを出す。
  - `position_sizing.calc_position_sizes` の将来的拡張として銘柄別 lot_size の対応が想定されている（現状は全銘柄共通の lot_size）。
  - `research/factor_research.py` の実装は途中でファイルが終端しており、継続実装が必要。

今後の予定（推測）
- research モジュールの完成（ファクター計算の全実装・最適化、DuckDB 上の SQL 最適化）。
- ExecutionEngine / BrokerClient の実運用でのテストと調整（レート制限、サーキットブレーカーのパラメータチューニング）。
- ペーパートレード検証ツールの拡張（CSV 出力・詳細メトリクス・可視化）。

---

この CHANGELOG はソースコードの内容とコメントから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要ならばリポジトリのコミットログやリリース方針に基づいて調整します。