# Changelog

すべての重大な変更はこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
慣例に従い、セマンティックバージョニングを使用します。

注: 以下の変更点は提供されたコードベースの内容から推測して記載しています。実際のコミット履歴ではなく、ソースコードの実装に基づく要約です。

## [Unreleased]

（保留中の変更はここに記載します）

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーションの初期実装を追加。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を設定。
- 実行/監視用エントリスクリプトを追加。
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI ランチャーを実装。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用の SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全に分離する実装。
    - BrokerClientFactory により実行時に適切なブローカクライアントを生成（paper と live の分岐を想定）。
    - Engine の別スレッド実行と停止フラグ（`data/stop_requested.flag`）監視を実装。
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動用スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。不正値は安全にフォールバックしてログ出力。
    - 監視は環境にかかわらず本番（`Settings.sqlite_path`）の sqlite パスを使用するよう明記。
    - 停止フラグ検出でループを終了、例外はログ出力して次ポーリングへ継続。
- 設定管理と自動 .env 読み込み機能を追加。
  - `src/kabusys/config.py`
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - `.env` / `.env.local` の読み込み順序を実装（OS 環境変数が優先され、.env.local が .env を上書き）。
    - 自動ロード無効化環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 環境変数パーサーは export 構文、クォート、エスケープ、インラインコメント等に対応。
    - `Settings` クラスを提供し、J-Quants / kabu API / DB / 監視など各種設定値の取得とバリデーションを実装。
    - `paper_fill_mode` の検証（許容値: instant|partial|never|reject）や `KABUSYS_ENV` / `LOG_LEVEL` の検証を実装。
- 設定支援・検証用 CLI を追加。
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで .env を生成・更新するツールを実装。
    - 各設定項目の説明、デフォルト、シークレット入力の扱いをサポート。
  - `src/kabusys/validate_config.py`
    - 起動前に .env と config/*.yaml の設定不備を検出する検証スクリプトを実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ファイルパスの親ディレクトリ存在チェック、YAML パース（PyYAML インストール時）、本番特有のガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START 設定等）を行う。
    - `--strict` オプションでワーニングをエラー扱いにできる。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ内計算）。
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（スコア降順、signal_rank でタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバック）を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限の適用（当日売却予定コードを除外可能）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告の上フォールバック。
  - `src/kabusys/portfolio/position_sizing.py`
    - 各種配分方式（risk_based / equal / score）に基づく発注株数算出を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）および残差処理（端数分を優先度に応じて再配分）を実装。
    - cost_buffer による保守的なコスト見積りを考慮。
  - `src/kabusys/portfolio/__init__.py` で上記をエクスポート。
- 監視・実行エンジン用 DB 初期化呼び出しを追加（冪等性確保）。
  - `monitoring_db.init_monitoring_db` を run_* スクリプトで呼び出し、監視テーブルが存在することを保証。
- ユーティリティ: プロセス優先度 / CPU affinity の設定を追加。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足等で失敗した場合は警告を出し安全にスキップ。
- 研究用ファクタ計算（DuckDB ベース）を追加（部分実装）。
  - `src/kabusys/research/factor_research.py`
    - モメンタム（1m/3m/6m）や 200 日移動平均乖離、ATR / 流動性指標の計算ロジックを DuckDB SQL で実装。prices_daily テーブル依存。
- ツール: Paper Trading 検証レポートを追加。
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計し、閾値に基づく PASS/FAIL レポートをコンソール出力。
    - P95 計算、期間フィルタ、DB 存在チェック、各種 SQL クエリに安全対策（テーブル欠如時のハンドリング）を実装。
- 署名・モジュール構成の整備。
  - `src/kabusys/tools/__init__.py`, `src/kabusys/utils/__init__.py` 等を整備。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （該当なし）

### Notes / Notable behaviors
- run_monitoring は「監視」は常に Settings.sqlite_path（本番の sqlite パス）を使用する実装になっています。開発環境で監視用 DB を別にしたい場合は設定の見直しが必要です。
- .env の自動読み込みはデフォルトで有効。テストや CI で自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `KILL_FLAG_CLEAR_ON_START` の値が本番で `1` に設定されていると危険である旨のチェックが validate_config に含まれています。
- position sizing のスケーリングや lot_size の扱いには保守的な設計（端数処理・cost_buffer）が取り入れられており、将来的な銘柄別単元対応のための TODO コメントがあります。
- DuckDB を用いる研究モジュールは prices_daily / raw_financials テーブルを前提としており、これらのテーブルが存在しない場合はエラー回避のためのハンドリングが必要です（validate_config で config ファイルの存在確認は行うが、DB スキーマ検証は実装されていません）。

---

（注記）上記は提供されたソースコードの内容から推測してまとめた CHANGELOG です。実際の変更履歴（コミット単位の差分）やリリースノート作成方針に応じて、項目の粒度や日付、重要度の分類を調整してください。