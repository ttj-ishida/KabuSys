CHANGELOG
=========

すべての重要な変更点は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
慣例: "Added", "Changed", "Fixed", "Security" などのセクションを使用しています。

[0.1.0] - 2026-04-04
-------------------

Added
- 初回公開: kabusys パッケージ v0.1.0 を追加。
  - パッケージのエントリポイント: src/kabusys/__init__.py （__version__ = "0.1.0"）。
- 環境設定管理:
  - kabusys.config.Settings を導入。環境変数経由で各種設定（APIキー、DBパス、監視閾値、環境種別など）を取得。
  - .env 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env ファイルのパース対応強化: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いのルールなどに対応。
  - .env の上書き挙動: .env（デフォルトで既存 OS 環境変数を上書きしない）→ .env.local（override=True）という優先順位を採用。OS 環境変数は protected として上書きから保護。
  - 必須環境変数未設定時は _require() による明示的な ValueError を送出。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性チェックを実装（許容値の検証）。
- AI モジュール:
  - kabusys.ai.news_nlp.score_news:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini / JSON Mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄/chunk）、1 銘柄あたりの記事数/文字数トリム、JSON レスポンスの堅牢なバリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ処理を実装。失敗はフェイルセーフでスキップし処理継続。
    - API キーは引数注入または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
    - DuckDB executemany の互換性（空リストバインド回避）に配慮した DB 書き込み（DELETE → INSERT の置換手法）。
  - kabusys.ai.regime_detector.score_regime:
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ書き込み。
    - prices_daily からのルックアヘッド回避（target_date 未満のみ参照）、マクロ記事の抽出、OpenAI 呼び出し（JSON パース、リトライ、フェイルセーフ）等を実装。
    - API 失敗時は macro_sentiment=0.0 として継続し、DB 書込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。
    - モジュール間の疎結合化: OpenAI 呼び出し用プライベート関数をモジュール毎に独立実装。
- Research（因子解析）:
  - kabusys.research パッケージ:
    - factor_research: calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照してモメンタム、ATR 等の因子を計算。
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
    - 設計上の配慮として DuckDB 接続を受け取り SQL と標準ライブラリだけで完結する実装。
- Data（データ基盤）:
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB に calendar がない場合は曜日ベース（土日非営業日）でフォールバックする設計。
    - calendar_update_job: J-Quants クライアント経由で差分取得・バックフィル・保存（冪等）を行う夜間ジョブを実装。取得範囲や健全性チェックを含む。
  - pipeline / ETL:
    - ETLResult データクラスを実装し、ETL の取得件数・保存件数・品質問題・エラー一覧を統一表現。
    - データ差分取得、保存、品質チェック（quality モジュールとの連携）を想定した設計を実装。初回ロード時の最小日付等の定数を追加。
  - data.etl で ETLResult を再エクスポート。
- その他ユーティリティ:
  - DuckDB 操作の互換性考慮ユーティリティ（テーブル存在チェック、日付変換等）を追加。
  - 複数モジュールで一貫して「ルックアヘッドバイアス回避」（datetime.today()/date.today() の直接参照禁止）を採用。

Fixed
- .env 読み込みでの I/O エラー時に warnings.warn を出すようにして例外直上げを回避。
- .env のパースで無効行・コメント行を正しく無視するよう修正。
- OpenAI レスポンスのパースエラーや API エラー発生時に適切にログを残し（warning/exception）、フォールバック動作（0.0 やスキップ）でシステム全体の耐障害性を向上。
- news_nlp の JSON モードでも前後の余計なテキストが混入したケースに対して最外の {} を抽出して復元するロジックを追加（レスポンスパース堅牢化）。
- score_news における DuckDB executemany の空パラメータ禁則に対応（空時は実行をスキップ）し、部分失敗時に既存スコアを守る削除→挿入戦略を採用。

Changed
- OpenAI 呼び出し実装をモジュール単位で独立化（news_nlp と regime_detector で同名の内部関数を共有しない設計）。モジュール間の結合を低減。

Security
- AI / 研究関連処理でのルックアヘッドバイアス対策として、すべてのスコアリング/解析処理は外部から与えられた target_date のみを基準に計算し、内部で現在日時を参照しない方針を徹底（バックテスト時のデータ漏洩防止）。

Known issues / Notes
- DuckDB バージョン依存の挙動（例: executemany に空リストが渡せない等）があるため、当面の互換性対策として空パラメータは呼ばない実装にしている。
- news_nlp と regime_detector は OpenAI API 依存（OPENAI_API_KEY）。運用環境では API キーの管理に注意すること。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存。クライアント実装の例外は呼び出し側でロギングして 0 を返す設計。

-----

今後のリリースでは、以下が予定事項です（実装済み/未実装にかかわらず参照用）:
- ETL 実行本体（差分ロジックの外側フロー）と quality モジュールの詳細な導入・ドキュメント化。
- モジュールのユニットテスト追加（OpenAI 呼び出し部はモック可能な設計）。