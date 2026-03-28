# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベース（src/kabusys）からの実装内容を元に推測して作成しています。

フォーマット:
- Unreleased: 今後の変更予定（現時点では空）。
- 各リリースはバージョンと日付（推定）を付記。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
最初の公開リリース（推定）。主要機能、データ処理、AI スコアリング、研究用ユーティリティ、環境設定ユーティリティなどを含む。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = "0.1.0" を定義。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env パーサーの実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いに対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、主要な設定項目（J-Quants / kabu API / Slack / DB パス / ログレベル / 環境種別など）をプロパティ経由で取得。値検証（env, log_level の許容値チェック）を実装。
  - デフォルトの DB パス（duckdb / sqlite）の設定サポート。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いた銘柄別ニュース集約と OpenAI（gpt-4o-mini）を使ったセンチメントスコアリング機能を実装。
  - time window の計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）を calc_news_window で提供。
  - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数のトリム、JSON Mode を利用した応答パース、レスポンス検証機能を実装。
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフを実装し、失敗時は安全にスキップするフェイルセーフ設計。
  - レスポンスバリデーション（results リスト、code/score の整合、スコアの数値化・有限値判定）とスコアの ±1.0 クリッピングを実装。
  - ai_scores テーブルへの冪等置換（DELETE → INSERT）を実行。部分失敗時に既存のスコアを保護する実装。
  - テスト容易性のために _call_openai_api をモック差替え可能に設計。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースの LLM ベースマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - MA200 計算はルックアヘッドバイアスを避けるため target_date 未満のみのデータを使用。データ不足時は中立扱い（ma200_ratio=1.0）。
  - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）で JSON 出力を期待、レスポンスパース失敗や API エラー時は macro_sentiment=0.0 のフォールバックを行うフェイルセーフ。
  - API 呼び出しの再試行（RateLimit/接続エラー/タイムアウト/5xx に対する指数バックオフ）を実装。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。

- 研究用ユーティリティ（kabusys.research）
  - ファクター研究モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）等を計算。
    - calc_value: raw_financials から PER / ROE を計算（EPS=0 や欠損時は None）。PBR・配当利回りは未実装として明記。
    - calc_volatility: 20 日 ATR（true range の取り扱いを明確にした実装）、相対 ATR、20 日平均売買代金、出来高比率などを計算。
  - 特徴量探索モジュールを追加:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算する汎用実装。horizons の検証（正の整数かつ <=252）あり。
    - calc_ic: スピアマン（ランク）相関で IC を計算（有効レコード数 < 3 の場合は None）。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を算出するサマリー機能。
  - いずれの関数も DuckDB 接続を受け取り、prices_daily / raw_financials 等の DB のみを参照する設計（本番の発注 API 等にはアクセスしない）。

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）管理、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）を採用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィルや健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスを公開（pipeline.ETLResult を etl モジュールで再エクスポート）。
    - ETL パイプラインのユーティリティ（差分取得ロジック、最小データ日、backfill、品質チェックとの連携）を実装。品質チェックでの問題は収集して呼び出し元に委ねる設計。
  - jquants_client などの外部クライアントは別モジュールとして抽象化（fetch/save 関数呼び出しを想定）。

### Changed
- （初回リリースにつき変更履歴はなし）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Notes / Design decisions
- ルックアヘッドバイアス対策: AI スコアリング / レジーム判定 / リサーチ関数は internal に date を明示的に渡し、datetime.today() / date.today() を参照しない実装に統一。
- OpenAI 呼び出しは JSON Mode を利用し、応答パースの堅牢性（余分な前後テキストの復元、キー検証）を考慮。
- DuckDB に対する互換性注意:
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約）を入れている。
  - date 型・NULL 取り扱いを明示的に変換。
- フェイルセーフ方針:
  - AI / API 呼び出しが失敗してもシステムは継続（スコアは 0 またはスキップ）し、重大な DB 書き込みエラーは上位へ伝播して明示的に処理する。
- テスト容易性:
  - OpenAI 呼び出し部分はモック差替えを想定した設計になっている（内部関数を patch 可能）。

### Known limitations
- calc_value で PBR / 配当利回りは未実装。
- OpenAI モデルは gpt-4o-mini を指定しているが、API 仕様変化への互換性は限定的（例外ハンドリングはある程度考慮済み）。
- calendar_update_job / ETL の J-Quants クライアント呼び出しは外部依存（ネットワーク・認証設定が必要）。

---

この CHANGELOG はコードの実装内容から推測して作成しています。必要であれば、各項目を実装ファイルのコミット履歴や実際のリリース日付に合わせて修正・補完してください。