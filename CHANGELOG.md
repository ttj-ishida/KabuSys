# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [Unreleased]

- なし

## [0.1.0] - 2026-04-03

初期リリース。日本株自動売買・データ基盤・リサーチ・AI支援機能の基盤実装を追加。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。パッケージバージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を探索して行う（CWD 非依存）。
  - .env パーサ実装（export 形式、クォート・エスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを実装し、以下の設定をプロパティで取得可能に：
    - J-Quants / kabu API / LINE / DB パス（DuckDB / SQLite） / 監視設定（PID ファイル等）
    - システム設定: KABUSYS_ENV の検証（development, paper_trading, live）や LOG_LEVEL の検証
    - ユーティリティプロパティ: is_live, is_paper, is_dev

- データ基盤（kabusys.data）
  - ETL パイプライン用の ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
  - pipeline モジュールに ETL 基盤ロジック（差分更新、バックフィル、品質チェックの枠組み）を実装。
    - ETLResult に品質問題・エラーの集約、辞書変換ユーティリティを実装。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーを管理するロジックを実装。
    - 営業日判定: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - 夜間バッチ: calendar_update_job により J-Quants から差分取得し market_calendar に冪等保存。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 最大探索日数 / バックフィル / 健全性チェックを実装し無限ループや異常データを防止。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を整理して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - calc_news_window（JST ベースのニュース窓）を提供。
    - バッチ処理（最大 20 銘柄/回）・トリム（記事数・文字数制限）を実装。
    - JSON Mode を想定したレスポンス検証と復元ロジックを実装（余計な前後テキストへの耐性）。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実行し、失敗時はログを残して対象をスキップするフェイルセーフ設計。
    - テスト容易性のため _call_openai_api の差し替え可能ポイントを用意。
    - スコアは ±1.0 にクリップ。DuckDB への書き込みは部分失敗時に既存スコアを保護するためコード絞り込みで DELETE → INSERT を行う（executemany を慎重に使用）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio 計算（target_date 未満のみを参照してルックアヘッドバイアスを回避）。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出し、OpenAI で macro_sentiment を算出。
    - API 呼び出しはリトライ/バックオフ処理を含み、失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK を試行して上位へ例外を伝播。
    - テスト容易性のため _call_openai_api の差し替え可能ポイントを用意。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - calc_momentum：mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を DuckDB SQL で一括計算。
    - calc_volatility：atr_20（20日 ATR）/ atr_pct / avg_turnover / volume_ratio を SQL で計算（欠損時は None を返す）。
    - calc_value：raw_financials から最新財務データを取得し PER / ROE を計算（EPS 0 または欠損は None とする）。
    - 各関数は prices_daily または raw_financials のみ参照し本番発注等には関与しない設計。
  - feature_exploration モジュール
    - calc_forward_returns：指定ホライズンに対する将来リターンを一括で取得（デフォルト [1,5,21]）。horizons のバリデーションを実施。
    - calc_ic：Spearman ランク相関（IC）を計算。データ不足（有効 n < 3）時は None を返す。
    - rank：同順位は平均ランクとなるランク関数を実装（丸めを行い ties の検出漏れを防止）。
    - factor_summary：count/mean/std/min/max/median の基本統計量を標準ライブラリのみで計算。
    - 外部ライブラリに依存しない実装方針を採用。

- DB バックエンド
  - DuckDB を主要な分析 DB として利用する方針を実装（SQL クエリ中心の処理）。
  - DB 書き込みは冪等化・部分更新を考慮（ON CONFLICT / DELETE→INSERT など）して実装。

### Changed
- 設計上の主要な方針を明文化（コードコメント・ドキュメント内に記載）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を計算ロジックに直接参照しない設計を明示。
  - API 呼び出しでのフェイルセーフ（失敗時にスコア 0.0 やスキップで継続）およびリトライ方針を統一。
  - DuckDB の executemany の挙動（空リスト不可）への対応をコード内で考慮。

### Fixed
- N/A（初版リリースのためバグ修正履歴なし。ただし実装には多くの警告ログ・健全性チェックを追加してランタイム問題を察知しやすくしている）

### Security
- 環境変数の必須チェックを実装（OpenAI API キー、J-Quants / kabu API パスワードなど）。未設定時は ValueError を送出して明示的に失敗する。
- .env 読み込み時に OS 環境変数を保護する protected セットを導入（override 動作時に既存 OS 変数を上書きしない）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的な取引ロジック・注文実行部分の実装とテスト。
- CI 上での DuckDB テストフィクスチャ整備、および OpenAI 呼び出しのモックを用いた単体テストカバレッジ拡充。
- ai モジュールのスコア格納スキーマ拡張（複数スコア種の保存・履歴管理）やモデル切替の設定化。

もし特定のファイルや変更点の説明をより詳細にしたい箇所があれば教えてください。