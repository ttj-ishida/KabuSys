# Changelog

すべての変更は Keep a Changelog の形式に従います。  
この CHANGELOG は提示されたソースコードの内容から推測して作成しています（実際のコミット履歴ではありません）。

全般的な方針:
- DuckDB を中心としたローカルデータプラットフォームを想定した実装。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価機能を提供。
- ルックアヘッドバイアス防止のため、日付参照や DB クエリは厳密に target_date 未満/以前などを指定。
- テストしやすさを考慮し、外部 API 呼び出し箇所は差し替え可能（モジュール内 private 関数を patch で置換可能）に実装。

## [Unreleased]
- （該当なし）

## [0.1.0] - 2026-04-01
初回公開（コードベースから推測）

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョンを `0.1.0` に設定。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env のパースは以下をサポート/考慮:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - インラインコメントの扱い（クォートなしはスペース直前の # をコメントとして扱う）
  - Settings クラスを提供。J-Quants / kabu ステーション / Slack / DB パス（DuckDB/SQLite）/監視閾値/環境モード・ログレベル等のプロパティを定義。
  - 環境値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL 値検証）と必須値取得時の明示的なエラー（_require）。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols を基にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - JST のビジネスウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して対象記事を抽出する calc_news_window を実装。
    - チャンク処理（デフォルト 20 銘柄/回）、1銘柄あたりの記事上限（件数・文字数）および JSON Mode を用いた厳密なレスポンス検証。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）とフェイルセーフ（失敗時は該当チャンクをスキップ、例外を上位へ波及させない設計）。
    - レスポンスの頑健なパース（前後余計なテキストの切り出し処理含む）とスコアクリップ（±1.0）。
    - スコア取得後、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に他銘柄スコアを保護する実装。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジームを判定（bull / neutral / bear）。
    - MA 計算は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）を採用してフェイルセーフ。
    - マクロニュース抽出は title に対する複数マクロキーワード検索。記事がある場合のみ OpenAI を呼び出す。
    - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）で、再試行ロジックを持つ。API 失敗時には macro_sentiment=0.0 にフォールバック。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

  - 両モジュールとも:
    - OpenAI クライアント生成時に api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する設計。
    - テスト容易性のため API 呼び出し箇所は patch で差し替え可能な設計（関数化）。

- リサーチ/ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を SQL で集約）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS=0/欠損時は None）。
    - 各関数は不足データ時に None を返す仕様、結果は (date, code) ベースの dict リストを返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト: [1,5,21]）の将来リターンを一括 SQL で取得。horizons のバリデーションあり。
    - calc_ic: スピアマン（順位）相関（IC）を計算。有効レコードが 3 未満なら None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と列ごとの統計サマリー（count/mean/std/min/max/median）を提供。
  - 研究系ユーティリティは外部依存を抑え、標準ライブラリと DuckDB SQL の組み合わせで実装。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar ベースの営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得日のフォールバックは曜日ベース（土日を非営業日扱い）。
    - calendar_update_job: J-Quants からカレンダーデータを差分取得して market_calendar に冪等保存。バックフィル・健全性チェック（未来日付の異常検知）を実装。
  - pipeline / etl:
    - ETLResult データクラスを定義（ETL 実行結果の集約: 取得件数・保存件数・品質問題・エラー等）。
    - pipeline と quality モジュールとの連携を想定した設計（差分取得、保存、品質チェックのフロー）。data.etl で ETLResult を再エクスポート。

- 技術的設計メモ（コード上の考慮点）
  - すべての「日付基準」処理において datetime.today()/date.today() を直接参照しない設計（テスト性とルックアヘッドバイアス防止）。
  - DuckDB のバージョン依存性（executemany の空リスト回避など）を考慮した安全実装。
  - API 呼び出しに対しては明示的な再試行、ログ出力、フェイルセーフ（フォールバック値の使用 / 該当チャンクスキップ）を採用。

### Fixed
- （初期リリースにつき該当なし）

### Changed
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

### Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から供給する設計。キーの取り扱いに注意すること（ログに出力しない等を想定）。
- .env 自動読み込み時は OS 環境変数を保護する仕組み（protected set）を導入。

Notes / 備考:
- 上記は提供されたソースコードから推測してまとめた CHANGELOG です。実際のコミット単位・日付・著者情報とは異なる可能性があります。
- 将来的な変更・バグ修正・改善点としては、より詳細な品質チェック実装（quality モジュール）、strategy / execution / monitoring 部分の具体実装、及びエンドツーエンドの統合テストの追加が想定されます。