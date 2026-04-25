# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

次のバージョン順に新しいものが上に来ます。

## [Unreleased]

### 追加予定 / 予定されている改善
- position_sizing:
  - 将来的に銘柄ごとの単元株（lot_size）を stocks マスタから取得する設計への拡張を予定（現状は全銘柄共通の lot_size を使用）。（ソース内に TODO コメントあり）
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価など）を導入して、エクスポージャー推定の過少見積もりを改善する予定（TODOコメント）。
- research.factor_research:
  - モジュールは設計方針と定数が定義されているが、実装が途中で終わっている箇所があり（ファイル末尾が途中で切れている）、完全実装およびテストを予定。
- ロギング / ファイル出力:
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合のフォールバックは既にあるが、さらに詳細なリカバリや監視アラートを追加する計画。
- その他:
  - 各コンポーネントのエラーハンドリングや単体テストの拡充、CLI ユーザビリティ向上を継続的に行う予定。

---

## [0.1.0] - 初回リリース

リリース日: 2026-04-XX（コードベースから推定）

注: パッケージの __version__ は "0.1.0"。

### 追加（新機能）
- エントリポイント / 実行スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境に応じて Paper Trading 用の専用 DB を使用（KABUSYS_ENV=paper_trading の場合は data/paper_trading.db）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - 停止フラグ（data/stop_requested.flag）や pid ファイル（data/execution.pid）で制御。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きに対応（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を「high」に設定し、停止フラグでループを終了する仕組みを実装。
- 設定管理
  - config.Settings: 環境変数読み込みと便利なプロパティ集を追加。
    - 自動 .env 読み込み（プロジェクトルートに基づき .env / .env.local を読み込み、OS 環境変数は保護）。
    - 必須/任意の設定項目、パス関連（duckdb/sqlite/paper_sqlite など）、paper_trading の fill mode 検証、ログレベル、環境（development/paper_trading/live）判定等を提供。
- 設定ツール / 検証
  - config_setup CLI: 対話式ウィザードで .env を生成・更新するツールを追加。
    - 秘匿項目はマスク表示し、既存 .env の読み込み・Enter で既存値再利用可能。
    - .env の保存テンプレートを標準化。
  - validate_config CLI: .env および config/*.yaml の基本的な整合性チェックツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・（PyYAML があれば）パース検証を実施。
    - --strict モードで警告を失敗扱いにできる。
- ユーティリティ
  - utils.logging_setup.setup_logging: ルートロガーに対して StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler を設定するユーティリティを追加。
    - ログレベル / ログディレクトリの優先順位と、既存ハンドラのクリア処理を実装。
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX を透過的に扱い、プロセス優先度（high/normal/low）を設定。
    - set_cpu_affinity(cpu_count): プロセスの CPU affinity を設定（実行環境依存で安全にフォールバック）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: signal スコアでソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を抑制するため、既存ポジションのセクター比率に応じて新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注株数を計算。
      - risk_based: リスク許容率とストップロスでポジションサイズを算出。
      - equal/score: 各銘柄重みから単位株数を計算。
      - 単元株（lot_size）で丸め、1銘柄上限や aggregate cap（available_cash）超過時のスケーリングを実装。残余キャッシュを用いた再配分（fractional remainder に基づく）ロジックを実装。
      - cost_buffer による手数料・スリッページの保守的見積りをサポート。
- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を解析して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数 等。
    - 判定基準（しきい値）を定義し、PASS/FAIL を判定（デフォルト: uptime >= 99%、fill >= 90%、send >= 95%、P95 latency <= 200 ms）。
    - 日付フィルタ (--from / --to) とデータ存在チェックに対応。
- 監視データベース用初期化
  - monitoring.monitoring_db.init_monitoring_db が各起動時に呼ばれ、監視用テーブルの存在を保証（冪等）。
- DuckDB / SQLite の併用を前提とした設計
  - duckdb は分析用（prices_daily 等）・sqlite は監視・履歴用に使い分ける構成を反映。

### 変更（設計上の明示）
- .env 自動読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local を自動読み込み。ただし OS 環境変数は保護される設計（既存 OS 環境変数を上書きしない）。
- ログ出力先は stdout を基本とし、ファイル出力は logs/<app_name>.log に日次ローテーションで保存（ログディレクトリ作成に失敗した場合はコンソールのみ継続）。

### 修正（バグ修正）
- なし（初回リリース相当）。ただし各モジュールに堅牢なエラーハンドリング（例: DB 操作・ファイル作成失敗時のフォールバック）が実装されている。

### 既知の制限 / 注意点
- research.factor_research は設計方針と定数が定義されているが、実装が途中で終わっている箇所があり（ファイルが途中で切れている）、完全な実行には未実装部分の補完が必要。
- position_sizing と apply_sector_cap は価格データが欠損している場合に conservative（0.0）扱いになる箇所があり、これによりブロックやスキップが発生する可能性がある（将来的にフォールバック価格を導入予定）。
- run_monitoring は Monitoring 用 DB として settings.sqlite_path（本番）を常に使用する設計のため、開発環境では意図せず本番 DB を参照しないよう注意が必要（config の env 設定で運用方針を管理）。

---

開発チームへのメモ:
- 単体テスト・統合テストの整備、特に position sizing のスケーリングロジックや paper_verification_report の境界ケース（データ欠損・0件）を重点的に追加することを推奨します。
- research モジュールの完成と、DuckDB テーブル構造（prices_daily / raw_financials）に対するスキーマとサンプルデータ提供を推奨します。