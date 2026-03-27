# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

[Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - src/kabusys/__init__.py にて public API を data・strategy・execution・monitoring でエクスポート。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの自動読み込みを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DBパス / 環境種別 / ログレベル等のプロパティ（必須変数は未設定時に ValueError を発生）を提供。
  - env 値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出する機能（score_news）。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の変換）を calc_news_window で提供。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事トリム（最大記事数・最大文字数）やレスポンスの堅牢なバリデーションを実装。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフによるリトライ、失敗時は該当チャンクをスキップ（フェイルセーフ）。取得済みコードのみ ai_scores テーブルへ置換（DELETE→INSERT）することで部分失敗時の保護を実現。
    - JSON Mode を利用し、レスポンス整形・JSON 抽出ロジックを備える。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を提供。
    - LLM 呼び出しの失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。API リトライロジックを実装。
    - レジーム計算は lookahead バイアスを避けるため target_date 未満のデータのみを使用。
    - 結果は idempotent に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ユーティリティ群を実装: is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day。
    - market_calendar データが未取得の場合は曜日ベース（平日のみ営業）でフォールバックする一貫したロジックを提供。
    - 夜間バッチジョブ calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィル・健全性チェックを含む。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETL の結果を表す ETLResult データクラスを実装（取得/保存件数・品質チェック結果・エラー一覧等を含む）。
    - 差分更新・バックフィル・品質チェックを行う設計方針（詳細はモジュール内コメント）。
    - ETLResult を kabusys.data.etl から再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュールにて定量ファクター計算関数を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等。
    - calc_value: raw_financials からの EPS/ROE を使った PER / ROE 計算（PBR 等は未実装）。
    - 実装は DuckDB SQL を利用し、prices_daily / raw_financials のみ参照。
  - feature_exploration モジュールにて解析ユーティリティを提供:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - rank: 平均ランク（同順位は平均ランク）への変換。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリー。

### Changed
- 設計方針の明記・安全性強化
  - すべての AI / レジーム / ニュース処理は datetime.today() / date.today() を直接参照しないよう設計され、ルックアヘッドバイアスを回避。
  - DuckDB を中心とした SQL 処理と、外部発注 API へのアクセス分離により、研究モジュールは本番環境の取引に影響を及ぼさない構成。

### Fixed
- （初版のため特定の「修正」はなし。モジュール内で多数のログ・例外処理を整備し、フェイルセーフ動作を明確化。）

### Security
- OpenAI、Slack、kabu/station、J-Quants 等のシークレットは環境変数経由で取得。Settings に必須変数が設定されていない場合は ValueError を発生させて安全側に停止する。
- .env の自動読み込み時に OS 環境変数を保護するため protected セットを使用し、デフォルトでは OS 環境変数が .env によって上書きされないよう実装。

### Notes / Implementation details
- OpenAI 使用:
  - モデル: gpt-4o-mini（ニュース / レジーム双方で使用）。
  - JSON Mode を使った厳密な JSON 出力期待と、パース耐性のための前後テキスト抽出ロジックを実装。
  - リトライ制御・バックオフ、5xx とそれ以外の扱い、APIStatus の互換性対応（status_code の有無への安全な対処）を実装。
- News NLP:
  - 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）。
  - 1 銘柄につき最新 _MAX_ARTICLES_PER_STOCK（デフォルト 10）件、最大 _MAX_CHARS_PER_STOCK（デフォルト 3000 文字）でトリム。
  - スコアは ±1.0 にクリップし、取得成功銘柄のみ ai_scores に書き込むことで部分失敗耐性を確保。
- Regime Detector:
  - ETF 1321 の MA200 乖離とマクロセンチメントの加重和（MA_WEIGHT 0.7, MACRO_WEIGHT 0.3）でレジームスコアを算出。しきい値で bull/neutral/bear を判定。
  - マクロキーワード群を定義し raw_news のタイトルでフィルターした上で LLM に渡す。
- DuckDB を主要なデータ層として利用。DuckDB バージョン固有の制約（executemany に空リスト不可 等）に配慮した実装がされている。

### Known issues / TODO
- PBR や配当利回りなどの追加バリューファクターは未実装（calc_value に明記）。
- strategy / execution / monitoring パッケージは __all__ に準備済みだが、今回提供されたコード断片では詳細な実装が含まれていない。今後の拡張予定。
- テスト用のモック差し替えポイントをいくつか提供している（例: _call_openai_api の patch でテスト可能）ものの、統合テスト・E2E テストケースは別途整備推奨。

---

著者注:
- 本 CHANGELOG は提供されたソースコードからの推測に基づき作成しました。実際のリリースノートと差異がある可能性があります。必要であればリリース日や詳細（貢献者・既知バグの追跡番号等）を追記します。