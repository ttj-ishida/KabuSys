# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

- リリース日付は YYYY-MM-DD 形式
- 未リリースの変更は "Unreleased" に記載します

## [Unreleased]
- 現在なし

## [0.1.0] - 2026-03-31
最初の公開リリース。日本株のデータ取得・ETL・研究用ファクター計算、ニュースNLP / レジーム判定等の基盤的な機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機構を実装。プロジェクトルートは .git または pyproject.toml を起点に探索するため CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パース機能を独自実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメントの扱いを考慮）。
  - 環境変数の保護（既存 OS 環境変数を protected set として優先する挙動）と override 制御。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（KABUSYS_ENV）等のプロパティを提供。
  - KABUSYS_ENV の許容値検証（development / paper_trading / live）および LOG_LEVEL 検証を実装。

- AI モジュール（kabusys.ai）
  - news_nlp モジュールを追加（score_news / calc_news_window 等）。
    - raw_news / news_symbols テーブルから銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini / JSON mode）へバッチ送信してセンチメントを算出。
    - バッチ処理（最大 20 銘柄／チャンク）、1銘柄あたりの最大記事数・文字数トリム等のトークン肥大化対策を実装。
    - リトライ政策（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、レスポンスの厳格バリデーションとスコアの ±1.0 クリップ。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時に他データを守る設計。
    - ルックアヘッドバイアス対策のため datetime.today()/date.today() を参照しない設計。
    - OpenAI API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。
  - regime_detector モジュールを追加（score_regime 等）。
    - ETF 1321（Nikkei-225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、ニュースベースのマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照、マクロニュースはキーワードベースで抽出して LLM（gpt-4o-mini）で評価。
    - API フェイルセーフ：API 失敗時は macro_sentiment = 0.0 として継続。
    - DuckDB への冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス防止の設計。

- 研究（research）モジュール
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 約1ヶ月/3ヶ月/6ヶ月リターン、200 日 MA 乖離（ma200_dev）。
    - Value: PER（EPS が 0/欠損なら None）、ROE（raw_financials 参照）。
    - Volatility: 20 日 ATR（true range の扱いに注意）、相対 ATR・20日平均売買代金・出来高比等。
    - DuckDB 上の SQL ウィンドウ関数を活用し営業日ベースで計算。
    - データ不足時（行数不足等）は None を返す安全設計。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）, rank, factor_summary を実装。
    - 将来リターン（任意ホライズン）を一度のクエリで取得する効率化設計。
    - IC はランク相関（スピアマン ρ）を直接計算（tie を平均ランクで扱う）。
    - 統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージ __all__ で主要関数を再エクスポート。
  - kabusys.data.stats の zscore_normalize を再公開。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
    - market_calendar が未取得のときは曜日ベース（土日を非営業日）でのフォールバックを実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックあり。
  - pipeline / etl: ETLResult データクラスを公開（etl モジュールは pipeline.ETLResult を再エクスポート）。
    - ETL の差分更新設計、backfill 日数、品質チェック（quality モジュール連携）等の方針をコード内に定義。
    - ETLResult は品質問題・エラーの集約と to_dict 変換を持つ。
  - jquants_client 経由での保存処理呼び出しを想定した設計（save_* 関数の利用）。

- DuckDB 対応
  - 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、既定のテーブル（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols, market_regime 等）を参照／更新する実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で注入可能（テスト時の注入容易性と環境変数依存の緩和）。環境変数未設定時は ValueError を投げる明示的な扱い。

### Notes / 設計上の重要点
- ルックアヘッドバイアス回避: ニュース / レジーム / ETL / 研究モジュールは内部で date.today()/datetime.today() を参照せず、必ず caller が指定する target_date を基準に処理を行う設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は原則例外を握りつぶさずログを残して部分的に継続する（ニュースのセンチメントやマクロスコアは 0 にフォールバックする等）、ただし DB 書き込み失敗時はロールバックして例外伝播する設計。
- DuckDB executemany の互換性に配慮（空リストでの executemany を避けるチェック等）。

---

今後の予定（例）
- strategy / execution / monitoring の実装・テスト強化
- 単体テストおよび CI 設定の追加
- ドキュメント整備（API リファレンス、運用ガイド、ETL 運用手順）

もし CHANGELOG に追加してほしい詳細（たとえば各モジュールの関数別の例や既知の制約など）があれば教えてください。