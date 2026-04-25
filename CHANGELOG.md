# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載します。  
このファイルは主にコードベースから推測して作成した初期リリースの変更履歴です。

全般的なバージョニング規則: SemVer 準拠を想定。

## [Unreleased]

- （現時点のワークツリーに未リリースの変更はありません）

## [0.1.0] - 2026-04-25

初期リリース — KabuSys 基盤機能の実装。

### Added
- 基本パッケージとバージョン情報
  - パッケージ初期化およびバージョン定義を追加（__version__ = "0.1.0"）。

- 設定管理
  - Settings クラスによる環境変数ラップを実装（kabusys.config）。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local を読み込む）。
  - .env 解析の堅牢化:
    - export プレフィックス対応、クォート文字列のエスケープ処理、インラインコメント処理等をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。

- 設定作成支援 CLI
  - 対話式ウィザードによる .env 作成 / 更新ツールを追加（kabusys.config_setup）。
  - デフォルト値・選択肢・シークレット扱いの入力表示などをサポート。
  - .env を安全に書き出すテンプレートと説明を実装。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml を検証するツールを追加（kabusys.validate_config）。
  - 必須環境変数チェック、KABUSYS_ENV および LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 利用）などを実装。
  - --strict オプションで警告を fail 扱いにできる。

- 起動スクリプト
  - ExecutionEngine 起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading 時は paper trading 用 SQLite に接続し MockBroker を利用（本番 DB と分離）。
    - プロセス優先度設定、高優先度で起動、PID ファイル管理、停止フラグ（data/stop_requested.flag）対応を実装。
    - コンポーネント組み立て: BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の起動ルーチンを組み込み。
  - SystemMonitor 起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用して接続（監視データの一元化）。
    - 停止フラグ、エラー時の例外ログ出力、KeyboardInterrupt での優雅な終了処理を実装。

- ロギング基盤ユーティリティ
  - setup_logging 関数を実装（kabusys.utils.logging_setup）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップして console のみで継続。
    - 既存ハンドラを一旦閉じて再設定することで二重出力を防止。

- プロセス優先度・CPU affinity ユーティリティ
  - set_process_priority, set_cpu_affinity を実装（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収。
    - 権限不足や未サポート環境でも警告ログを出して安全にスキップする実装。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates（スコア降順・タイブレーク処理）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化、全スコア 0 の場合は警告して等比率へフォールバック）
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap（セクター集中制限に基づき候補を除外）
      - 売却予定銘柄をエクスポージャー計算から除外する機能をサポート
      - "unknown" セクターは上限適用除外
      - price 欠損時の注記（将来的なフォールバックの TODO を明記）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数: bull/neutral/bear）
      - 未知レジームは警告して 1.0 にフォールバック
  - 位置サイズ計算（kabusys.portfolio.position_sizing）
    - calc_position_sizes 実装
      - allocation_method: "risk_based" / "equal" / "score" をサポート
      - lot_size 単位での丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン
      - cost_buffer を考慮した保守的コスト見積りと残差（fraction）に基づく追加配分ロジック
      - 価格未取得銘柄のスキップ・ログ出力

- 取引検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ（--from / --to）、DB パスオーバーライド（--db）対応。
    - P95 計算、データ不足時のハンドリング、閾値はスクリプト内定義で一元管理。

- リサーチ / ファクター計算（骨格）
  - factor_research モジュール追加（kabusys.research.factor_research）。
    - モメンタム、MA、ATR 等の計算方針と定数を定義（DuckDB 接続を想定）。
    - 実装はファイル末尾で途中まで（将来的なファクター計算の拡張を想定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- apply_sector_cap の価格欠損時の扱いについて TODO コメントあり（前日終値や取得原価等のフォールバックを検討）。
- process_priority の設定は権限不足やプラットフォーム差分で失敗する可能性があるが、安全にスキップする実装となっている。
- factor_research の一部実装が未完（ファクター計算の続き実装が必要）。
- .env ファイルは絶対にリポジトリにコミットしないこと（config_setup の出力にもその旨を明記）。

### Security
- 機密値（API トークン・パスワード）は .env に保存する設計。config_setup はシークレット入力をマスクするが、運用時は `.env` を安全に管理すること。

---

（この CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴や差分に基づくものではありません。必要に応じて日付や項目を調整してください。）