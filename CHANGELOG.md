CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
以下は提示されたコードベースの内容から推測して作成したリリース履歴です。実際のコミット履歴ではなく、ソースコードから読み取れる機能追加・設計意図・既知の制約を元にまとめています。

フォーマット:
- Unreleased: 今後の追加予定や注意点（コード内の TODO や未完部分に基づく推測）
- 各リリースは [バージョン] - 日付 の形で記載

Unreleased
----------
- factor_research.calc_momentum の実装が途中で終わっている（ファイル末尾が切れているため、計算ロジックの完了およびテストの追加が必要）。
- position_sizing や risk_adjustment にある TODO（銘柄ごとの lot_size 拡張、価格欠損時のフォールバックロジックなど）の対応。
- ログ出力周り・ファイルハンドラ作成失敗時の挙動やエラーハンドリングの追加強化。
- 追加ユニットテスト・統合テスト（DB 接続/duckdb クエリ/外部ライブラリ依存箇所のモック化）。
- ドキュメント補完（PortfolioConstruction.md / StrategyModel.md など参照文書のリンク整備）。

[0.1.0] - 2026-04-19
-------------------

Added
- 全体
  - パッケージ初期版として多数のサブモジュールを導入。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 起動スクリプト / ランタイム
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のバックグラウンド実行（スレッド）を実装。
    - 停止フラグ（data/stop_requested.flag）と pid ファイル（data/execution.pid）による制御を導入。
  - run_monitoring.py: SystemMonitor を定期ポーリングする監視プロセス用スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視用 DB 初期化も実行）。
    - 停止フラグによる優雅な終了と KeyboardInterrupt のハンドリング。

- 設定関連
  - config.py:
    - .env 自動読み込み機能を導入（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env の読み込み順序: OS 環境 > .env.local > .env。OS 環境は保護され上書きされない。
    - .env 行パーサを実装（export 形式、クォート値・エスケープ、インラインコメント処理など対応）。
    - Settings クラスを導入し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定などをプロパティで安全に取得。
    - KABUSYS_ENV, LOG_LEVEL 等のバリデーションを実装（許容値チェック）。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット入力マスク、選択肢提示、既存値の再利用、保存前確認などの操作性を用意。
  - validate_config.py: 起動前に設定の妥当性を検査するツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード等。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を定義し、既存ハンドラの再初期化（重複防止）を行う。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続する安全策を実装。
  - utils/process_priority.py:
    - psutil を使ったプロセス優先度設定 (high/normal/low) を OS に依らず呼べるユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を考慮した実装。CPU affinity 設定ユーティリティも実装。
    - アクセス権限や未サポート環境の際は警告を出してスキップする。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選出。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア全 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を適用して新規候補を除外するロジックを実装（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を計算。
    - 単元株丸め（lot_size）、1 銘柄上限・集合上限（aggregate cap）や cost_buffer による保守的見積り、スケーリングと端数分配のロジックを備える。

- データベース / 分析
  - DuckDB と SQLite を併用する設計を導入（duckdb_path / sqlite_path の Settings 管理）。
  - 監視用 DB 初期化ユーティリティ init_monitoring_db の呼び出しを各プロセスで行い、監視テーブル存在の冪等保証。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の SQLite データベースから複数指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ: avg/max/P95）を集計し、PASS/FAIL 判定を行う CLI。
    - P95 算出、期間フィルタのサポート、閾値（稼働率 99% など）をデフォルトで定義。

- リサーチ
  - research/factor_research.py:
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算方針と定数を定義。calc_momentum の骨組みを実装（ただしソースの末尾が欠落している箇所あり）。

Changed
- .env 読み込み仕様の改善:
  - export 付き行、クォート、インラインコメントを意識した堅牢なパースを実装。
  - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能に変更。
  - OS 環境変数を保護する protected パラメータを導入し、意図しない上書きを防止。

Fixed
- （初版のため過去の修正履歴はコードからは特定できません。実装上の安全策としてファイルハンドラ作成失敗時のフォールバック処理や例外ハンドリングを多数導入。）

Known issues / Notes
- research.calc_momentum の実装が途中で終わっている（ファイル末尾切れ）。計算ロジックとテストの追記が必要。
- position_sizing と risk_adjustment にコメント化された TODO が残る:
  - 価格 (price) が欠損した場合のフォールバック（前日終値や取得原価の利用等）が未実装で、これが無いとエクスポージャーや配分が過少/過大見積りされ得る。
  - 将来的な拡張として銘柄別 lot_size を導入する想定あり。
- 外部依存:
  - psutil, duckdb, （オプションで）PyYAML が必要。PyYAML 未導入時は config/*.yaml の内容検証がスキップされる（validate_config 参照）。
- 実行時の DB / ファイルパスは環境変数で上書き可能。初期状態で親ディレクトリが存在しない場合は警告が出るが、起動時に自動作成される箇所がある。

その他
- ドキュメント参照:
  - ソース内に PortfolioConstruction.md、StrategyModel.md 等への言及があるが、これらのドキュメント自体は今回のコード一覧に含まれていないため、実際の設計仕様はそちらを参照する想定。
- 今後の推奨作業:
  - calc_momentum の完成と検証、価格フォールバック実装、各種ユニットテスト・CI の整備、運用手順書（デプロイ/監視/バックアップ）作成。

--- 
（注）上記は提供いただいたソースコードの解析に基づく推測的な CHANGELOG です。実際のコミットメッセージやリリースノートがある場合はそれに従って調整してください。必要であれば、各項目をより詳細な変更単位（コミット単位）に分解して記載することも可能です。