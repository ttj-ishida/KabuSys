# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、バージョン番号はパッケージの __version__（0.1.0）に合わせています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
Added
- パッケージ初版リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を実装。
- パッケージ情報
  - src/kabusys/__init__.py にて __version__=0.1.0、主要サブパッケージをエクスポート。
- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロードを実現。
  - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）、.env.local は上書き（override）を行う。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - 複雑な .env 行のパース対応（export プレフィックス、シングル/ダブルクォート内バックスラッシュエスケープ、コメント判定など）。
  - 必須設定取得ヘルパー _require と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルの検証付き）。
  - 環境名・ログレベル値の検証（不正値で ValueError を送出）。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算（JSTベース → UTC変換）を提供（calc_news_window）。
    - バッチサイズ／記事数／文字数上限などトークン肥大対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode 応答のバリデーションとパース復元（余分な前後テキストが混ざるケースに対応して最外の {} を抽出）。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx）と指数バックオフを実装。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で行い、部分失敗時に既存スコアを保護。
    - テスト容易性のため、OpenAI 呼び出しを差し替え可能（unittest.mock.patch が使える実装）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存する機能を実装。
    - prices_daily から MA200 乖離を計算するロジック（_calc_ma200_ratio）。データ不足時は中立値 (1.0) を使用してフェイルセーフ。
    - マクロキーワードで raw_news をフィルタしてタイトル集合を取得する機能（_fetch_macro_news）。
    - OpenAI（gpt-4o-mini）呼び出しラッパー、リトライ、エラー時フォールバック（macro_sentiment=0.0）を実装。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に行い、失敗時は ROLLBACK を試行。
- Data（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを扱うユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバック。
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫した判定を行う設計。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants API から差分取得 → 保存（jq.save_market_calendar を呼ぶ）を実装。バックフィルと健全性チェックあり。
  - ETL / パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開し、ETL 実行結果・品質チェック結果・エラー一覧を保持可能に。
    - 差分取得ロジック、バックフィル日数管理、品質チェック連携のための基盤を実装。
    - _get_max_date 等の DB ヘルパーを提供。
- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）を実装。
    - DuckDB SQL ベースで計算し、価格や raw_financials のみ参照する設計（取引や外部 API 呼び出し無し）。
    - 結果は (date, code) をキーとした dict のリストで返却。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
- テスト性・堅牢性対応
  - 多くの関数で api_key の注入可能（引数）にしてテストしやすく設計。
  - OpenAI 呼び出し部分はモジュール内で差し替え可能にしてユニットテストでモック可能。
  - 例外発生時はロギングしてフェイルセーフ（処理をスキップして継続）する設計を採用。
- ドキュメント的コメント
  - 各モジュールに設計方針・処理フロー・注意点を詳細に記載。

Fixed
- DuckDB executemany の空リストバインド制約を考慮して、埋め込みロジックで empty チェックを行うように対応（news_nlp と pipeline の DB 書き込みで対応）。
- OpenAI JSON Mode の応答に前後ノイズがある場合に最外の {..} を抽出してパースする復元処理を実装（news_nlp の _validate_and_extract）。
- DuckDB から返る日付値の型差異に対応するユーティリティ _to_date を追加して日付処理の互換性を改善（calendar_management / pipeline）。

Changed
- ルックアヘッドバイアス防止
  - 主要な処理（news_nlp, regime_detector, pipeline 等）は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計に統一。
- OpenAI 呼び出しの設定
  - モデルを gpt-4o-mini に統一し、response_format を JSON mode にして厳密なパースを想定。

Security
- 環境変数の自動ロード時に既存の OS 環境変数を保護するため、読み込み時に保護集合（protected）を使用。これによりホスト側の重要な環境変数が意図せず上書きされるのを防止。

Notes / Known limitations
- 現バージョンでは PBR や配当利回りなどのバリューファクターは未実装（calc_value に注記あり）。
- OpenAI 依存機能は API 可用性に依存するため、API エラー時はフォールバックやスキップ処理で継続するが、モデルや API 仕様の変更により将来修正が必要になる可能性あり。
- DuckDB のバージョン差異や SQL 構文互換性には注意（コード中に互換性対策の注記あり）。

---

著者注: 本 CHANGELOG はソースコードの内容とコメントから推測して作成しています。実際のリリースノートは実装履歴（コミットログ）やリリース時の変更点と合わせて調整してください。