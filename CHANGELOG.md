CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  
詳しくは https://keepachangelog.com/ を参照してください。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-03
-------------------

初回リリース。日本株自動売買/データ基盤の初期実装を公開します。主な追加点と設計上の注意点は以下の通りです。

Added
- パッケージ初期化
  - kabusys パッケージのバージョンを "0.1.0" として定義。主要サブパッケージ（data, research, ai, execution, monitoring, strategy など）を __all__ で公開。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート探索は __file__ を基点に .git または pyproject.toml を探索し、CWD に依存しない設計。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ対応、インラインコメントの適切な無視、クォートなし時のコメント取り扱いなどに対応。
  - Settings クラスを公開し、J-Quants / kabuステーション / LINE / DB / 監視 / システムなどの設定プロパティを提供。
    - 必須値は _require() でチェックし未設定時は ValueError を送出。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証を実装。
    - デフォルトパス設定（DUCKDB_PATH, SQLITE_PATH, PID/KILL フラグ等）を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols から対象記事を集約し、OpenAI (gpt-4o-mini, JSON Mode) にバッチ送信して銘柄ごとのセンチメントを ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC naive で処理）を calc_news_window で計算。
    - 1銘柄あたり記事数・文字数の上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によりトークン膨張を防止。
    - バッチサイズ、リトライ（429 / ネットワーク / タイムアウト / 5xx）、指数バックオフの実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、コード照合、数値チェック）と ±1.0 でのクリッピング。
    - DB 書き込みは部分失敗に耐える設計（対象コードのみ DELETE → INSERT）かつ DuckDB の executemany の制約を考慮。
    - API キー注入対応（api_key 引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を market_regime テーブルへ冪等書き込み。
    - マクロニュースは定義キーワード群でフィルタ（_MACRO_KEYWORDS）し、OpenAI (gpt-4o-mini) により -1.0〜1.0 のスコアを取得。
    - API 呼び出しのリトライ/バックオフ、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - DuckDB クエリではルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を確保。失敗時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム関連 (kabusys.data)
  - ETL パイプライン用の ETLResult データクラスを公開 (data.etl 再エクスポート)。
    - ETL 実行結果の集約（取得数、保存数、品質問題、エラー）とヘルパープロパティ（has_errors, has_quality_errors）を提供。
  - pipeline モジュール（ETL の土台）:
    - 差分取得、品質チェック、idempotent 保存（jquants_client の save_* を利用）など ETL 設計の基盤を実装。
    - backfill_days による後出し修正吸収、最大スキャン日・カレンダー先読み等の定義を含む。
  - マーケットカレンダー管理 (data.calendar_management)
    - market_calendar テーブルの存在チェック、営業日判定(is_trading_day)、SQ 判定(is_sq_day)、前後営業日取得(next_trading_day, prev_trading_day)、期間内営業日リスト取得(get_trading_days) を実装。
    - DB にカレンダーが無い/未登録日には曜日ベース（平日を営業日）でフォールバックする一貫性ある挙動。
    - calendar_update_job により J-Quants API から差分取得 → 保存（冪等）を行い、バックフィルと健全性チェック（将来日に対する不正チェック）を実装。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を取得し PER, ROE を計算（EPS が 0 または NULL の場合は None）。
    - すべて DuckDB SQL を用いて実装し、外部 API 呼び出しや発注ロジックとは分離。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（存在しない場合は None）。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合 None）。
    - rank / factor_summary: ランキング（同順位は平均ランク）や基本統計量を標準ライブラリだけで提供。
  - research パッケージ __init__ で有用関数を再公開（zscore_normalize を含む）。

Design / Behavior notes（設計上の特記事項）
- ルックアヘッドバイアス対策: 日次判定関数やニュース/価格のクエリは datetime.today()/date.today() に依存せず、必ず target_date を明示的に渡す設計。
- フェイルセーフ: 外部 API（OpenAI や J-Quants）失敗時は処理をスキップまたはデフォルト値（例: macro_sentiment=0.0）で続行し、致命的な例外を極力回避する方針。
- 冪等性: DB への書き込みは部分更新/DELETE→INSERT/ON CONFLICT 等で冪等に設計されている（部分失敗時に既存データを不必要に消さない）。
- テスト容易性: OpenAI 呼び出し箇所はモック差替え（unittest.mock.patch）を想定した関数分離がなされている。
- DuckDB 互換性への配慮: executemany の空リスト回避、date 型取り扱い変換ユーティリティなど実運用での互換性に配慮。

Fixed
- （初回リリースのため該当なし。ただし各モジュールで堅牢性・エラーハンドリングを重点的に実装）

Security
- OpenAI API キーや各種パスワードは Settings 経由で環境変数から供給する設計。.env 自動ロードは明示的に無効化可能。

Breaking Changes
- 初回リリースのため該当なし。

補足
- 本リリースはライブラリのコア機能群（データ取り込み・カレンダー管理・ファクター計算・ニュース NLP・レジーム判定）を整備したもので、実際の売買執行・監視/オペレーションコード等は別モジュール（execution, monitoring, strategy）として分離されています。今後のリリースで各モジュールの連携・オーケストレーション・ドキュメント拡充を予定しています。