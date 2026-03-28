# Changelog

すべての非破壊的変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイル（および .env.local）/OS 環境変数から設定を自動ロードする仕組みを実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、CWD に依存しない実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export 形式・クォート・エスケープ・インラインコメントへの対応。
  - Settings クラスを実装しアプリ設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須項目は未設定時に ValueError）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルトを提供
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev ヘルパー

- データ基盤（src/kabusys/data/*）
  - calendar_management:
    - JPX マーケットカレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。
    - market_calendar テーブルを使った営業日判定ユーティリティ群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - バックフィル、先読み、健全性チェック (_BACKFILL_DAYS, _CALENDAR_LOOKAHEAD_DAYS, _SANITY_MAX_FUTURE_DAYS)。
  - pipeline / etl:
    - ETLResult データクラスを含む ETL パイプラインの骨格を実装（差分取得、保存、品質チェックのためのインターフェース）。
    - jquants_client と quality モジュールを介した差分取得・保存・品質判定の設計を反映。
    - DuckDB との互換性や executemany の注意点（空リスト回避）を考慮。
  - etl: ETLResult を public に再エクスポート（src/kabusys/data/etl.py）。

- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research:
    - Momentum, Value, Volatility, Liquidity 等の定量ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の不足時は None とする）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播を考慮）
      - calc_value: per, roe（raw_financials の最新レコードを target_date 以前から取得）
    - DuckDB SQL を用いた効率的なウィンドウ集計実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD 使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（結合・フィルタ・ties の取り扱い含む）。
    - rank: 同順位は平均ランクを採るランク変換ユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: 基本統計量（count, mean, std, min, max, median）を計算するユーティリティ。
  - research __init__ で主要関数をエクスポート。

- AI（src/kabusys/ai/*）
  - news_nlp (src/kabusys/ai/news_nlp.py):
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）算出ユーティリティ calc_news_window を実装。
    - バッチサイズ、記事数上限、文字数トリム（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーションと数値クリップ（±1.0）を実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx）は指数バックオフで処理し、失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - 書き込みは部分失敗に備えて取得済みコードのみ DELETE→INSERT の冪等処理を採用（トランザクション管理）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - regime_detector (src/kabusys/ai/regime_detector.py):
    - ETF 1321（225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定・保存。
    - ma200_ratio を安全に計算（データ不足時は中立 1.0 を採用し警告ログ）。
    - マクロニュースは news_nlp.calc_news_window を使ってフィルタしたタイトルを取得して LLM に送信。
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける）かつリトライ・エラー処理を実装。API 失敗時は macro_sentiment=0.0 をフォールバック。
    - 判定結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT、エラー時は ROLLBACK）。
    - デザイン方針としてルックアヘッドバイアス回避（datetime.today() を直接参照しない）を明示。

- 共通実装上の配慮 / 品質
  - "ルックアヘッドバイアス防止" の設計指針を各 AI/研究モジュールで徹底（target_date ベースの集計・クエリ）。
  - DuckDB を主要な分析 DB として想定し、SQL と Python の組み合わせで効率的に処理。
  - OpenAI に対する堅牢なエラーハンドリング（再試行・5xx 判定・JSON パースの復元処理）を導入。
  - ロギングと警告を充実（データ不足・API 失敗・ROLLBACK 失敗等で明示的ログ）。
  - テストしやすい設計:
    - API 呼び出し関数の差し替え箇所を明確化（unittest.mock.patch を想定）。
    - api_key を引数で注入可能（テストでの固定化が容易）。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Deprecated
- （初回リリースのためなし）

### Removed
- （初回リリースのためなし）

### Security
- OpenAI API キーや外部トークンは Settings 経由で必須チェックを行い、未設定時は ValueError を投げることで誤動作を防止。
- .env の読み込みは OS 環境変数を保護するため protected セットを用いた上書き制御を導入。

---

注記:
- この CHANGELOG は現在のコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴や PR 説明を元に必要に応じて修正してください。