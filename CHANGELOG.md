# Changelog

すべての重要な変更点をここに記録します。本ドキュメントは "Keep a Changelog" の形式に従います。

## [0.1.0] - 2026-04-17 (Initial release)

### Added
- 基本パッケージ情報
  - パッケージメタデータを追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）を監視し、検知でループを終了。
    - 監視は KABUSYS_ENV に関係なく本番の sqlite_path を使用する旨の挙動を明示。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して paper_trading 専用 DB（data/paper_trading.db）に記録し、本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および実行 PID ファイル（data/execution.pid）を扱う仕組みを追加。
    - エンジンをデーモンスレッドで起動し、停止フラグ検知で安全に停止。

- 設定／環境変数管理
  - config.Settings クラスを追加（settings インスタンスをエクスポート）。
    - .env 自動読み込み機能（プロジェクトルートに基づく）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env/.env.local の読み込み順序と override 挙動を実装（OS 環境変数は保護）。
    - .env パーサーは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応する堅牢な実装。
    - 必須環境変数チェック（_require）・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を追加。
    - 多数のプロパティを提供（DB パス、paper_trading 用パス、監視閾値、PID/kill flag パス、env 判定メソッド等）。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度を設定するユーティリティを追加（set_process_priority）。
    - CPU アフィニティを最初の N コアに固定する set_cpu_affinity を追加。
    - Windows / POSIX の差分を吸収し、権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合のフォールバック（等金額）に警告出力。

  - portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定コードを除外可能、"unknown" セクターは除外しない）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知レジームはフォールバックと警告）。

  - portfolio.position_sizing
    - position size（発注株数）算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、銘柄別上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer の考慮、残差処理ロジックを追加。
    - 価格欠損・ゼロ価格時のスキップやログ出力を行う。

  - portfolio パッケージのエクスポート設定を追加。

- 研究・ファクター計算
  - research.factor_research
    - Momentum / Volatility / Value ファクター計算を実装（DuckDB 接続を受け取る）。
    - momentum: 1m/3m/6m リターン、MA200 乖離の算出。過去データ不足時の None 処理。
    - volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率の算出。true_range の NULL 伝播制御。
    - value: EPS / PER、ROE の計算（raw_financials の最新レコードを target_date <= report_date で取得）。

  - research.feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズンの集約取得）。
    - IC（Spearman）計算 calc_ic（ランク相関、最小有効サンプルチェック）。
    - ランク変換ユーティリティ rank とファクター統計量 factor_summary を実装（None 除外・基本統計量提供）。
    - 標準ライブラリのみで実装、外部依存を最小化。

  - research パッケージのエクスポート設定を追加（zscore_normalize の re-export を含む）。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）へ送って銘柄別センチメントを ai_scores に保存するスコアリングモジュールを追加。
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のタイムウィンドウ計算（UTC 変換）を行う calc_news_window を実装。
    - バッチング（1 API コールあたり最大 20 銘柄）、1 銘柄当たりの最大記事数 / 文字数制限、JSON 出力厳格化、スコアの ±1.0 クリップなどの設計。
    - 429 / ネットワーク / タイムアウト / 5xx に対して指数バックオフで最大リトライを行う仕組みを想定（定数と制御ロジックを実装）。
    - API キーが未設定の場合は明確な例外を送出。
    - 書き込みは部分更新を意識（対象コードを限定して DELETE → INSERT）して部分失敗時の既存データ保護を考慮。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプトを追加（CLI エントリポイント）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計。
    - 判定閾値と Pass/Fail 判定ロジックを定義（デフォルト閾値はソース内に明記）。
    - --from / --to / --db CLI オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数でも DB 指定可能。
    - DB のテーブル欠損（OperationalError）に対するフォールバック処理を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed / Hardening
- 環境変数パーサーの堅牢化
  - .env パーサーでクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの解釈を正しく処理するように実装。
  - 数値系環境変数（例: MONITOR_POLL_INTERVAL）のパースエラー時にデフォルトへフォールバックし、警告ログを出力する実装を追加。

- プロセス優先度 / アフィニティ設定の安全性向上
  - 権限不足や未実装 API 呼び出しで例外になる場合は警告に落とし、処理継続するように変更。

- DuckDB / SQLite の利用時にテーブル欠損や OperationalError が発生した場合のフォールバックを追加（ツール側・研究側のクエリ実行で安全に N/A を返す等）。

### Notes / Migration / Usage
- .env の自動読み込み
  - デフォルトでプロジェクトルートの .env / .env.local を自動ロードします。テスト等で自動ロードしたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OS 環境変数は保護され、.env.local の override でも上書きされません。

- データベース
  - 監視(run_monitoring)は常に settings.sqlite_path（本番 monitoring DB）を使用します。paper_trading 環境でも監視 DB は本番のパスを使う点に注意してください。
  - 実行(run_execution)は paper_trading 環境時に settings.paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離します。

- 環境変数とバリデーション
  - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は未設定だと ValueError を発生させます。
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の許容値は厳密にチェックされ、不正値は例外になります。

- AI モジュール
  - OpenAI API 使用時は `OPENAI_API_KEY`（または関数引数）を必ず設定してください。未設定だと error を投げます。
  - ニュースウィンドウ計算は JST を基準にして UTC で DB クエリする仕様になっています（ルックアヘッドバイアス回避のため日付を直接参照しない実装意図）。

- 実行時のプロセス優先度
  - 起動スクリプトは初動で set_process_priority("high") を呼び出します。OS/権限によっては設定に失敗し警告が出ますが、処理自体は続行します。

### Known limitations / TODO
- position_sizing の price フォールバックは未実装（コメントで将来の拡張を示唆）。
- ai.news_nlp の実際の API 呼び出し／レスポンス処理はリトライ方針等の骨組みを含めた実装になっているが、実稼働での監視・ログ/エラー処理の強化が望まれる。
- DuckDB の executemany の制約（params が空だと失敗）を考慮した保護はコメントで言及あり。実データでの動作確認が必要。

---

このリリースは初期機能群の整備・設計方針実装を中心としたもので、監視・実行・ポートフォリオ構築・研究解析・ニュース NLP・ツール類を含みます。必要に応じて個別モジュールの API 使用例や運用上の注意点を追記します。