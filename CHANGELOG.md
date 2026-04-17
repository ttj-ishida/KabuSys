# CHANGELOG

すべての重要な変更は Keep a Changelog の方針に従って記載しています。バージョン/日付は、ソースコード内の実装状況から推測して設定しています。

## [0.1.0] - 2026-04-17

### Added
- 実行エントリープロセス
  - run_execution.py: ExecutionEngine を起動するエントリースクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用する（本番 DB と分離）。停止フラグ / PID 管理 / スレッド化された run_session サイクルを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書きが可能（デフォルト 60 秒）。停止フラグ検出や DB 初期化処理を含む。
- 設定管理
  - config.py: .env 自動ロード機能を追加（プロジェクトルート検出、.env / .env.local の読み込み順序、OS 環境変数を保護する override ロジック）。パースはクォートやエスケープ、インラインコメントに対応。多くの設定プロパティ（DB パス・PID パス・閾値など）を Settings クラスとして提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定（select_candidates）、等配分・スコア配分（calc_equal_weights / calc_score_weights）を追加。スコアが全て 0 の場合は等配分にフォールバックして警告ログを出力。
  - position_sizing: position サイズ計算（risk_based / equal / score）を実装。単元株（lot_size）、コストバッファリング、aggregate cap によるスケールダウンと残差配分ロジックを含む。
  - risk_adjustment: セクター集中上限の適用（apply_sector_cap）とマーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
- リサーチ機能（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算関数を追加。prices_daily / raw_financials テーブルに対して SQL を用いた高速集計を実装。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を追加。外部ライブラリに依存せず標準ライブラリで実装。
  - research.__init__ で主要関数をエクスポート。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して CLI 出力する。期間指定オプション（--from / --to / --db）に対応。DB が存在しない場合はわかりやすくエラーメッセージを出力。
- AI ニュース NLP（初期実装）
  - ai/news_nlp.py: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルに書き込む機能を追加（ウィンドウ計算、バッチサイズ、リトライ方針、出力バリデーション、スコアのクリッピング等の設計を含む）。API キー解決と時間窓計算ユーティリティ（calc_news_window）を実装。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。Windows / POSIX に対応し、権限不足や未対応環境時は警告ログでフォールバック。

### Changed
- 監視関連の運用方針
  - run_monitoring: Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を参照する仕様を明確化（監視データの一元化を想定）。
- .env 読み込みロジックの優先度と保護
  - config.py: OS 環境変数を保護しつつ .env/.env.local を適切に読み込む順序を採用（OS 環境変数 > .env.local > .env）。.env.local は既存値を上書きするが、OS 変数は上書きされない。
- 各種デフォルト値とバリデーション
  - Settings に PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、監視閾値（CPU/MEM/DISK）などを追加し、不正値での早期エラー検出を行うようにした。
- レポート／集計の出力表現
  - paper_verification_report: P95 計算、NA 表示ロジック、クエリの期間フィルタなどが整備され、欠損テーブルに対しても安全に動作するようになった。

### Fixed
- .env パーサの堅牢化
  - クォート文字の扱い（エスケープ、閉じクォートまでの正確な抽出）、コメントの取り扱い（クォートなしの場合の '#' をインラインコメントとして扱うルール）などの不正パースを修正。
- 数値処理／境界ケース対応
  - paper_verification_report._p95: 空リストに対して None を返すようにして例外を防止。
  - calc_score_weights: 全スコアが 0 の場合にゼロ除算を避けて等配分にフォールバックし、警告ログを出力。
  - calc_momentum / calc_volatility / calc_value: ウィンドウ内データ不足時に None を返すガードを追加し、不完全データでの誤計算を回避。
  - feature_exploration.calc_forward_returns: horizons 引数のバリデーションを導入（正の整数かつ最大 252 日まで）。
  - position_sizing: 価格欠損（None や 0）時のスキップ、lot_size 単位での丸め、aggregate cap スケーリング時の残差配分で上限を超えないよう保護する実装を追加。cost_buffer の考慮を導入。
- プロセス設定におけるフェイルセーフ
  - set_process_priority / set_cpu_affinity: アクセス権限不足や未サポート環境での例外を捕捉し、警告ログを出してスキップするように変更。
- CLI の堅牢化
  - paper_verification_report: DB が存在しない場合のメッセージと早期終了、SQL クエリがテーブル無しで失敗した場合の例外ハンドリング（OperationalError を捕捉して N/A 相当の値で継続）。

### Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で解決する設計とし、未設定時は ValueError を返して明示的に処理側で対処させるようにした（漏洩防止の観点からコード中にキーを埋め込まない方針）。

### Notes / Misc
- パッケージバージョンはパッケージヘッダで __version__ = "0.1.0" に設定。
- ai/news_nlp.py は設計方針・ウィンドウ計算・API リトライ方針などを実装済みだが、ソース末尾が一部切れている（スニペット truncation の可能性）。実運用前に完全な処理ループ（記事フェッチ→バッチ送信→DB 書込）および単体テストの追加を推奨します。

## 影響（Breaking changes）
- 既存の .env 自動ロード動作が明示的に導入されたため、従来のテスト環境などで環境変数の衝突がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化してください。
- Monitoring は常に settings.sqlite_path（本番想定）を使用する設計になっています。テスト用の監視データを分離したい場合は設定ファイル/環境変数の見直しまたはコードの変更が必要です。

---

今後の改善候補（要検討）
- ai/news_nlp の完全実装とエンドツーエンドのリトライ/部分失敗時のロールバック戦略（トランザクション的な保護や部分更新のポリシー）。
- position_sizing の銘柄別 lot_size 対応（将来的な拡張案として stocks マスタの導入）。
- DuckDB クエリのパフォーマンス監視・インデックス化、及び各集計のユニットテスト強化。