# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはプロジェクト初期の公開バージョンに合わせて、コードベースから推測して作成した変更点を日本語でまとめたものです。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 基本パッケージ情報
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。

- 実行スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` の存在で検知。
    - Monitoring は環境にかかわらず本番（settings.sqlite_path）を使用して監視 DB に接続。
    - duckdb との接続確立、init_monitoring_db による監視テーブル初期化、例外ハンドリング実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時はペーパートレード用 DB（デフォルト `data/paper_trading.db`）を使用し、本番 DB と明確に分離。
    - 停止フラグ（`data/stop_requested.flag`）検知で実行エンジンを安全に停止。
    - 実行中は PID ファイル (`data/execution.pid`) を使用する仕組みを提供。
    - 実行前に監視テーブルの存在を保証するため `init_monitoring_db` を呼び出し（冪等）。

- 設定管理・環境読み込み
  - config.py: Settings クラスを実装。
    - .env ファイルおよび環境変数から設定を自動ロード（`.env` → `.env.local`、OS環境変数を保護）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `.env` パースロジックは `export KEY=val`、クォート、エスケープ、インラインコメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定 等）。
    - `PAPER_FILL_MODE` や `KABUSYS_ENV`、`LOG_LEVEL` 等の値検証を実装。
    - プロジェクトルート検出ロジック（`.git` または `pyproject.toml` を探索）を提供。

- 設定ユーティリティ & CLI
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加。
    - 複数の設定項目を対話的に入力可能。シークレット項目はマスク表示。
    - 既存 .env の読み込み・再利用、保存確認、`.env` 書き込み機能を提供。
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML 有無に応じて）を検証。
    - `--strict` オプションで警告も失敗扱いにできる。
  - tools.paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 指定期間のシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集約してレポート出力。
    - 各種閾値（稼働率、成功率、P95 レイテンシ等）に基づく PASS/FAIL 判定を実装。
    - `--from` / `--to` / `--db` オプションでレポート範囲や DB を指定可能。

- ロギング & プロセス優先度ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決優先度を実装。既存ハンドラのクリーンアップを実施。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）差異を吸収して優先度を設定（psutil を使用）。
    - CPU affinity 固定機能（最初の N コアにピン留め）を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順 + タイブレークに基づく候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（スコア全0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮）と候補除外ロジックを実装。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは警告後フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method による発注株数決定（risk_based / equal / score）。
    - 単元株丸め、銘柄上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer を考慮した安全な配分ロジックを実装。

- リサーチ（骨格）
  - research/factor_research.py:
    - ファクター計算モジュールの骨格を追加（モメンタム / MA200 / ATR / ボリューム系の計算方針）。DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する設計。
    - （ファイル末尾で計算関数の実装が途中で始まっているため、今後完成予定の旨が想定される）

### 変更 (Changed)
- なし（初期リリースのため新規機能追加が中心）

### 修正 (Fixed)
- なし（新規追加のため既存バグ修正履歴は無し）

### 注意事項・設計上のポイント (Notes)
- .env 自動ロードは OS 環境変数を優先し、`.env.local` は `.env` の上書きに使える（ただし OS 環境変数は保護）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring と run_execution はプロセス優先度を最初に "high" に設定します（実行環境や権限により無効化される場合があります）。
- run_execution は paper_trading モード時に本番 DB と完全分離して専用 SQLite を使用することで、テスト時の安全性を担保します。
- logging_setup は標準エラーではなく標準出力（stdout）に StreamHandler を出す設計のため、外部スケジューラやリダイレクトとの相性を考慮しています。
- process_priority や CPU affinity の操作は権限・プラットフォーム依存のため、失敗した場合に警告を出して処理を継続する設計になっています。
- Paper Trading 検証レポートは DB のスキーマ（system_status / trade_logs / risk_logs 等）に依存します。該当テーブルが存在しない場合は安全に N/A を返してレポートを生成します。

---

今後の予定（推測）
- research/factor_research.py の完全実装（ファクター計算の詳細ロジック）。
- Strategy / Execution コンポーネントのさらなる統合テスト、監視・アラートの強化、そしてドキュメント整備。