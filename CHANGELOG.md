# Changelog

すべての注目すべき変更点を記録します。これは Keep a Changelog の形式に従っています。  
リリースは semver 準拠を想定しています。

※ この CHANGELOG は提示されたコードベースから推測して作成しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 基本パッケージ初回実装
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine の起動エントリポイントを実装。
    - プロセス優先度を High に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、`ExecutionEngine.run_session` を別スレッドで実行。
    - 停止制御: `data/stop_requested.flag` を監視し、検出時に安全停止。
    - 実行 PID ファイル管理（`data/execution.pid` などのパス指定）。

  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用して監視データを記録。
    - 停止制御: `data/stop_requested.flag` を検知してループを終了。
    - エラー発生時は例外をキャッチしてログに出力し、次ポーリングまで待機。

- 設定管理 / 自動 .env 読み込み
  - `config.py`
    - 環境変数と設定値を扱う `Settings` クラスを実装。多くのプロパティ（J-Quants / kabu API / DB パス / Paper Trading 関連 / 監視閾値 / ログ設定 等）を提供。
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を実装し、これにより配布後も CWD に依存せず .env の自動読み込みが可能。
    - `.env` / `.env.local` の自動読み込み機構を導入。OS 環境変数は保護され、`.env.local` は `.env` の上書きに使用。
    - `.env` 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - `PAPER_FILL_MODE` のバリデーション、`paper_sqlite_path` など paper_trading 向け設定を実装。
    - `env` / `is_live` / `is_paper` など環境判定ユーティリティを提供。

- 設定検証 CLI
  - `validate_config.py`
    - `.env` と `config/*.yaml` の設定不備を起動前に検出する CLI を実装。
    - 必須環境変数のチェック（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` 等）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値チェック。`live` 時の追加ガード（LINE 通知設定未設定時の警告、KILL_FLAG_CLEAR_ON_START 設定の警告等）。
    - DuckDB / SQLite のパス存在チェック（親ディレクトリの有無に関する警告）。
    - PyYAML の有無を確認し、存在すれば config YAML のパース検証を行う（パース失敗はエラー）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 設定ウィザード CLI
  - `config_setup.py`
    - インタラクティブな `.env` 作成・更新ウィザードを実装。
    - J-Quants / kabu API / DB パス / LINE 通知 / ログレベル / Kill Switch など主要設定項目を対話的に収集・保存。
    - 既存の `.env` 読み取り、シークレットのマスク表示、選択肢のバリデーション、保存確認をサポート。

- ロギング / プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーへ一貫したログ設定を提供。
    - stdout へ StreamHandler、日次ローテーション（TimedRotatingFileHandler）でファイル出力を設定（デフォルト logs/<app_name>.log、30日保持）。
    - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ稼働。

  - `utils/process_priority.py`
    - Windows / POSIX の差を吸収するプロセス優先度設定を実装（"high"/"normal"/"low"）。
    - CPU affinity 設定ユーティリティ `set_cpu_affinity` を提供。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ
  - `portfolio/portfolio_builder.py`
    - シグナル候補の選定（スコア降順・タイブレーク）と重み計算（等分配 / スコア加重）を実装。

  - `portfolio/risk_adjustment.py`
    - セクター集中制限適用（既存保有を考慮して新規候補をフィルタ）。
    - 市場レジームに基づく投下資金乗数（bull/neutral/bear）を提供。
    - 未知レジームは 1.0 にフォールバックして警告を出す。

  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数算出ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）対応、1 銘柄上限・集計上限、コストバッファを考慮したスケーリング処理を実装。
    - スケールダウン時の端数取り扱い（lot 単位での追加配分）や安全弁の実装。

  - `portfolio/__init__.py` で主要関数をエクスポート。

- 研究用ファクター計算（途中実装）
  - `research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity ファクターの設計と計算方針を実装（DuckDB 経由で prices_daily / raw_financials を参照する想定）。
    - モメンタム計算のための定数（1M/3M/6M・MA200・ATR 等）を定義。モジュールは DuckDB 接続を受け取り純粋関数として動作する設計。

- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - paper trading の SQLite（`PAPER_TRADING_SQLITE_PATH`）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計してレポート出力。
    - PASS/FAIL の閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を設定。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

### 変更 (Changed)
- なし（初回リリース想定）

### 修正 (Fixed)
- なし（初回リリース想定）

### 注意点 / 既知の制約 (Notes / Known issues)
- `config._load_env_file` の .env パースはシンプルな実装で、引用符内のバックスラッシュエスケープやコメント処理に独自ロジックを採用しているため、非常に複雑な .env 行は想定外の扱いになる可能性がある。
- `portfolio/risk_adjustment.apply_sector_cap` の価格欠損処理に TODO コメントがあり、価格が欠損するとエクスポージャー過少見積りとなる可能性がある（将来的にフォールバック価格を導入予定）。
- `position_sizing` は現状すべての銘柄で同一の単元株数（lot_size=100）を仮定。将来的に銘柄別 lot_size 対応が予定されている。
- `research/factor_research.py` はモメンタム計算を含む実装の一部が途中で終わっているため、完全なファクター計算の利用には追加実装が必要。

### セキュリティ (Security)
- なし（初回リリース想定）

---

今後のリリースでは、テストケース追加、DuckDB のスキーマ/テストデータ、Research モジュールの完成、各種例外ハンドリング強化、パフォーマンス最適化などを反映する予定です。必要があれば、この CHANGELOG を基にバージョン分けや追加項目を追記します。