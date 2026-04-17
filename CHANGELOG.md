# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。日付・バージョンはコードベースの内容（__version__ = "0.1.0" 等）から推測しています。

すべての変更は主に初回リリース相当の機能追加を表しています。実装中の注意点や既知の制約・フォールバック挙動も併記しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース相当。以下の主要機能とユーティリティを追加しました。

### 追加
- CLI・起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用 DB（デフォルト: data/paper_trading.db）と MockBroker を使用し、本番 DB と完全分離して実行。
    - 実行中の停止フラグ（data/stop_requested.flag）および pid 管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用する設計（監視 DB は一元管理）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
- 設定管理・検証・セットアップ
  - config.py: Settings クラスを追加。
    - 環境変数の読み込みとアクセス用プロパティを提供（J-Quants、kabu API、DB パス、監視閾値、環境種別など）。
    - .env 自動読み込み機能を実装（プロジェクトルートの探索: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順と既存 OS 環境変数の保護（上書き禁止）をサポート。
    - .env 内の export 形式やクォート、エスケープ、インラインコメント処理に対応するパーサを実装。
    - 環境値の検証（有効値のチェック、PAPER_FILL_MODE の検証等）を実装。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在とパース検証（PyYAML があれば内容検証）を実施。
    - --strict オプションで警告を失敗扱いにできる。
    - KABUSYS_ENV=live の場合の本番向けガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）を追加。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - よく使う設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話的に作成・更新可能。
    - 既存 .env 読み込み・マスク表示・保存機能を提供。
- ポートフォリオ構築ロジック（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選出する関数を追加。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分の算出関数を追加。スコア合計が 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を制限するフィルタ関数を追加（当日売却予定銘柄を除外可能、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を計算する関数を追加（未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 銘柄ごとの発注株数を算出する主要ロジックを追加。
      - risk_based / equal / score の配分方式をサポート。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積）を考慮。
      - 価格欠損時のスキップやログ出力、スケールダウン時の残差処理（lot 単位での追加配分）を実装。
- リサーチ・ファクター計算
  - research/factor_research.py:
    - DuckDB を用いたファクター計算モジュールを追加（prices_daily / raw_financials を参照）。
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR）、流動性（20日平均売買代金、出来高変化率）などの計算関数を実装。
    - データ不足時の None ハンドリング、計算用スキャン範囲のバッファ考慮。
- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収。psutil を用い、権限不足など失敗時は警告を出して安全にスキップ。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を出力。
    - デフォルトの DB パスは PAPER_TRADING_SQLITE_PATH / data/paper_trading.db。日付フィルタ（--from / --to）に対応。
    - 定義された閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms）を用いた判定を実装。

### 変更（設計上の決定・挙動）
- 環境変数読み込みの仕様
  - 自動 .env 読み込みはデフォルトで有効。テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書きを防止。
  - .env パーサは export 形式、クォート、バックスラッシュエスケープ、インラインコメント（クォート無しで直前が空白/タブの場合のみ）に対応。
- DB の扱い
  - 監視（run_monitoring）は実行環境にかかわらず本番用 sqlite_path を参照する設計（監視テーブルは一元管理）。
  - 実行エンジン（run_execution）は paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離。
- プロセス優先度は起動直後に high に設定する方針（可能な場合）。権限不足等で設定できない場合は警告ログでフォールバック。

### 修正・安定化（既知のフォールバック動作）
- .env パーサリングは多くのケース（シングル/ダブルクォート、エスケープ）に対応するが、複雑な構文や不正行は無視する（安全第一）。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合、自動的に等金額配分にフォールバックして WARNING ログを出す。
- calc_regime_multiplier: 未知のレジーム文字列は 1.0 にフォールバックして WARNING を出す。
- process_priority / set_cpu_affinity: OS 未対応や権限不足、psutil 非対応機能が原因で失敗した場合は警告を出して処理をスキップする。

### 既知の注意点 / TODO
- portfolio/position_sizing.calc_position_sizes:
  - price が欠損（0 や None）の場合にスキップするが、将来的には前日終値や取得原価によるフォールバックの検討が必要（コメントで TODO を記載）。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map をサポートする設計に拡張予定。
- research/factor_research:
  - DuckDB 上のテーブル（prices_daily, raw_financials）に依存。データ不足時は None を返すため、上流での欠損ハンドリングが必要。
- validate_config:
  - config/*.yaml の内容検証は PyYAML が存在する場合にのみ実施。PyYAML 未インストール時は警告となり検証はスキップされる。

### セキュリティ
- .env ファイルに機密情報（API トークン・パスワード）が含まれるため、config_setup にて .env を Git にコミットしないよう注記を出力。

---

今後のリリースでは以下の点を優先して改善予定です:
- ログレベルに応じたより詳細なログ出力や構成可能なログフォーマットの導入。
- position sizing の銘柄別 lot_size 対応、価格フォールバック戦略の実装。
- duckdb/sqlite 周りの接続プールや並列処理に関する改善。
- 単体テスト・統合テストの補強と CI 設定の追加。