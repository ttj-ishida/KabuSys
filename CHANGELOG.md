# Changelog

すべての変更は Keep a Changelog のガイドラインに従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお以下はコードベースの内容から推測して作成した初期リリース／変更履歴です。

## [Unreleased]

### Added
- なし（次回リリースまで保留）

---

## [0.1.0] - 2026-04-09

初期公開リリース。自動売買システム「KabuSys」のコアライブラリを提供。

### Added
- パッケージ基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - public API エクスポートに主要サブパッケージ（data, strategy, execution, monitoring）を設定。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local ファイルまたは OS 環境変数から設定値を自動読み込み。  
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に __file__ を起点に探索（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理等に対応。
  - OS 環境変数を保護するため既存の環境変数はデフォルトで上書きされない（.env.local は override=True）。
  - 必須環境変数取得ヘルパー `_require()`（未設定時は ValueError を送出）。
  - 設定オブジェクト `Settings` を提供し、各種設定値をプロパティとして取得可能:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルトあり）
    - LINE: `line_channel_access_token`, `line_user_id`
    - DB パス: `duckdb_path`, `sqlite_path`
    - Paper Trading 用: `paper_fill_mode`（バリデーション付き）、`paper_sqlite_path`
    - 監視関連: `pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`
    - システム: `env`（development/paper_trading/live のバリデーション）、`log_level`（ログレベルのバリデーション）、`is_live`/`is_paper`/`is_dev` の便易プロパティ

- ポートフォリオ構築ロジック（kabusys.portfolio）
  - 候補選定（portfolio_builder）
    - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を抽出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし WARN ログ）。
  - リスク調整（risk_adjustment）
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、1セクター上限を超える場合は同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし WARN ログを出力。
  - ポジションサイズ計算（position_sizing）
    - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score をサポート）。
    - リスクベース: 許容リスク率・損切り率から基本株数算出、単元（lot_size）丸め。
    - equal/score: ウェイトに基づく割当て、per-position 上限・aggregate cap を考慮。
    - 手数料・スリッページを考慮する cost_buffer、合計コストが利用可能現金を超える場合はスケーリング処理と残差の lot 単位での再配分ロジックを搭載。
    - 価格欠損時のスキップとデバッグログ出力。

- 研究（research）モジュール（kabusys.research）
  - ファクター計算（research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（必要サンプル不足時は None を返す）。
    - calc_volatility: 20日 ATR、ATR 相対値（atr_pct）、20日平均売買代金、出来高比率。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE（EPS 欠損時は None）。
    - いずれも DuckDB を直接使う SQL ベース実装で、prices_daily / raw_financials のみ参照（外部 API に依存しない）。
  - 特徴量探索（research.feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（複数 horizon を同時に SQL で取得）。
    - calc_ic: スピアマン順位相関（IC）を計算。データ不足や定常値の場合は None を返す。
    - rank: 同順位は平均ランクとするランク関数（丸め処理で ties の検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）を再エクスポート。

- AI 関連（kabusys.ai）
  - ニュース NLP（ai.news_nlp）
    - raw_news を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（JST ベースを UTC に変換）：前日 15:00 JST 〜 当日 08:30 JST を対象。
    - 入力テキスト長・記事数のトリム（1銘柄最大 _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄）・JSON Mode を利用した厳密なレスポンス検証。
    - リトライ戦略: 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフ（最大リトライ回数制御）。
    - レスポンス検証・数値クリップ（±1.0）。部分失敗に備え、書き込みは該当コードのみ DELETE→INSERT（冪等かつ他コード保護）。
    - API キー未設定時は ValueError を発生。
    - フェイルセーフ: API 失敗時はスキップし他銘柄処理を継続。
  - レジーム検出（ai.regime_detector）
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（'bull' / 'neutral' / 'bear'）を算出。
    - マクロニュースはキーワードフィルタリングしタイトルを LLM へ渡す（記事なしなら API コールを行わず macro_sentiment=0.0）。
    - 合成スコアはクリップ・閾値判定でラベル付与し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー未設定時は ValueError を発生。API 失敗時は macro_sentiment を 0.0 にフォールバックして処理継続。
    - news_nlp とは目的に応じて OpenAI 呼び出し処理を独立化（モジュール間のプライベート関数共有を回避）。

- 監視永続化層（kabusys.monitoring.monitoring_db）
  - SQLite ベースの監視ログ永続化用関数 `init_monitoring_db(conn)` を提供。
  - system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを冪等で作成。

### Changed
- なし（初期リリースのため）

### Fixed
- なし（初期リリースのため）

### Removed
- なし

### Security
- OpenAI API キーは環境変数 `OPENAI_API_KEY` または関数引数で解決。キー未設定時は例外により明示的に失敗させる設計。

### Notes / Known limitations / TODO
- position_sizing の価格欠損（price == 0.0）時は現状スキップとなるため、エクスポージャーや発注量が過少見積りになる可能性あり（将来的に前日終値や取得原価でのフォールバックを検討）。
- DuckDB への executemany に空リストを渡せない制約への対応（空チェックを導入）。
- news_nlp / regime_detector は OpenAI API 呼び出し周りをテストしやすくするため、内部呼び出し関数に対して unittest.mock.patch による差し替えを想定している。
- マジックナンバー／デフォルト値（lot_size=100、risk_pct=0.005 等）は将来的にマスタや設定から読み取る設計に拡張可能。
- research モジュールは DuckDB のテーブル（prices_daily / raw_financials）を前提としているため、投入データの整備が必須。

---

著者: コードベースの内容から推測して自動生成  
（実際の変更履歴やリリースノートはプロジェクト管理者による確認・補足を推奨します）