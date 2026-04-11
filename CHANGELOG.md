# Keep a Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記述します。  
フォーマット: 変更の種類ごとに箇条書き。影響の大きい挙動変更は Breaking change として明記します。

## [Unreleased]
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-11

### Added
- 全体
  - パッケージ初期リリース。バージョンは `kabusys.__version__ = "0.1.0"`。
  - DuckDB と SQLite を併用するデータ基盤を導入。多くの研究・AI・監視処理で DuckDB 接続を受け取る設計。

- 実行 / 監視
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視はプロセス優先度を "high" に設定して起動する。
    - 監視開始時に monitoring DB の初期化（`init_monitoring_db`）を行う。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は専用の MockBroker 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する。
    - プロセス優先度を "high" に設定して起動する。
    - ExecutionEngine の開始処理（Broker Factory、OrderManager、RiskManager、Reconciler、OrderRepository の組み立て）を実装。
    - RiskConfig の初期値と `initial_portfolio_value` をブローカーから取得して設定。

- 設定（config）
  - `Settings` クラスを導入し、環境変数のアクセスとバリデーションを統一。
  - 自動 .env 読み込み機能を追加（プロジェクトルートを `.git` または `pyproject.toml` で探索）。
    - 読み込み順序: OS 環境 > .env.local > .env（OS 環境のキーは上書きされない）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
  - .env パーサを強化: `export KEY=val`、クォート値（エスケープ処理含む）、インラインコメント処理などに対応。
  - 各種プロパティを実装（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, kill flag 関連、閾値設定、`env` バリデーション など）。
  - `PAPER_FILL_MODE` のバリデーション（allowed: instant, partial, never, reject）。

- ポートフォリオ構築（portfolio）
  - 銘柄選定と重み計算モジュール（portfolio_builder）を実装。
    - `select_candidates`, `calc_equal_weights`, `calc_score_weights` を実装。スコアが全て 0 の場合は等金額配分にフォールバック（警告ログ）。
  - リスク調整（risk_adjustment）
    - `apply_sector_cap`: セクター集中制限に基づき候補を除外するロジックを実装（売却予定銘柄の除外などに対応、"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier`: 市場レジームに応じた資金乗数（bull/neutral/bear）を実装（未知レジームは 1.0 でフォールバック）。
  - 株数計算（position_sizing）
    - `calc_position_sizes`: risk-based / equal / score の各 allocation method に対応。単元株（lot_size）で丸め、per-stock / aggregate cap、コストバッファ考慮のスケーリングアルゴリズムを実装。

- リサーチ（research）
  - ファクター計算（factor_research）
    - `calc_momentum`, `calc_volatility`, `calc_value` を実装。DuckDB 上の `prices_daily` / `raw_financials` を参照して計算。
  - 特徴量探索（feature_exploration）
    - `calc_forward_returns`: 任意ホライズンの将来リターンを一括取得する SQL 実装。horizons のバリデーションあり。
    - `calc_ic`: スピアマンランク相関に基づく IC 計算（ランク算出の tie 処理あり）。
    - `factor_summary`, `rank` など統計ユーティリティを提供。
  - すべて標準ライブラリと DuckDB のみで実装（pandas など外部依存を避ける設計）。

- AI（ai）
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを付与して `ai_scores` に書き込む処理を実装。
    - バッチサイズ上限（20 銘柄/回）、1 銘柄あたり文字数・記事数の上限などトークン肥大化対策を実装。
    - API 呼び出しはリトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで行い、JSON パースやレスポンスバリデーション（構造・型・既知コード・スコアの数値化）を徹底。
    - スコアは ±1.0 にクリップ。DuckDB への書き込みは部分失敗時の既存データ保護のため、対象コードのみ DELETE → INSERT（トランザクション）する。
    - OpenAI クライアントの呼び出しは `_call_openai_api` を抽象化しており、テスト時に差し替え可能。
  - レジーム判定（regime_detector）
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジーム ('bull'/'neutral'/'bear') を日次判定し `market_regime` テーブルへ冪等的に書き込む処理を実装。
    - マクロキーワードリストにより raw_news からタイトルを抽出し、OpenAI で macro_sentiment を算出（失敗時は 0.0 を採用してフェイルセーフ）。
    - LLM 呼び出し失敗時でも処理継続する耐障害性設計。

