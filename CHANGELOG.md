# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - Initial release
リリース: Initial implementation（初期リリース）。以下の主要機能を実装しています。

### Added
- パッケージ基盤
  - パッケージのメタ情報を定義（kabusys.__version__ = "0.1.0"、公開モジュール __all__ の設定）。
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、カレントワーキングディレクトリに依存しない設計。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装（コメント・export プレフィックス・クォート中のエスケープ等に対応）。
  - Settings クラスを提供し、アプリケーションの設定値をプロパティとして取得可能（J-Quants、kabu API、LINE、DB パス、監視閾値、ログレベル等）。
  - 必須環境変数未設定時に ValueError を発生させる _require() を導入。
  - KABUSYS_ENV および LOG_LEVEL の値検証（不正な値は ValueError）。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）に対して一括（チャンク）でセンチメントを問い合わせ、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウの算出（JST ベース → DB 比較は UTC naive datetime）を提供（calc_news_window）。
    - バッチサイズ、記事数上限、文字数トリム、リトライ（指数バックオフ）などの実装。
    - レスポンス検証（JSON パース、results 配列、code/score 検証、スコアの ±1.0 クリップ）。
    - DuckDB に対する冪等的な書き込み（DELETE → INSERT）および DuckDB executemany の空リスト取り扱いに配慮。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出・保存。
    - OpenAI 呼び出し（gpt-4o-mini）を JSON モードで行い、リトライ・バックオフ・エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行）。
    - LLM 呼び出しは news_nlp 側と意図的に独立した内部実装でモジュール結合を避ける設計。
- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - market_calendar が未取得または該当日が未登録の場合は曜日ベースのフォールバック（週末は非営業日）を提供。
    - next/prev_trading_day は最大探索日数を設定して無限ループを防止。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得 → 冪等保存（バックフィル + 健全性チェック）を実行。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（取得数・保存数・品質診断結果・エラー一覧などを保持）。
    - 差分更新、バックフィル、品質チェック連携を想定した設計。jquants_client と quality モジュールを利用する想定。
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティを実装（内部ユーティリティ）。
  - etl モジュールの公開インターフェースとして ETLResult を再エクスポート。
- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）、20 日平均売買代金・出来高比率を計算。欠損時は None。
    - calc_value: raw_financials から最新財務データを取得して PER・ROE を算出。EPS が 0 または欠損の場合は None。
    - DuckDB の SQL ウィンドウ関数を活用した実装。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 将来リターン（指定営業日ホライズン）を計算。horizons の検証（1〜252 日）を実施。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 は None）。
    - rank: 同順位は平均ランクで処理するランク関数を提供（丸めで ties を回避）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計ユーティリティ。
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
- 設計上の重要な方針・安全機構
  - ルックアヘッドバイアス防止のため、各モジュールで datetime.today()/date.today() を直接参照しない（ターゲット日を明示的に受け取る）。
  - OpenAI API 呼び出しでの失敗はフェイルセーフ（0.0 フォールバックや対象コードのみの書き換え等）によりシステム全体の停止を防止。
  - DuckDB に対する操作は冪等性（DELETE→INSERT）と executemany の空引数回避に配慮。
  - テスト容易性を考慮し、OpenAI 呼び出し部分をモック差し替えできる設計を採用。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI の API キーは呼び出し側が明示的に api_key 引数を渡すか、環境変数 OPENAI_API_KEY を設定する必要がある旨を明確化（未設定時は ValueError を送出）。

### Notes / Breaking changes
- settings のプロパティ（KABUSYS_ENV, LOG_LEVEL など）は不正値で ValueError を送出するため、運用時は環境変数の内容に注意してください。
- score_news / score_regime は OpenAI API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）。
- DuckDB のバージョン依存（executemany の空リスト不可等）に配慮した実装になっています。既存 DB 運用環境と整合性が必要です。

---

（今後の変更は Unreleased セクションに追記してください。）