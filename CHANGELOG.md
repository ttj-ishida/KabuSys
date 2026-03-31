# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルは、ソースコードから推測できる実装内容を基に作成した初期リリース向けの変更履歴です。

注: 日付はコード解析時点（2026-03-31）を採用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31

### Added
- プロジェクト初期リリース。
- パッケージの公開エントリポイントを追加（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

- 設定 / 環境変数管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読込（KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能）。
  - .env パーサ実装（export プレフィックス、引用符・エスケープ、インラインコメント処理対応）。
  - 自動ロード時に OS 環境変数を保護する仕組み（protected set）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境種別 / ログレベル等のプロパティを公開。
  - 必須環境変数未設定時は ValueError を送出する _require の導入。
  - KABUSYS_ENV / LOG_LEVEL の検証（許可値の制約）を実装。

- AI モジュール群を追加（src/kabusys/ai）。
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - バッチサイズ、記事数上限、1銘柄あたりの文字数上限を設定（トリム実装）。
    - JSON Mode を想定したレスポンス検証・復元ロジック（前後の余計なテキストを含む場合に最外の {} を抽出）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはスキップして継続（フェイルセーフ）。
    - DuckDB の executemany に関する空リスト制約に配慮した DB 書き込み（存在するコードのみ DELETE → INSERT）。
    - score_news(conn, target_date, api_key=None) を公開。APIキー指定が無い場合は OPENAI_API_KEY 環境変数を参照し、未設定時は ValueError を送出。
    - UTC naive datetime を用いるニュース収集ウィンドウ計算（JST→UTC 変換ロジックを内包、ルックアヘッドバイアス防止のため date.today を使わない）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で regime を評価（'bull' / 'neutral' / 'bear'）。
    - マクロニュースフィルタ（キーワードリスト）によるタイトル抽出、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント推定。
    - API エラー時は macro_sentiment=0.0 にフォールバック、リトライロジックあり。
    - レジーム結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開。APIキー未指定時は ValueError を送出。

  - ai/__init__.py で score_news を公開。

- データプラットフォーム関連モジュールを追加（src/kabusys/data）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day を実装。
    - カレンダー未取得時の曜日ベースフォールバック（土日非営業）をサポート。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants からの差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）を実装。バックフィル・健全性チェックあり。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを追加（target_date, fetched/saved counts, quality_issues, errors 等）。
    - 差分取得、保存、品質チェックのワークフローを想定したユーティリティを実装（jquants_client と quality モジュールを利用）。
    - DuckDB のテーブル存在チェック、最大日付取得等のユーティリティを実装（一部未完部分を含むコード構成）。
  - etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）。

- リサーチ / ファクター計算モジュールを追加（src/kabusys/research）。
  - factor_research.py
    - Momentum：mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算する calc_momentum(conn, target_date) を実装。過去データ不足時は None を返す設計。
    - Volatility / Liquidity：atr_20 / atr_pct / avg_turnover / volume_ratio を計算する calc_volatility(conn, target_date) を実装。true_range の NULL 伝播を明示的に制御。
    - Value：raw_financials から最新財務データを取り出し per / roe を計算する calc_value(conn, target_date) を実装。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None) を実装（デフォルト horizons=[1,5,21]、入力検証あり）。
    - IC（Spearman の ρ）を計算する calc_ic(factor_records, forward_records, factor_col, return_col) を実装（最小有効レコード数チェックあり）。
    - ランク変換ユーティリティ rank(values) と factor_summary(records, columns) を実装（count/mean/std/min/max/median を算出）。
  - research/__init__.py で主要関数を公開。

### Changed
- （初回公開のため既存からの変更は無し。設計上の重要点を明示）
  - すべての AI 系関数・ETL・Research ユーティリティは「ルックアヘッドバイアス防止」のため内部で datetime.today()/date.today() を直接参照しない設計を明示。
  - DuckDB の互換性制約（executemany に空リストを渡せない等）に配慮した DB 書き込み実装。

### Fixed
- （初版のため該当なし。コード内には各種例外処理・フォールバック実装が多数追加されているため堅牢性向上が期待される点を記載）
  - OpenAI 呼び出し関連で 5xx / タイムアウト / レート制限等に対するリトライとフォールバック（0.0 スコア）を実装。
  - DB トランザクション失敗時の ROLLBACK 試行とログ出力を追加。

### Deprecated
- なし

### Removed
- なし

### Security
- 環境変数読み込み時に OS 環境変数を保護（上書き防止）する仕組みを導入（.env 自動ロード時）。

---

既知の制約・注意点（実装から推測）
- OpenAI API（gpt-4o-mini）を利用するため、動作には有効な OPENAI_API_KEY が必要。score_news / score_regime は未指定時に ValueError を投げる。
- DuckDB のバージョン差異によりパラメータバインドの挙動が異なる箇所（list バインド等）に注意。コード内で互換性確保のための回避が入っている。
- .env 自動ロードはプロジェクトルートの特定に依存する（.git または pyproject.toml）。プロジェクト配布後に挙動を変えたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。
- news_nlp/regime_detector では LLM レスポンスの不確実性を考慮し、JSON パース失敗や不正レスポンスはスキップまたはデフォルト値で処理するフェイルセーフ設計。

もしリリースノートをもう少し詳細なモジュール単位の変更履歴（関数シグネチャ、戻り値の詳細、例外仕様）として拡張したい場合は、対象モジュールまたは関数を指定してください。