- ユーティリティ（utils）
  - process_priority: プラットフォーム差を吸収するプロセス優先度ユーティリティを追加。
    - `set_process_priority(level: "high"|"normal"|"low")` を実装（Windows と POSIX に対応、未対応 OS はスキップ）。失敗時は警告ログでスキップ。
    - `set_cpu_affinity(cpu_count: int | None)` によりプロセスを最初の N コアにピン留め可能。無効値や権限不足は警告で処理。

### Changed
- 環境ロード優先度の明確化と挙動
  - 自動 .env ロードを行う際の探索ルールを明確化（プロジェクトルート探索、`.env.local` の上書き）。
  - OS 環境変数はデフォルトで保護され、.env による上書きを防止。

- DB の取り扱い
  - 監視（run_monitoring）は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用する（意図的な設計）。※本番監視は常に本番 DB を見る想定。
  - 実行（run_execution）は paper_trading 環境のときのみ paper_sqlite_path を使用し、本番 DB と分離するよう変更。

- 安全性 / バイアス回避
  - AI / レジーム処理、ニュース処理、研究処理はいずれも `date` / `target_date` を受け取り、内部で `date.today()` / `datetime.today()` を参照しない設計に統一（ルックアヘッドバイアス防止）。

### Fixed
- ポートフォリオ/ウェイト計算
  - `calc_score_weights` が全銘柄スコア合計 0 の場合に等金額配分にフォールバックする挙動を追加（警告ログ出力）。これにより除算エラーや NaN を回避。
- ランク計算
  - `rank` 関数で丸め（round(v, 12)）を行い、浮動小数点の丸め誤差による ties 検出漏れを防止。
- forward returns
  - `calc_forward_returns` で horizons の入力検証を追加（正の整数かつ <=252）。
- OpenAI 呼び出しの堅牢化
  - JSON mode によるレスポンスでも前後余計なテキストが混入するケースに対して最外の {} を抜き出すリカバリ処理を追加。
  - レスポンスの検証とスコアのクリッピングを実装して不正データを無害化。
- 監視ループ
  - `run_monitoring.main` 内のポーリングループで `monitor.check_once()` が例外を投げてもログを出して次回ポーリングへ継続するように変更（監視の健全性向上）。

### Security
- OpenAI API キーの取り扱い
  - `score_news` / regime_detector 等は引数から API キーを受け取れ、引数未指定時は環境変数 `OPENAI_API_KEY` を参照。未設定時は明示的にエラーを投げる（事故で無効な呼び出しが行われないようにする）。
- DB 書き込み
  - ai_scores の更新はトランザクションで行い、部分失敗時に既存スコアを不必要に消去しないよう配慮。

### Breaking Changes
- 監視 DB の使用方法が明示的に変更されました:
  - run_monitoring は KABUSYS_ENV に関係なく `Settings.sqlite_path`（本番 monitoring.db）を使用します。以前のバージョンで環境に応じて別 DB を使っていた運用がある場合、監視対象 DB の分離が期待通りでない可能性があります。運用上の分離が必要な場合は run_monitoring の起動スクリプト・設定を見直してください。
- Settings の環境値検証強化:
  - `KABUSYS_ENV`, `PAPER_FILL_MODE`, `LOG_LEVEL` 等に対するバリデーションが追加され、誤った値は ValueError を投げます。既存のデプロイで非標準の値を使っている場合は設定を修正する必要があります。

### Notes / Implementation details
- DuckDB を使った複雑な SQL（ウィンドウ関数・LEAD/LAG/AVG OVER 等）を多用しており、prices_daily / raw_financials 等のテーブルスキーマに依存する設計です。データ整備（欠損・行数）に注意してください（例: MA200 のデータ不足時は中立にフォールバック）。
- position_sizing のスケーリングは lot_size（現状デフォルト 100）単位で丸めるため、少額の銘柄では発注量が 0 になる可能性があります。
- OpenAI とのやり取りは外部サービスとの相互作用を含むため、ネットワーク・レート制限による部分失敗を想定した設計となっています。テスト時は `_call_openai_api` をモックしてください。

---

（補足）本 CHANGELOG はソースコードからの推測に基づく記述です。実際のリリースノートや運用ドキュメントと差異がある場合は、該当箇所の実装・運用方針に合わせて適宜修正してください。