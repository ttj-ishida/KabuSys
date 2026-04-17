# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠して記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今後のリリースで記載予定の変更点をここに追加します。

## [0.1.0] - 2026-04-17
初期リリース（このコードベースのスナップショットに基づく機能群と改善点）。

### Added
- コアパッケージ導入
  - kabusys パッケージ（バージョン: 0.1.0）
  - パッケージメタ情報: __version__ = "0.1.0"
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。paper_trading 環境向けに MockBroker を使い DB を分離（data/paper_trading.db）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ file による安全停止に対応。
- 設定管理
  - config.Settings: 環境変数/.env 自動ロードとプロパティベースの設定取得を実装。
    - .env/.env.local の読み込み順序制御、OS 環境変数の保護、読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）に対応。
    - .env パーサは export プレフィックス、クォート（シングル・ダブル）、エスケープ、コメント処理等に対応。
    - 各種設定プロパティ（DB パス、paper_trading 用パス、監視しきい値、環境種別判定など）を提供。
- Portfolio 構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのソート・上位選出。
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限の適用（既存ポジションからセクター露出計算、"unknown" セクターは除外対象外の挙動）。
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio.position_sizing
    - calc_position_sizes: リスクベース／等配分／スコア加重に対応した株数計算。ロット丸め、1株当たり上限、コストバッファ考慮、合計資金超過時のスケールダウンと残差処理（lot 単位での再配分）を実装。
- Research（DuckDB ベースのファクター計算・解析）
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value: prices_daily/raw_financials を用いたモメンタム・ボラティリティ・バリュー指標の算出。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算。
    - calc_ic / rank / factor_summary: IC 計算（Spearman）、ランク付け、統計サマリー。
  - research パッケージは外部ライブラリに依存せず、DuckDB SQL を主体に設計。
- AI ニュース NLP（ニュースセンチメントの OpenAI API 連携）
  - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへスコアを書き込むロジックを実装。
    - バッチサイズ制御、文字数上限・記事数上限、429/ネットワーク/5xx のリトライ設計、レスポンス検証、スコアの ±1.0 クリップ、部分更新（特定コードのみ置換）等の仕様を記述。
    - タイムウィンドウの計算（JST → UTC 変換）ユーティリティを提供。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。期間フィルタ対応（--from/--to/--db）。
- ユーティリティ
  - utils.process_priority: プラットフォーム差（Windows/POSIX）を吸収したプロセス優先度設定と CPU affinity 設定関数を提供（権限不足や未対応 OS に対してはワーニングでフォールバック）。

### Changed
- DB 周りの設計
  - 実行エンジン（run_execution）は paper_trading 環境の場合に paper_trading 用 SQLite を使用し、本番 DB と完全分離する挙動を採用。
  - 監視用（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計に統一。
- ログレベルと起動ログの改善
  - 起動時に Settings().env の値をログに出力するようにして起動環境を明確化。
- .env の自動読み込みロジックを堅牢化
  - プロジェクトルート探索を .git / pyproject.toml ベースで行い、配布後の動作を安定化。

### Fixed
- 環境変数の検証とフォールバック
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出しデフォルトにフォールバックするように修正（run_monitoring）。
- 安全なプロセス設定
  - set_process_priority / set_cpu_affinity は AccessDenied や NotImplementedError を捕捉してワーニングでスキップするようにして、権限やプラットフォーム差分での起動失敗を回避。
- スコア重み化のフォールバック
  - calc_score_weights は全スコアが 0.0 の場合に等金額配分へフォールバックし、警告を出すように修正。
- SQL / 集計の堅牢化
  - research と tools のクエリにおいて、データ不足（テーブル未存在や行不足）時に例外をハンドルして Nil 値や N/A 表示にフォールバックする実装に改善。

### Known issues / Notes
- ai/news_nlp.py はファイル末尾がスナップショットで途中切れになっている（_fetch_articles 呼び出し以降の実装断片が欠落）。現状はアーキテクチャ・設計仕様は明記されているが、実行時に未実装部分が存在する可能性あり。OpenAI 連携を有効にする際は残り実装の追加と十分なテストが必要。
- position_sizing の価格欠損時の挙動に関する注記
  - apply_sector_cap / calc_position_sizes は price_map/open_prices に欠損（0.0）がある場合に一部で過少見積りやスキップが発生する旨の TODO コメントあり。将来的に前日終値や取得原価のフォールバックを検討することを推奨。
- DuckDB executemany のパラメータ空配列に関する注意
  - ai/news_nlp の設計で executemany を呼ぶ前に params が空でないことを確認する必要がある（DuckDB 0.10 の制約に起因）。

### Removed
- なし（初期リリースのため該当なし）。

### Security
- 現状、機密情報（API キー等）は環境変数経由で管理する設計。config._require により必須変数未設定時に早期にエラーを出す仕様。ただし運用では .env の取り扱いと権限管理に注意すること。

---

注: 上記 CHANGELOG は提示されたコードベースの内容（関数名・コメント・挙動・TODO を含む）から推測して作成しています。実際のコミット履歴や意図とは差異があり得ます。必要であれば、コミットログやリポジトリ履歴に合わせて修正します。