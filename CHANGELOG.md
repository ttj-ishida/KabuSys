KEEP A CHANGELOG
※本ファイルは Keep a Changelog の形式に準拠しています。

Unreleased
---------

- （現在のブランチには未公開の変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ概要: 日本株自動売買システムのコアモジュール群を提供。

- 環境設定 / 初期化
  - kabusys.config: .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを実装。
    - 自動ロード順序: OS環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .env パーサは export 〜、クォート、バックスラッシュエスケープ、行内コメントのルールに対応。
  - Settings クラスを公開（settings インスタンス）: J-Quants、kabu API、Slack、DB パス、環境種別（development/paper_trading/live）、ログレベル等を取得するプロパティを提供。
    - 必須環境変数未設定時は ValueError を送出するヘルパーを用意。

- AI / ニュース NLP
  - kabusys.ai.news_nlp.score_news:
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存。
    - 処理特徴:
      - JST時間帯（前日15:00〜当日08:30）のウィンドウ計算（UTC変換含む）
      - 1銘柄あたり最大記事数／最大文字数でトリム（トークン肥大化対策）
      - 最大 _BATCH_SIZE (20) 銘柄ずつバッチ送信
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
      - レスポンスバリデーション（results 配列/型/既知コード/数値）とスコアの ±1.0 クリップ
      - 部分失敗時も既存スコアを保護するため、書き込みは対象コードに限定して DELETE → INSERT を実行
    - APIキーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

  - kabusys.ai.regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - 特長:
      - prices_daily から target_date 未満のデータのみを使用しルックアヘッドバイアスを回避
      - マクロニュースはキーワードでフィルタし最新記事を上限件数で取得
      - OpenAI 呼び出しは再試行や 5xx 判定を考慮、失敗時は macro_sentiment=0.0 のフェイルセーフ
      - 設計上 news_nlp の内部関数と共有しない独立実装（モジュール結合を避ける）
    - APIキーは引数または環境変数 OPENAI_API_KEY。

- Data / ETL / カレンダー
  - kabusys.data.pipeline.ETLResult: ETL 実行結果を表す dataclass を公開（監査ログや呼び出し元で利用）。
    - ETL の各フェーズ（prices, financials, calendar）の取得・保存件数や品質問題、エラー一覧を保持。
    - has_errors / has_quality_errors / to_dict メソッドを提供。

  - kabusys.data.pipeline:
    - ETL 方針とユーティリティを実装（差分取得、バックフィル、品質チェックの基礎）。
    - DuckDB を想定した最大日付取得・テーブル存在チェック等のユーティリティ関数を提供。

  - kabusys.data.calendar_management:
    - JPX マーケットカレンダー管理と判定ロジックを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - market_calendar が未取得の場合は曜日（平日）ベースのフォールバックを行う設計。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新（バックフィル、健全性チェック含む）。
    - 探索上限（_MAX_SEARCH_DAYS）やバックフィル期間、先読み日数等の安全対策を実装。

- Research / ファクター計算 / 特徴量探索
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン・200日MA乖離などのモメンタムファクターを計算。
    - calc_volatility: 20日 ATR（平均）／相対ATR／20日平均売買代金／出来高比率などのボラティリティ・流動性指標を計算。
    - calc_value: raw_financials から取得した最新財務情報と当日の価格から PER / ROE を計算（EPS が 0 または欠損時は None）。
    - 全関数は DuckDB 上の prices_daily / raw_financials を参照し、外部 API にはアクセスしない設計。

  - kabusys.research.feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算（LEAD を使用）。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ。サンプル数不足時は None を返す。
    - rank: 同順位は平均ランクで処理（丸め誤差対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - 設計方針: pandas 等に依存せず標準ライブラリ＋DuckDB の SQL を活用。

- モジュール公開整理
  - 各サブパッケージの __init__ に主要関数を再エクスポート（例: kabusys.ai.score_news, kabusys.research.*）。

Notes / 注意点
- 環境変数（主なもの）
  - 必須: OPENAI_API_KEY（AI 機能を使う場合）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
  - DB パスデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
  - 環境種別: KABUSYS_ENV = development | paper_trading | live（デフォルト development）
  - ログレベル: LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
  - 自動 .env ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI 呼び出し
  - gpt-4o-mini を使用（JSON mode）。API エラーやパース失敗はフェイルセーフで基本はスキップまたは score=0.0 を採用。
  - テスト容易性のため内部の API 呼び出し関数はモジュール内で定義しており、unittest.mock.patch による差し替えが可能。

- DuckDB 書き込み
  - 書き込みは基本的に BEGIN / DELETE / INSERT / COMMIT（冪等性維持）で行う。失敗時には ROLLBACK を試行。
  - DuckDB の executemany に対する互換性（空リスト不可など）に配慮して条件分岐を行っている。

- ルックアヘッドバイアス対策
  - すべての「日次」処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に与える設計。prices_daily クエリも target_date 未満など排他的条件を採用。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

運用・導入メモ（短縮）
- まず .env.example を参考に .env を作成し、必要な環境変数を設定してください。
- AI 関連機能をローカルでテストする際は OPENAI_API_KEY を用意するか、api_key を関数に注入してください。
- テスト時に自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL / カレンダー更新は DuckDB 接続を渡して calendar_update_job / pipeline ロジックを呼び出します。

--- 
（補足）この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートにはリリース日や追加の作者／マイグレーション手順を追記してください。