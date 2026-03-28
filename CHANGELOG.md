# Changelog

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。以下の主要機能・設計方針・公開 API を含みます。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - src/kabusys/__init__.py で公開モジュール: data, strategy, execution, monitoring（将来機能拡張用のエントリポイントを用意）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動ロード機能を実装（優先順: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探す方式で CWD に依存しない実装。
  - .env 解析は export KEY=val 形式、クォートやエスケープ、インラインコメントを考慮した堅牢なパーサーを採用。
  - Settings クラスを提供し、主要な設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時は明示的に ValueError を送出。

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py)
  - OpenAI（gpt-4o-mini）の JSON Mode を用いたニュース記事の銘柄別センチメント集計機能。
  - score_news(conn, target_date, api_key=None) を公開:
    - 対象ウィンドウ: 前日15:00 JST 〜 当日08:30 JST（内部は UTC naive datetime を返す calc_news_window）。
    - raw_news と news_symbols を結合し、銘柄ごとに最新 N 件を集約（記事数上限・文字数上限あり）。
    - 最大 20 銘柄ずつバッチ送信（_BATCH_SIZE=20）し、API レスポンスをバリデーションして ai_scores テーブルへ冪等的に置換（DELETE→INSERT）。
    - スコアは ±1.0 にクリップ。API の一時エラー（429・ネットワーク・タイムアウト・5xx）は再試行（指数バックオフ）、失敗時はスキップして継続（フェイルセーフ）。
  - テスト容易性のため _call_openai_api の差し替えポイントを用意。
  - レスポンスの耐性強化（前後の余計なテキストを含む場合の JSON 抽出、整数コードを文字列化して照合など）。

- マーケットレジーム判定（AI + 指標合成） (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None) を公開:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出は news_nlp.calc_news_window と raw_news からマクロキーワードでフィルタ。
    - LLM 呼び出しは gpt-4o-mini、JSON モードで macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - DuckDB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
  - 設定可能・固定の定数群（キーワードリスト、重み、しきい値、最大記事数、リトライ設定等）を内包。

- データプラットフォーム関連 (src/kabusys/data/)
  - calendar_management.py
    - JPX カレンダー管理／営業日判定機能を実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar がない場合は曜日ベースのフォールバック（平日を営業日）を使用。
    - calendar_update_job で J-Quants API からの差分取得 → jq.save_market_calendar で冪等保存、バックフィル・健全性チェックを実装。
  - pipeline.py / etl.py
    - ETL の結果を表す dataclass ETLResult を実装・公開（etl.py で再エクスポート）。
    - 差分取得のためのユーティリティ（_get_max_date 等）、バックフィル、品質チェック（quality モジュール連携を想定）等の設計。
    - ETL の設計方針: idempotent 保存、品質問題の集約（Fail-Fast ではなく呼び出し元で処理決定）、テスト容易性（id_token 注入）。
  - jquants_client, quality 等のクライアント連携を想定した構成（実装は別モジュール）。

- リサーチ（factor / feature） (src/kabusys/research/)
  - factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。
    - prices_daily / raw_financials のみを参照し、DuckDB 上で SQL + Python により計算。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（データ不足は None）。
    - Value: PER（EPS が 0/欠損の場合 None）、ROE（最新の raw_financials を使用）。
  - feature_exploration.py
    - calc_forward_returns: 任意のホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装。
    - calc_ic: スピアマンのランク相関（IC）を実装（合致レコードが 3 未満なら None）。
    - rank: 平均ランク（ties は平均ランク）を計算するユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する集計ユーティリティ。
  - 研究向けユーティリティは外部依存（pandas 等）を避け、標準ライブラリ + DuckDB で完結する設計。

- 再エクスポート（public API）
  - research パッケージ __init__ で zscore_normalize（kabusys.data.stats 由来）や主要関数を再エクスポート。
  - data.etl は ETLResult を外部に公開。

### Fixed
- 初版につき明確なバグ修正履歴はなし（初期実装での既知のフェイルセーフや警告ログを多用した堅牢化を実装）。

### Security
- OpenAI API キーは引数で注入可能。環境変数 OPENAI_API_KEY が使われるが、明示的な引数優先の設計によりキー管理の柔軟性を確保。
- 必須の認証系トークンは settings にて必須プロパティとなり、未設定時は ValueError を送出して安全側に振る。

### Design / Notable implementation details
- ルックアヘッドバイアス対策: ほとんどの関数（score_news, score_regime, ETL/研究系関数等）は datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計。
- DuckDB を主要データ格納先として想定。SQL はパフォーマンスを意識したウィンドウ関数・LEAD/LAG を活用。
- DB 書き込みは基本的に冪等（DELETE→INSERT / ON CONFLICT）で実装し、部分失敗時に既存データを無駄に消さないよう配慮。
- AI 呼び出し部分はリトライ/バックオフ・レスポンスバリデーション・クリップなどのフォールトトレラントな実装。テスト時に差し替え可能なポイントを提供。

---

今後のリリースでは、strategy / execution / monitoring の具体的な発注ロジック・バックテスト機能・運用監視統合などを追加予定です。必要であれば CHANGELOG をアップデートし、各モジュールの変更差分を詳細に記載します。