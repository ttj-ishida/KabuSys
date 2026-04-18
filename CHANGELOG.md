# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルは、リポジトリ内のソースコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-18
初回リリース（推測）。自動売買システム KabuSys のコア機能群を実装・追加。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグファイルで制御。
    - 監視（monitoring）用 DB は実行環境にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時はペーパートレード専用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離する仕様。
    - ブローカークライアント生成は BrokerClientFactory を利用。エンジンは別スレッドで実行され、停止フラグで安全に停止可能。
    - PID ファイルを data/execution.pid に保存する仕組みを想定。

- 設定管理・ユーティリティ
  - config.py
    - .env の自動読み込み機能（.env / .env.local）を追加。プロジェクトルートの判定は .git / pyproject.toml を探索して行うため、CWD に依存しない。
    - export KEY=val 形式やクォート値、インラインコメントの扱いなど、堅牢な .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止対応。
    - Settings クラスを導入し、各種設定値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE など）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を追加。
    - 環境種別（development / paper_trading / live）やログレベルの検証、有用なデフォルト値を提供。

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在および簡易パース検証（PyYAML があれば内容も検証）などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - J-Quants／kabu API／DB パス／ログレベル／Kill Switch などの主要設定を対話形式で編集・保存できる。
    - .env の出力テンプレートを提供し、.env をコミットしない旨を明示。

  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout を使う StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイル（logs/<app_name>.log）へ出力。ローテーションは 30 日分保持。
    - 既存ハンドラのクリーンアップ、LOG_LEVEL / LOG_DIR の解決順序を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（Windows/Linux/macOS の差分を吸収）。
    - set_process_priority(level) で "high"/"normal"/"low" をサポート。権限不足等は警告ログで無害にフォールバック。
    - set_cpu_affinity(cpu_count) により最初の N コアにプロセスをピン留めする機能を追加（対応不可環境は警告でスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順・同点時 tie-break）、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - スコアが全て 0 の場合のフォールバックを実装（等金額配分に落とす）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有と当日売却予定を考慮して新規候補を除外。
    - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単位株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）に対するスケーリング、cost_buffer による手数料・スリッページ保守見積り、残余キャッシュを使った端数配分アルゴリズム等を含む。

  - portfolio/__init__.py
    - 上記関数をまとめてエクスポート。

- リサーチ / ファクター計算（着手）
  - research/factor_research.py
    - モメンタム・ボラティリティ等のファクター計算の骨子（calc_momentum 等）を追加。DuckDB 経由で prices_daily / raw_financials を参照して計算する設計。関数仕様・スキャン幅などの定数を定義（例: MA200、ATR の窓長など）。
    - 実装はファイル末尾で途中（切り出し）だが、設計方針とインターフェースが定義されている。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成ツールを追加。
    - Paper Trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポートを出力。
    - PASS/FAIL 判定閾値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）し、基準未達時に FAIL 理由を列挙する。
    - 日付フィルタを --from / --to で指定可能。

### 変更 (Changed)
- ログの扱い
  - ルートロガーの既存ハンドラをクリアしてからハンドラを再設定することで、複数回の初期化で二重出力が発生しないようにした。

- .env 読み込みの挙動
  - OS 環境変数を保護するために .env 読み込み時の protected セットを導入。デフォルトでは OS 環境変数が上書きされない。
  - 読み込み優先度を OS 環境変数 > .env.local > .env と明確化。

### 修正 (Fixed)
- 環境変数のパース強化
  - export プレフィックスやシングル／ダブルクォート内のエスケープ、インラインコメントの扱いを堅牢化し、.env ファイル形式の互換性を改善。

- プロセス優先度設定の堅牢化
  - 未対応の OS や権限不足時に例外で停止しないようにし、警告ログを出してフォールバックするように修正。

### ドキュメント・開発補助 (Docs / Dev)
- 各 CLI スクリプトに簡単な docstring / 使用例を追加（run_monitoring, run_execution, config_setup, validate_config, paper_verification_report）。
- config_setup が生成する .env テンプレートに注意書きを追加（.env を Git にコミットしないこと）。

### 注意事項 / 既知の問題 (Known issues)
- research/factor_research.py はモメンタムなどの計算関数の実装途中（ファイル末尾で切れている）。実用には追加実装が必要。
- position_sizing の価格欠損（price が 0.0 や欠如）の場合、現在はスキップしているため、将来的にフォールバック価格（前日終値等）の導入が必要。
- apply_sector_cap は "unknown" セクターに対して上限適用を行わない仕様だが、マスタデータが不完全だと期待する制約が働かない可能性がある。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップするが、その際は stderr に警告を出力する実装になっている（挙動を運用で確認してください）。

---
この変更履歴はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実際の git log を基にした正確な CHANGELOG の生成も支援します。