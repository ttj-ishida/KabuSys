# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-19

初回リリース。

### 追加 (Added)
- 起動スクリプト / ランナー
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てとエンジン起動処理を実装。
    - 停止フラグ (data/stop_requested.flag) と実行中 PID ファイル (data/execution.pid) による開始/停止管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを管理。

- 設定・環境管理
  - config.py
    - 環境変数ラッパー Settings を導入。J-Quants / kabu API / DB パス /ログレベル /各種しきい値等をプロパティとして提供。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env/.env.local の自動読み込み機能を追加。OS 環境変数を保護する仕組みあり（上書き制御）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等の設定を実装。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装（選択肢、シークレットマスク表示、既存値の再利用など）。
  - validate_config.py
    - 起動前に .env および config/*.yaml の整合性や存在を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パーサが利用可能なら YAML の構文チェック、KABUSYS_ENV=live の追加ガード等を実装。
    - --strict オプションで警告を失敗扱いにする機能。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルをスコア降順で選択（タイブレークルールあり）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア比率配分（スコアが全て 0 の場合は等分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームはフォールバックして 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot_size）丸め、per-position 上限・aggregate cap（利用可能現金）でのスケーリング、cost_buffer を考慮した保守的見積り等を実装。

- ユーティリティ
  - utils.logging_setup
    - ルートロガーの初期化ユーティリティ。stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app>.log）を統一設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力で継続する堅牢性を持つ。
    - ログレベル / ログディレクトリ解決順を明示。
  - utils.process_priority
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（既定: data/paper_trading.db）を解析し、稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計してレポート出力する CLI。
    - --from / --to / --db オプションをサポート。
    - PASS/FAIL 判定用の閾値（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms など）を定義。
  - research.factor_research
    - DuckDB 接続を受け取り、モメンタム / Value / Volatility / Liquidity 等のファクターを (date, code) 単位で計算するためのモジュール（Momentum 計算の骨子を含む）。
    - DuckDB 上の prices_daily / raw_financials テーブル参照設計。

- パッケージ
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

### 変更 (Changed)
- ログ出力の挙動
  - logging_setup にて stdout に出力するよう明示（cron 等の実行環境でのログリダイレクトを想定）。

### 修正 (Fixed)
- 起動時の堅牢性向上
  - .env 読み込みでファイル読み込み失敗時に警告を発し、プロセスを継続するように変更。
  - process_priority / set_cpu_affinity は権限不足や未サポート環境でも例外を投げず警告でスキップするように改善。
  - run_monitoring のポーリングループで check_once() の例外をキャッチしてログに記録し、ループを継続することで監視の自己修復性を向上。
  - run_execution, run_monitoring で DB 接続を finally で閉じるようにしてリソースリークを防止。

### ドキュメント (Documentation)
- 各スクリプト・モジュールに docstring / 使用例を追加。特に設定ウィザード、validate_config、logging_setup、process_priority、portfolio モジュールなどで挙動や引数の説明を充実。

### 注意事項 / 既知の制約 (Notes / Known issues)
- apply_sector_cap の価格が欠損（0.0）の場合の扱いについて TODO コメントあり。将来的に前日終値や取得原価でフォールバックする予定。
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_map に拡張予定）。
- research.factor_research の実装は続きがあり、一部（calc_momentum の実装途中など）未完の箇所が存在する。
- monitoring は環境にかかわらず「本番 sqlite_path」を使用する設計（監視データを本番用に一元管理する意図）。paper_trading の実行エンジンは paper 用 DB を使用して本番 DB と分離している点に留意。

### セキュリティ (Security)
- .env は絶対にリポジトリにコミットしない旨を config_setup のヘッダに明記。

---

今後のリリースでは以下を想定しています（未実装・改善予定）:
- research.factor_research の完全実装とテストカバレッジ拡張
- 銘柄別単元（lot_size）サポート、価格フォールバックロジックの追加
- エンドツーエンドの統合テスト（paper_trading と monitoring の相互検証）
- ドキュメント（README、運用手順書）の充実

（以上）