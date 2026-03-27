Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット
----------
この CHANGELOG は "Keep a Changelog" の形式に従います。  
カテゴリ: Added, Changed, Fixed, Removed, Security, Deprecated, Internal。

[Unreleased]
------------

（現時点のコードベースは初回リリース v0.1.0 相当であるため、下記は v0.1.0 の項目です。今後の変更はこのセクションに追加してください。）

0.1.0 - YYYY-MM-DD
------------------

Added
- 初期リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。
  - パッケージ情報
    - バージョン: 0.1.0（src/kabusys/__init__.py）
    - パッケージ公開用 __all__ に data, strategy, execution, monitoring を指定。
  - 環境変数／設定管理（src/kabusys/config.py）
    - .env および .env.local を自動読込（プロジェクトルート判定：.git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
    - export KEY=val 形式やクォート／エスケープ、インラインコメントの取り扱いに対応した .env パーサ実装。
    - 環境変数必須チェック用 _require を提供（不足時は ValueError を送出）。
    - 主要設定プロパティを持つ Settings クラスを公開（settings インスタンス）。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live、検証あり）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、検証あり）
      - is_live / is_paper / is_dev のユーティリティプロパティ
  - AI モジュール（src/kabusys/ai）
    - ニュース NLP（src/kabusys/ai/news_nlp.py）
      - raw_news と news_symbols を使い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）に投げ、センチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
      - バッチ処理：1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE=20）。
      - 1 銘柄あたり最大記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
      - JSON mode を利用し、応答の検証・復元ロジック（余分なテキストを含む場合の {} 抽出）を実装。
      - リトライ/バックオフ対応（429/ネットワーク断/タイムアウト/5xx を対象、指数バックオフ）。
      - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
      - DB 書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存データを保護する設計。
      - テスト容易性: _call_openai_api をモック差し替え可能。
    - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
      - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
      - ma200_ratio の算出は target_date 未満のデータのみ参照し、ルックアヘッドを防止。
      - マクロ記事はキーワードフィルタで抽出（複数キーワード一覧を定義）。
      - LLM 呼び出しは最大リトライ、API 失敗時は macro_sentiment=0.0 にフォールバック（例外を投げず継続）。
      - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - OpenAI クライアントは引数または環境変数 OPENAI_API_KEY で解決。
  - データプラットフォーム（src/kabusys/data）
    - ETL パイプラインインターフェース（src/kabusys/data/pipeline.py / etl.py）
      - ETLResult データクラスを提供。ETL 実行の取得数・保存数・品質問題・エラーを集約可能。
      - 差分更新・バックフィル・品質チェックを想定した設計（J-Quants クライアント経由での取得を想定）。
      - DuckDB を前提とした max date 取得・テーブル存在チェックなどのユーティリティを実装。
    - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
      - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB にデータが無い場合は曜日ベースのフォールバック（土日非営業日）。
      - カレンダーバッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得して保存、バックフィル、健全性チェックあり。
  - Research（src/kabusys/research）
    - ファクター計算（src/kabusys/research/factor_research.py）
      - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。
      - Volatility & Liquidity: 20 日 ATR, ATR/price, 20 日平均売買代金, 出来高比率。
      - Value: PER（price / EPS）、ROE（raw_financials から最新レコードを参照）。
      - DuckDB SQL を主体に実装、結果は (date, code) をキーとする辞書リストで返却。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns: デフォルト horizons=[1,5,21]）。
      - IC（Information Coefficient）計算（スピアマンの ρ をランク相関で算出）。
      - ファクターの統計サマリー（count/mean/std/min/max/median）。
      - ランク計算ユーティリティ（同順位は平均ランク）。
      - pandas 等に依存しない純標準ライブラリ + DuckDB 実装。
  - その他ユーティリティ
    - data/etl の ETLResult を public に再エクスポート（src/kabusys/data/etl.py）。
    - テスト容易性やルックアヘッドバイアス防止を意識した設計（datetime.today()/date.today() を直接参照しない処理が多い）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Internal / Notes
- OpenAI API 呼び出し時の耐障害性を重視（リトライ、5xx 判定、レスポンス JSON パース補強、フェイルセーフ値）。
- DuckDB に対する executemany の互換性（空リストバインドの回避）を考慮した実装。
- カレンダー・価格参照におけるルックアヘッド防止（target_date 未満／LEAD/ LAG の正しい使い方）を徹底。
- 外部 API キーや重要設定は環境変数で注入する設計。必要な環境変数が未設定の場合は早期に例外を出す（安全側）。

Security
- OpenAI キー等の敏感情報は環境変数で管理することを想定。自動 .env ロード機能があるため、.env ファイルの取り扱いには注意すること。

How to upgrade / migration notes
- v0.1.0 は初期実装。今後のメジャー変更で API 署名（関数名・戻り値の形式・DB スキーマ）や環境変数名が変わる可能性あり。アップグレード時は CHANGELOG の該当バージョンを確認してください。

問い合わせ
- 不明点や誤りの指摘はリポジトリの Issue を立ててください。