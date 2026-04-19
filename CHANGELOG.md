# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。ここに記載されている内容は、提供されたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

### 追加予定
- 追加のユニットテスト
- factor_research の残り実装（calc_momentum の実装途中の続き）
- 監視・実行エンジンの運用ドキュメント追記

---

## [0.1.0] - 2026-04-19

初期公開リリース。システムのコア機能一式を実装。

### Added
- 基本パッケージとバージョン
  - パッケージ定義: `kabusys`、バージョン `0.1.0` を追加（src/kabusys/__init__.py）。

- 設定管理
  - Settings クラスによる環境変数ベースの設定管理を追加（src/kabusys/config.py）。
    - 自動 .env 読み込み（プロジェクトルートの検出、.env と .env.local の取り扱い）。
    - 必須/オプション変数の取得用プロパティ（J-Quants、kabu API、DB パス、ログ等）。
    - PAPER_FILL_MODE、paper_sqlite_path、KABUSYS_ENV 等の検証ロジックを実装。
  - 環境設定ウィザード CLI を追加（python -m kabusys.config_setup）。
    - 対話式で .env を作成/更新する機能（.env の読み書き、シークレットのマスク表示）。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース確認、live 環境向けガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- 実行 / 監視プロセス
  - Execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を上げる（High）。
    - paper_trading 環境では専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - Broker クライアントのファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組立てと起動ロジック（デーモンスレッド起動、停止フラグ監視）。
    - 起動時の PID ファイル出力（data/execution.pid）や停止フラグ（data/stop_requested.flag）に対応。
  - Monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグ検知でループ終了、例外時はログを出して次ポーリングへ継続。

- ロギング / プロセス管理ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順・ディレクトリ作成失敗時のフォールバックを実装。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収して優先度設定を行う。
    - set_cpu_affinity() によりプロセスを最初の N コアにピン固定する機能を提供。
    - 権限不足や未サポート環境では警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
    - スコアが全て 0 の場合のフォールバックを実装（警告ログ）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮してセクター上限を適用・除外）を実装。
    - calc_regime_multiplier（bull/neutral/bear に応じた乗数）を実装。未知レジームはフォールバック（1.0）と警告。
    - 設計コメントや将来的な改善点（価格フォールバック等）を明記。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes により allocation_method（risk_based / equal / score）に基づく発注株数を計算。
    - 単元株（lot_size）丸め、個別・総投下上限、cost_buffer を考慮したスケールダウンロジックを実装。
    - aggregate cap のスケール・残余配分ロジックを実装。

- research
  - ファクター計算モジュールのスケルトンを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針、定数、インタフェースを定義。
    - calc_momentum 関数の冒頭まで実装（以降の実装は継続中）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - paper_trading の SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数を抽出してレポートを生成。
    - PASS/FAIL 基準（稼働率、fill_rate、send_rate、P95 レイテンシ等）を定義して判定を出力。
    - コマンドライン引数で期間指定（--from, --to）や DB パス指定（--db）に対応。

- DB 接続サポート
  - sqlite3 と DuckDB（duckdb）を利用するコードが複数のコンポーネントで利用されるよう実装（Execution/Monitoring/Research/Tools）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサーの堅牢化（src/kabusys/config.py）
  - export 形式のサポート、クォート内のバックスラッシュエスケープ処理、行末コメント処理などを実装して .env の取り扱いを堅牢化。

### Removed
- （初回リリースのため該当なし）

### Security
- 機密値（トークン・パスワード）はウィザードでマスク表示。`.env` は Git へコミットしない旨を .env ファイルヘッダに明記。

### 注意事項 / 既知の制限
- factor_research.calc_momentum の実装が途切れている（スケルトン実装）。実運用で必要なファクター計算は追加実装が必要。
- position_sizing の lot_size は現在全銘柄共通の想定。将来的には銘柄別単元対応が望ましい（TODO コメントあり）。
- apply_sector_cap は "unknown" セクターに対してセクター上限を適用しない設計。必要に応じて方針変更の検討が必要。
- process priority / cpu affinity の設定は権限や OS により失敗する可能性があり、その場合は警告を出して処理を継続する。
- ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続する。

### CLI / 実行方法（抜粋）
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

（注）上記は提供されたソースコードの内容から推測して作成した CHANGELOG です。実際のコミット履歴や変更履歴に基づくものではありません。必要ならば各項目を実際の git コミットやリリース計画に合わせて調整できます。