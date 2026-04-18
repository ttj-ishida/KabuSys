# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
タグ付けは semantic versioning を想定しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 基本アプリケーション構成
  - パッケージ初期化およびバージョン定義 (src/kabusys/__init__.py, __version__ = "0.1.0")。

- 起動スクリプト
  - 実取引/ペーパートレード用実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite (デフォルト: data/paper_trading.db) を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をデーモンスレッドで実行。
    - 停止フラグ (data/stop_requested.flag) 検出時に安全に停止。PID ファイルの管理。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。
  - 監視ポーリングループ起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor を用いたポーリング実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用するよう設計。
    - 停止フラグ検出でループ終了、KeyboardInterrupt による終了処理。

- 設定管理
  - Settings クラスによる環境変数ラッパ (src/kabusys/config.py)
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env / .env.local の読み込み順と上書きルール（OS 環境変数は保護）。
    - 多数の設定プロパティを提供（J-Quants トークン、kabuAPI、DB パス、paper_trading 関連、監視閾値、KABUSYS_ENV バリデーション等）。
    - PAPER_FILL_MODE の値検証（"instant"/"partial"/"never"/"reject" のみ許容）。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック。

  - .env 対話型ウィザード (src/kabusys/config_setup.py)
    - .env の初期作成・更新を対話的に支援する CLI。
    - シークレット入力対応・既存値の再利用・デフォルト値の提示。
    - .env を安全なテンプレート形式で保存（Git にコミットしない旨のヘッダ注記）。

  - 設定検証 CLI (src/kabusys/validate_config.py)
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の値チェック、DB パスや config/*.yaml の存在・パースチェック（PyYAML がない場合は YAML 検証をスキップして警告）。
    - --strict フラグで警告も失敗扱いにできる。

- ポートフォリオ構築ライブラリ (src/kabusys/portfolio/*)
  - 候補選定と重み計算 (portfolio_builder.py)
    - select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重（全スコアが 0 の場合は等金額へフォールバック）。
  - セクター集中制限・レジーム乗数 (risk_adjustment.py)
    - apply_sector_cap: 既存保有のセクター曝露に基づき新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - ポジションサイズ計算 (position_sizing.py)
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）処理、per-position 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り。
    - 割り当て調整で残余キャッシュを利用して lot 単位で配分するフェアネスロジックを実装。

- 監視・ログ・プロセスユーティリティ
  - ロギングセットアップユーティリティ (src/kabusys/utils/logging_setup.py)
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリの解決・自動作成、LOG_LEVEL / LOG_DIR の環境変数対応。
    - ファイル出力失敗時はコンソール出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差分を吸収して現在プロセスの優先度を設定（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアに固定する機能。権限不足等は警告してスキップ。

- 監視 DB 初期化 API (参照)
  - run_monitoring と run_execution の起動時に monitoring テーブルを冪等に初期化するための init_monitoring_db 呼び出しを組み込み（src/kabusys/monitoring/* は参照される実装を想定）。

- Paper Trading 検証レポートツール (src/kabusys/tools/paper_verification_report.py)
  - paper_trading 用 SQLite を解析してシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計・判定しレポート出力。
  - デフォルト閾値: 稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms。
  - 日付範囲指定オプション (--from / --to) と DB パス指定 (--db) をサポート。
  - P95 計算・欠損値の扱い・テーブル存在チェックを考慮。

- リサーチモジュール基盤 (src/kabusys/research/factor_research.py)
  - モメンタム等のファクター計算の骨子を実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。モジュールの一部が未完（calc_momentum の実装開始を含む）。

- パッケージ構造
  - ユーティリティ、ポートフォリオ、ツール、監視、実行コンポーネントを整理してエクスポート (src/kabusys/portfolio/__init__.py 等)。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Notes / Operational notes
- run_monitoring は KABUSYS_ENV に依存せず常に settings.sqlite_path（デフォルト: data/monitoring.db）を使用する点に注意。監視データは本番 DB に保存される設計。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離するため、ペーパートレードと本番の DB は混ざらない。
- .env 自動読み込みはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後や特殊な配置でプロジェクトルートが検出できない場合は自動読み込みがスキップされる。
- ログディレクトリの作成やプロセス優先度設定は権限に依存する。失敗時は警告ログを出してフォールバック動作を行うため、OS や実行ユーザーの権限に応じた運用確認を推奨。
- config_setup により生成される .env は絶対にリポジトリにコミットしないでください（生成ヘッダにも注意喚起あり）。
- research/factor_research の一部実装は継続作業が必要（calc_momentum 実装の続きなど）。

---

将来的にリリースする際は、ここに Unreleased セクションを用いて変更を積み重ね、バージョンごとにカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）で分けて記載してください。