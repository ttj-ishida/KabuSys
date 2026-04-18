# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。語彙・表現はコードベース（src/ 以下）の実装から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初期リリース。以下の主要な機能・CLI・ユーティリティ・ライブラリ群を追加しました。

### 追加 (Added)
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用するよう分離。
    - デーモン化されたスレッドで engine.run_session を実行し、data/stop_requested.flag による外部停止に対応。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - data/stop_requested.flag による停止フラグ検知と KeyboardInterrupt ハンドリングを実装。

- 設定関連 CLI / ユーティリティ
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。
    - J-Quants、kabuAPI、DB パス、ログレベル等の主要項目を対話的に入力・確認し .env を生成。
    - secret 項目はマスク表示。保存前に確認プロンプトあり。
  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML 存在時）パース検証を行う。
    - --strict オプションで警告を失敗扱いにできる。

- 設定管理
  - config.py: Settings クラスを実装。
    - .env 自動読み込み機能を実装（.env → .env.local の順、OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - 各種環境変数のラッパー（duckdb/sqlite パス、KABUSYS_ENV 判定、PAPER_FILL_MODE の妥当性チェック等）を提供。
    - settings = Settings() をモジュールレベルで公開。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選択（同点時のタイブレークにも対応）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等配分へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を適用し、上限を超えるセクターの新規候補を除外。
      - 当日売却予定銘柄をエクスポージャー計算から除外するオプション対応。
      - "unknown" セクターは上限適用対象外とする設計。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。
      - リスクベースの計算（risk_pct, stop_loss_pct）をサポート。
      - 1銘柄上限、aggregate cap（available_cash）を考慮し、lot_size（単元株）で丸める。
      - cost_buffer を使った保守的なコスト見積り、投資合計が予算超過時のスケーリングと余剰配分ロジックを実装。
      - 将来的な拡張（銘柄別 lot_size 等）についての TODO コメントあり。

- 解析・研究機能
  - research/factor_research.py（ファクター計算の骨格を追加）
    - Momentum 等のファクター（1M/3M/6M リターン、MA200 乖離率等）計算のインタフェースと定数を実装。
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して計算する方針を定義。
    - （ファイル末尾に未完成箇所が見られ、実装途中の状態であることが推測されます）

- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 指定期間のシステム稼働率、注文成功率（fill / send）、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - デフォルト DB パスは data/paper_trading.db。コマンドライン引数 --from/--to/--db をサポート。
    - PASS/FAIL の閾値を定義（稼働率 >= 99%、fill >=90% 等）。

- ユーティリティ
  - utils/logging_setup.py: 統一的なログ初期化関数を追加。
    - stdout（StreamHandler）出力と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに追加。
    - ログディレクトリを自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数に基づく解決を実装。
  - utils/process_priority.py: psutil を用いたプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して API を提供。
    - set_process_priority("high"|"normal"|"low"), set_cpu_affinity(N) を提供。
    - 許可不足や未対応 OS の際は警告を出して安全にスキップ。

- パッケージ管理
  - パッケージのメタ情報として __version__ = "0.1.0" を追加。

### 変更 (Changed)
- 監視と実行の挙動設計
  - run_monitoring と run_execution はともに起動時にプロセス優先度を "high" に設定するように統一。
  - run_monitoring は監視用 DB 初期化（init_monitoring_db）を行い、duckdb も接続する構成に変更 / 実装。
  - run_execution は paper_trading モード時に専用 SQLite を用いることで本番 DB と分離する実装を採用。

- 環境変数の読み込みルール
  - 自動 .env 読み込みの優先順位を OS 環境 > .env.local > .env に定義。OS 環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みオフのメカニズムを追加。

### 修正 (Fixed)
- ロギングの二重設定防止
  - setup_logging にて既存ハンドラを flush/close してから削除することで、複数回呼び出し時のハンドラ重複を防止。

- ポジションサイズ算出時のスケールダウン精度改善
  - aggregate cap 超過時のスケーリング後、lot_size 単位で余剰キャッシュを残差に基づいて再配分するロジックを追加（順序安定性にも配慮）。

### 既知の問題 / TODO
- research/factor_research.py はファイル末尾が途中で切れているように見え、モメンタム計算のクエリ構築部分が未完です（実装途中の可能性あり）。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（price=0.0）があるとエクスポージャーが過少見積りされ、適切にブロックできない可能性がある旨の TODO コメントあり。
  - 将来的に前日終値や取得原価でのフォールバックを検討する旨のメモが残されています。
- logging_setup: ログディレクトリの作成に失敗した場合はファイルロギングをスキップするが、その際の復旧戦略は未実装。
- process_priority の優先度設定は権限不足（psutil.AccessDenied）や未実装 API の場合に警告でスキップする仕様。環境によっては期待どおり優先度が設定されないことがある。

### ドキュメント / 開発者向け注意
- validate_config では PyYAML がインストールされていない場合 config/*.yaml の内容検証をスキップするため、YAML の妥当性検証を有効にするには PyYAML をインストールしてください。
- PAPER_FILL_MODE は許容値が限定されており（"instant","partial","never","reject"）、不正な値を設定すると Settings.paper_fill_mode が ValueError を投げます。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要があります。その他の値は Settings.env や validate_config によって拒否されます。
- .env はセキュリティ上 Git にコミットしないでください（config_setup で注意喚起あり）。

### セキュリティ (Security)
- 本リリースでは特にセキュリティ脆弱性の修正は明示されていません。機密情報（API トークン等）は .env に格納する設計であり、取り扱いに注意してください。

---

参考: 実装に基づく主要コマンド例
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

（以上）