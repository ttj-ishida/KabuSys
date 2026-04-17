# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

全般的な注意:
- 環境変数はプロジェクトルートの .env / .env.local（存在する場合）から自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 多くの機能は DuckDB / SQLite をデータストアとして想定しています。実行時のパスは環境変数で上書き可能です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能とユーティリティ、ポートフォリオ構築ロジック、監視／実行用ランチャースクリプトを含みます。

### Added
- 環境設定と自動読み込み
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を追加（src/kabusys/config.py）。
  - 読み込みは OS 環境変数を上書きしない（既存のキーは保護）。override 引数で上書き挙動を制御可能。
  - .env の各行パースロジックを実装。`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いに対応。

- Settings（環境変数ラッパー）
  - Settings クラスを追加して各種設定をプロパティ経由で取得可能に（src/kabusys/config.py）。
  - J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定などをプロパティ化。
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の値検証を実装（不正値で例外）。

- .env 設定ウィザード
  - 対話式ウィザードで .env を生成・更新する CLI を追加（src/kabusys/config_setup.py）。
  - 必須項目・任意項目・デフォルト値・シークレット項目のマスク表示対応。生成された .env のテンプレート出力機能あり。

- 設定検証ツール
  - 起動前に .env や config/*.yaml の基本的妥当性を検証する CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パス親ディレクトリの存在チェックを実装。
  - PyYAML がインストールされていれば config/*.yaml のパース検証を実施。--strict オプションで警告を FAIL 扱いに可能。

- 実行エンジン起動スクリプト
  - ExecutionEngine を起動するランチャーを追加（src/kabusys/run_execution.py）。
  - プロセス優先度を最初に High に設定（utils/process_priority.set_process_priority を使用）。
  - 環境が paper_trading の場合は paper 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント選択、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動、停止フラグ（data/stop_requested.flag）検出による安全停止を実装。
  - エンジン起動時に監視用テーブルの初期化を行う（init_monitoring_db）。

- 監視ループ起動スクリプト
  - SystemMonitor のポーリングループ起動用スクリプトを追加（src/kabusys/run_monitoring.py）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
  - 監視は環境にかかわらず本番 sqlite_path（data/monitoring.db がデフォルト）を利用して監視データを記録。
  - 停止フラグ（data/stop_requested.flag）を検出してループを終了。例外発生時もロギングして次回ポーリングに待機。

- Paper Trading 検証レポートツール
  - ペーパートレード用 SQLite を解析して検証レポートを生成する CLI を追加（src/kabusys/tools/paper_verification_report.py）。
  - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。P95 の計算実装あり。
  - しきい値定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）に基づいて PASS/FAIL 判定を出力。
  - 日付レンジ指定（--from, --to）および DB パス指定（--db、環境変数 PAPER_TRADING_SQLITE_PATH にも対応）。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点時は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコアに基づく配分（全スコアが 0 の場合は等金額にフォールバックし警告）

  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクターエクスポージャを計算し、1 セクター上限超過時に新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（未知の値は 1.0 にフォールバックして警告）。

  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method による株数計算（"risk_based" / "equal" / "score"）を実装。
    - risk_based: risk_pct, stop_loss_pct を用いた株数算出。
    - equal/score: weight に基づく配分、max_position_pct による per-position 上限、lot_size（単元）での丸め。
    - aggregate cap（available_cash 超過時）のスケーリング処理、残差に対する lot 単位での再配分ロジックを実装。
    - cost_buffer による保守的コスト見積もりをサポート。
    - 価格欠損・小数切り捨て等のケースでのログ出力（デバッグ）あり。

- 研究用ファクター計算モジュール
  - モメンタム／ボラティリティ等のファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB の prices_daily テーブルから計算（ウィンドウ不足時は None）。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比率などを計算（true_range の NULL 伝播制御などを実装）。
    - 計算は DuckDB 上の SQL を利用して効率的に行う設計。

- ユーティリティ: プロセス優先度 / CPU affinity
  - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows（psutil の priority constants）と POSIX（nice 値）を吸収して抽象化。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 許可不足や未対応 OS では警告を出しつつ安全にスキップ。

- パッケージ基礎
  - パッケージ初期化ファイルにバージョン 0.1.0 を追加（src/kabusys/__init__.py）。
  - パッケージエクスポート: portfolio 関連関数を __all__ で公開。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- .env は生成テンプレート内で「絶対に Git にコミットしないこと」を強調。ウィザードはシークレット項目をマスクして表示。

---

変更点に関する補足や不明点があれば、どの機能について詳しくドキュメント化するか（例：API 仕様、コマンド例、設定例、サンプル .env）を指示してください。必要に応じて英語版 CHANGELOG 生成も可能です。