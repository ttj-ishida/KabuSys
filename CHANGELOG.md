# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本CHANGELOGはリポジトリ内のソースコード（src/ 以下）から実装内容を推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

---

## [Unreleased]

### Added
- ドキュメント化されている複数の主要コンポーネント（モニタリング、実行エンジン、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ユーティリティ等）の初期実装を追加。
  - run_monitoring: SystemMonitor をポーリングで定期実行する起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag によるフラグ検知で行う。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（data/paper_trading.db など）を使用し本番 DB と完全分離。
    - ブローカークライアントは BrokerClientFactory 経由で生成（環境により Mock/実運用を切替）。
    - 停止フラグ検知でエンジン停止、execution.pid に PID を記録する仕組みを備える。
  - config: 環境設定管理クラス Settings を実装。
    - プロジェクトルート探索（.git / pyproject.toml）に基づく .env 自動ロード（.env.local > .env、OS 環境変数優先）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - `.env` 行パーサーは export プレフィックス・クォート（エスケープ）・インラインコメントに対応。
    - 各種設定プロパティ（DB パス、PID/kill フラグパス、paper trading 用設定、監視閾値、ログレベル等）を提供。値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を実装。
  - portfolio: 銘柄選定・重み計算・リスク調整・ポジションサイズ計算の純粋関数群を追加。
    - portfolio_builder: シグナル選別 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。スコア全てが 0 の場合は等配分にフォールバックして WARN ログを出す。
    - risk_adjustment: セクター集中抑制 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier) を実装。未知レジームは警告して 1.0 でフォールバック。
    - position_sizing: risk_based / equal / score 方式による発注株数算出を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer（手数料・スリッページの保守見積り）、残差配分ロジックなどを実装。
  - research: DuckDB を用いたファクター計算・特徴量探索モジュールを追加。
    - factor_research: momentum / volatility / value ファクター計算（MA200、ATR20、平均売買代金、PER/ROE 等）。
    - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（スピアマンのランク相関）計算、ファクター統計サマリー、rank ユーティリティ等を実装。外部ライブラリに依存しない純 Python 実装。
  - tools: Paper Trading 検証レポート生成ツール (paper_verification_report) を追加。
    - 稼働率・注文成立率・送信率・P95 レイテンシ等を集計して PASS/FAIL を自動判定するレポート出力。
    - デフォルト DB パスは data/paper_trading.db。コマンドライン引数 --from/--to/--db に対応。
  - ai/news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む処理の実装（バッチ送信、バリデーション、クリップ、リトライ等）。
    - ニュース収集ウィンドウ計算（JST 基準を UTC に変換）を提供。
    - API キー解決、バッチサイズ制限、文字数・記事数のトリミング、429/5xx などのエクスポネンシャルバックオフ、レスポンス検証、部分更新（対象コードのみ DELETE→INSERT）方針を実装。
    - （注）ファイル末尾で記事集約処理が途中で途切れている（実装が未完または切り出しのため一部欠落）。
  - utils: プロセス優先度・CPU affinity 設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に差異を吸収する実装。権限不足や未実装 API に対しては警告を出してスキップするフェイルセーフ。

### Changed
- なし（初期導入・推測ベースの変更履歴のため省略）。

### Fixed
- なし（初期導入・推測ベースの変更履歴のため省略）。

### Removed
- なし。

### Security
- OpenAI API キー未設定時は明示的に ValueError を送出することで誤操作を防止（ai/news_nlp）。

---

## [0.1.0] - 2026-04-17

初期公開相当のリリース。上記 Unreleased の内容をベースに、次を含む機能をまとめてリリース。

### Added
- 基本アプリケーション情報（kabusys.__version__ = "0.1.0"）。
- モニタリング、実行エンジン、設定管理、ポートフォリオ構築、ポジションサイズ、リスク調整、リサーチ、特徴量探索、AI ニューススコアリング、運用ツール（検証レポート）、ユーティリティ（プロセス優先度）を含む包括的なモジュール群を追加。
- DuckDB / SQLite を用いたデータ処理基盤を導入。監視テーブル初期化ユーティリティを用意（init_monitoring_db を参照）。
- Paper Trading 用 DB の分離（PAPER_TRADING_SQLITE_PATH / 設定 is_paper フラグ）を実装。
- コマンドラインからの検証レポート生成機能（paper_verification_report）を追加。

### Notable implementation details / behavior
- .env 自動ロードはプロジェクトルートが特定できる場合に行われ、.env.local は .env を上書きする。OS 環境変数は保護される（既存環境変数は優先）。
- Settings のプロパティは未設定時に例外を投げるものとデフォルトを持つものが混在。環境変数値の検証を行う（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL など）。
- モニタリングは環境にかかわらず本番 sqlite_path を参照する挙動（モニタが監視対象を常に本番 DB に対して行う設計）。一方、Execution は paper_trading 環境時に DB を分離。
- position_sizing のスケーリング・残差処理は単元株（lot_size）に沿って厳密に丸める設計。aggregate cap 超過時にスケールダウンして残余キャッシュで端数調整を行う。
- research モジュールはホライズン／ウィンドウのカレンダー日バッファを設け、実用上のデータ不足や休日を吸収するように設計されている。
- ai/news_nlp モジュールは実装が進んでいるが、ソース切り出しの関係で一部（記事集約以降）のコード断片が欠落している。API 呼び出しのリトライ・バッチ化・出力検証方針は明文化されている。

### Known issues / TODOs（ソース内コメントより推測）
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小評価される可能性があり、将来的に前日終値や取得原価をフォールバックする検討が必要。
- position_sizing:
  - 将来的に銘柄ごとの lot_size をサポートするための拡張（lot_map）を検討中（現状は全銘柄共通 lot_size）。
- ai/news_nlp:
  - ファイル末尾が途切れており、記事集約・API 呼び出し以降の処理が未確認。部分的に未実装または切り出しミスの可能性あり。
- utils.set_cpu_affinity:
  - cpu_count が利用可能コア数を超える場合の挙動はログで説明しているが、より明示的なハンドリングや単体テストが欲しい。

---

注: 実装の詳細（引数仕様・デフォルト値・ログメッセージ等）はソースコメントや docstring を基に記載しています。実際の動作確認やユニットテスト結果に基づく修正は別途必要です。