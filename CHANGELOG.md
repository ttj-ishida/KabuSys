# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」の慣例に準拠しています。

最新版: 0.1.0 - 2026-04-04

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ基盤
  - パッケージのバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定/環境管理 (kabusys.config)
  - .env ファイルまたは環境変数からアプリ設定を自動読み込みする仕組みを実装。
  - プロジェクトルート探索を __file__ 起点で行い、.git または pyproject.toml を基準に判定（配布後も動作）。
  - .env のパースロジックを実装：
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - 行コメントの取り扱い（クォート内を除外）
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト向け）。
  - 必須環境変数取得ヘルパー _require と、Settings クラス（J-Quants / kabu / LINE / DB / 監視 / ログ等の設定プロパティ）を提供。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST）と calc_news_window ユーティリティを提供。
    - バッチ処理（1 API 呼び出し最大 20 銘柄）、銘柄内は最大記事数・最大文字数でトリムするトークン肥大化対策を実装。
    - OpenAI 呼び出しのリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列検査、code/score の型検証、スコアの ±1.0 クリップ）を実装。
    - 部分成功時に既存スコアを保護するため、更新は対象コードのみを DELETE → INSERT する冪等処理を提供。
    - テスト容易性のため _call_openai_api を直接 patch できるように実装。
    - エラー時は例外を投げるのではなく該当チャンク/銘柄をスキップするフェイルセーフ設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull / neutral / bear）を日次判定して market_regime テーブルへ書き込む機能を実装。
    - ma200_ratio の計算は target_date 未満のデータのみを用いることでルックアヘッドバイアスを防止。
    - マクロ記事抽出はタイトルに対するキーワードフィルタ（国内外のマクロ主要語）を使用。
    - OpenAI 呼び出しは最大リトライ回数とバックオフ制御を実装し、API 失敗時は macro_sentiment=0.0 にフォールバックして処理を継続するフェイルセーフ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT のトランザクションで冪等に行い、失敗時は ROLLBACK を試行して上位へ例外を伝播。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し market_calendar を冪等保存。
    - 営業日判定ユーティリティ群を提供：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が無い場合や未登録日は曜日ベース（平日＝営業日）でフォールバックする一貫した挙動。
    - 最大探索日数上限を設定して無限ループを回避する設計（_MAX_SEARCH_DAYS）。
    - 健全性チェックやバックフィル（直近数日を再フェッチ）をサポート。

  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを定義し、ETL 実行結果（取得／保存件数、品質チェック結果、エラー一覧など）を構造化して返却する仕組みを提供。
    - 差分更新・バックフィル・保存（jquants_client の save_* を用いた冪等保存）・品質チェックによる問題検出フローを設計に反映。
    - DuckDB の制約（executemany に空リスト不可）を考慮した実装を行い、部分失敗時の既存データ保護を実装。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20日）、流動性（20日平均売買代金、出来高比率）などのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - raw_financials と prices_daily の組合せで PER/ROE を算出する calc_value を提供。
    - DuckDB SQL を用いた効率的な集計を行い、欠損データは None を用いて扱う。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト [1,5,21]）に対する fwd_Xd を一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）：factor と将来リターンのスピアマンランク相関を計算（有効レコードが 3 未満の場合は None）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。
    - 外部依存をできる限り排し標準ライブラリのみで実装。

### 変更 (Changed)
- なし（初期リリースとして新規実装が中心）

### 修正 (Fixed)
- DuckDB の互換性対策:
  - executemany に空リストを渡せないバージョンへ対応するため、挿入／削除前に params の空チェックを行う実装を追加（ai.news_nlp, data.pipeline 等）。
- OpenAI レスポンスパース耐性向上:
  - JSON mode でも前後に余計なテキストが混入する場合を考慮して、最外の {} を抽出してパースするフォールバックを実装（news_nlp._validate_and_extract）。
- トランザクションの安全化:
  - DB 書き込み失敗時に ROLLBACK を試行し、それでも失敗した場合は警告ログを残すように改善（regime_detector, news_nlp, pipeline）。

### 非互換性 (Breaking Changes)
- なし（今回のリリースは初期導入・機能追加が中心で既存 API の破壊的変更は意図していない）

### セキュリティ (Security)
- OpenAI API キー等の機密情報は Settings を通じて環境変数から取得する設計。自動 .env ロードの動作は無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テスト環境や機密保護に配慮。

### テスト/開発支援 (Internal / Testing)
- OpenAI 呼び出しポイント（各モジュール内の _call_openai_api）を単体テストで差し替え可能な設計にし、外部 API へのモック注入を容易にしている。
- 多くの機能で datetime.today()/date.today() を直接参照しない設計とし、ルックアヘッドバイアスを防ぐため target_date を明示的に受け取る API を採用。

---

注: 本 CHANGELOG は提示されたコードベースの実装内容から推測して作成しています。実際のリリースノートでは、変更日・関連イシュー・著者情報などを適宜追加してください。