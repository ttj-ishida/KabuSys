# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

現在のバージョン: 0.1.0（初回リリース）

注意: 以下の変更履歴はソースコードの内容から推測して作成した要約です。実際のコミット履歴や設計文書に基づくものではありません。

## [Unreleased]

- ドキュメント・テスト目的の軽微な調整やログ出力の改善などの小修正を想定しています。

---

## [0.1.0] - 2026-04-17

初回公開リリース。自動売買システム KabuSys の基本コンポーネントを実装。

### Added
- コア設定管理
  - Settings クラスを実装し、環境変数および .env / .env.local ファイルからの自動読み込みを提供。
  - プロジェクトルートを .git / pyproject.toml から探索して .env 自動読み込みを行う仕組みを導入。
  - .env のパース機能を堅牢化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い対応）。
  - 必須環境変数取得ヘルパー（_require）を追加。

- 環境設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
  - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）をサポート。
  - 生成される .env に注意書きを含め、Git にコミットしない旨を明記。

- 設定検証ツール
  - validate_config.py: .env および config/*.yaml の存在・形式（PyYAML があればパース）・重要環境変数の妥当性をチェックする CLI を追加。
  - --strict オプションで警告を FAIL 扱いにできる。

- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動するワークフローを実装。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨（コード上の動作）。

- モニタリング DB 初期化
  - monitoring_db.init_monitoring_db を起動時に呼び出して監視用テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差を吸収する set_process_priority(level) を実装（Windows / POSIX の優先度設定対応）。
    - set_cpu_affinity(cpu_count) による CPU affinity 固定機能を追加。
    - 権限不足や未対応環境では警告ログを出してフォールバック。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates（スコア順選定）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、スコア合計が 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py:
    - apply_sector_cap（セクター集中度制限）
    - calc_regime_multiplier（市場レジームに応じた資金乗数）
  - portfolio/position_sizing.py:
    - calc_position_sizes（position sizing：risk_based / equal / score の配分アルゴリズム、単元株丸め、aggregate cap のスケールダウンロジックなど）

- リサーチ（ファクター計算）
  - research/factor_research.py:
    - DuckDB 接続を受け取り prices_daily / raw_financials から各種ファクター（モメンタム、MA200乖離、ATR、売買代金等）を計算する関数を提供。
    - calc_momentum / calc_volatility 等を実装（ウィンドウ不足時の None 取り扱い、P99/P95 等の考慮に対応可能な構成）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ統計等を集計・レポート化する CLI を追加。
    - PASS/FAIL 判定基準（稼働率、成功率、送信率、P95 レイテンシ）を実装。
    - --from / --to / --db オプションに対応。

### Changed
- 実行環境分離
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用することで本番データベースと完全に分離する設計を採用。
- .env 自動読み込みの挙動
  - OS 環境変数を保護するための上書き制御（.env → .env.local の順でロードし、既存 OS 環境変数を protected として扱う）を実装。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート文字内のバックスラッシュエスケープ、インラインコメント取り扱いなど、複雑な .env フォーマットに対応（以前の単純実装で失敗しうるケースを回避）。
- process_priority の例外ハンドリング改善
  - 権限不足や未実装 API での失敗をキャッチして警告ログを出し、プロセスは継続するように修正。

### Security
- .env ファイルは出力ヘッダで「絶対に Git にコミットしないこと」と明記（config_setup にて）。

### Notes / Migration
- Monitoring（run_monitoring）は明示的に Settings.sqlite_path（デフォルト: data/monitoring.db）を使用するため、他の環境（paper_trading 等）でも監視 DB は共有されます。監視データの切り離しが必要であれば設定を見直してください。
- KILL_FLAG_CLEAR_ON_START の値が本番環境で 1 に設定されていると危険である旨を validate_config で警告します。運用時はデフォルト 0 を推奨します。
- PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH の設定により、ペーパートレードの挙動を柔軟に切り替えできます。

---

## 今後の予定（例）
- strategy/engine や execution のさらなるテスト追加、ログ出力の強化。
- 銘柄ごとの lot_size 対応（stocks マスタから読み込み）による position_sizing の拡張。
- DuckDB を使ったファクター計算の追加最適化とキャッシュ機構。
- monitoring のアラート送信（LINE 連携）の実装強化。

---

関連ファイル・参考
- src/kabusys/__init__.py: バージョンは 0.1.0 に設定済み
- CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数の要点:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 実行環境: KABUSYS_ENV = development | paper_trading | live

もし特定のファイルや変更点についてより詳細な差分ベースの CHANGELOG(コミット単位)が必要であれば、コミットログや差分を提供してください。