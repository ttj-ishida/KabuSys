# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0 — 2026-03-31

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期リリース。
- パッケージメタ情報
  - kabusys.__version__ = 0.1.0、パッケージの公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境変数／設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境 > .env.local > .env。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパースは export プレフィックス、シングル／ダブルクォート内のエスケープ、コメント処理をサポート。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須。未設定時は ValueError）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント（ai_scores テーブル）を生成・書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換済み）。
    - バッチサイズ、最大記事数、文字数トリム、リトライ（429/ネットワーク/5xx に対する指数バックオフ）等の制御。
    - レスポンスバリデーションとスコア ±1.0 のクリップ。
    - 部分成功時の DB 保護（対象コードのみ DELETE → INSERT）を実装。
    - テスト用に _call_openai_api をモック可能に設計。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - prices_daily からのデータ取得でルックアヘッドを防止する条件を明示。
    - マクロニュース抽出用キーワード群と OpenAI 呼び出し、リトライ／フォールバック（API 失敗時は macro_sentiment=0.0）。
    - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）。

- Research（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）等を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出（EPS 0 または欠損時は None）。
    - 全関数は DuckDB の prices_daily / raw_financials を参照し外部 API へアクセスしない。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを営業日ベースで計算。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク）相関を計算（有効レコード < 3 の場合は None を返す）。
    - rank: 平均ランク（同順位は平均ランク）を計算。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - すべて標準ライブラリのみで実装（pandas など外部依存なし）。

- Data（kabusys.data）
  - calendar_management
    - market_calendar を基に営業日判定・前後営業日取得・期間内営業日リスト・SQ 判定機能を提供。
    - DB にカレンダーがない場合は土日ベースのフォールバックを実施。
    - calendar_update_job: J-Quants API から差分取得し market_calendar テーブルへ冪等更新（バックフィル、健全性チェックあり）。
  - pipeline / etl
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を公開（kabusys.data.etl が再エクスポート）。
    - ETL フローの設計（差分取得、保存、品質チェック）に対応するユーティリティを提供。
    - DuckDB テーブルの最大日付取得やテーブル存在チェック等のヘルパーを実装。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 非推奨 (Deprecated)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- API キー等の必須値は Settings 経由で厳密に取得され、未設定時は明確なエラーメッセージを出力する設計。
- .env ファイル読み込みはプロジェクトルートを基準に行い、OS 環境変数を保護する実装（protected set）。

## 重要な注意事項 / 移行ガイド・運用メモ

- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須とされます。未設定時は ValueError を送出します。
  - OpenAI を利用する機能（score_news / score_regime）は api_key 引数を受け取るか、環境変数 OPENAI_API_KEY を設定してください。

- 自動 .env 読み込み
  - デフォルトでパッケージ読み込み時にプロジェクトルートの .env / .env.local を読み込みます。テストや特殊な環境では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化してください。

- DuckDB スキーマ依存
  - 多数のモジュールが DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime など）に依存しています。実行前に該当スキーマが整備されていることを確認してください。
  - score_news は DuckDB の executemany に対する空リストバグを考慮して実装されています（DuckDB 0.10 系での互換性を考慮）。

- LLM（OpenAI）呼び出しの挙動
  - モデル: gpt-4o-mini を想定し、JSON mode（response_format={"type":"json_object"}）での呼び出しを行います。
  - レスポンスパースや API エラーはフェイルセーフ設計。news_nlp: 失敗したチャンクはスキップ（空辞書返却）、regime_detector: マクロスコア失敗時は macro_sentiment=0.0 として継続。
  - テスト用に内部の _call_openai_api をモック（patch）する設計です。

- ルックアヘッドバイアス対策
  - 日付ロジックは内部で datetime.today()/date.today() に依存しない設計を意図しています（関数は target_date を明示的に受け取り、DB クエリは target_date 未満／等の条件でルックアヘッドを防止）。

- ロギング
  - 各モジュールで適切に logger を使用し、失敗時やフォールバック時に Warning / Info / Debug を出力します。LOG_LEVEL は Settings.log_level で検証されます。

## 開発者向けメモ
- テスト容易性:
  - news_nlp._call_openai_api および regime_detector._call_openai_api を unittest.mock.patch で差し替え可能。
- 設計上の意図は各モジュールの docstring に記載されています。特に ETL / Data / Research 周りの設計方針を参照してください。

---

今後のリリースでは、strategy（売買戦略の具現化）や execution（発注）、monitoring（監視/アラート）の具体実装、より詳細な品質チェック機能や CLI / Worker の追加を予定しています。ご要望や不具合報告は issue にてお知らせください。