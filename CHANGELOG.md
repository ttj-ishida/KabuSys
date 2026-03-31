Keep a Changelog
================

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを使用します。

[Unreleased]
------------

なし（初期リリースのみ）

0.1.0 - 2026-03-31
-----------------

Added
- 初回公開リリース。
- パッケージ基礎
  - kabusys パッケージの公開インターフェースを追加（__version__ = "0.1.0"、__all__）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルートの自動検出は .git または pyproject.toml を基準に探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサー実装:
    - 空行・コメント行の無視、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い。
    - クォートなし時の '#' の扱い（直前が空白/タブならコメントとみなす）。
  - Settings クラスを提供し、各種必須値（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）とデフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）をプロパティ経由で取得。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許可値制限）、実行環境判定ユーティリティ（is_live / is_paper / is_dev）。
- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント（score_news）
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 対象日の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して比較）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1 銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レスポンスの堅牢なバリデーション（JSON 抽出・results リスト・code/score 検証・スコアの数値変換・±1.0 クリップ）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。致命的でないケースはスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）し、部分失敗時に既存データを保護。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込む。
    - マクロニュースは news_nlp.calc_news_window と raw_news からフィルタ（マクロキーワード一覧）し、OpenAI（gpt-4o-mini）で評価。
    - LLM 呼び出しは失敗しても macro_sentiment=0.0 として継続。DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に更新。
    - ルックアヘッドバイアス防止の設計（date 未満のデータのみ使用、datetime.today() を参照しない）。
  - OpenAI 呼び出しの内部ラッパーを実装（テスト用に差し替え可能）。
- データプラットフォーム（kabusys.data）
  - 市場カレンダー管理（calendar_management）
    - market_calendar テーブルの有無に応じた営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB データ優先、未登録日は曜日ベースのフォールバック。探索は _MAX_SEARCH_DAYS により制限。
    - 夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants から差分取得して冪等保存（バックフィル／健全性チェックを含む）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー等を格納）。
    - 差分更新・バックフィル・品質チェックを想定した構成（jquants_client 経由での取得と保存、quality モジュールによる検査を想定）。
  - etl モジュールで ETLResult を再エクスポート。
- Research（kabusys.research）
  - factor_research
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）などのファクター計算を DuckDB に対する SQL / Python ベースで実装。
    - 各ファクターは prices_daily / raw_financials のみ参照し、本番取引 API にはアクセスしない設計。
    - 計算は (date, code) をキーとした dict のリストで返却。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、統計サマリー（factor_summary）、rank ユーティリティを実装。
    - 外部ライブラリへ依存せず標準ライブラリのみで実装。
- 内部的な堅牢性・設計上の配慮
  - ルックアヘッドバイアス対策: datetime.today() / date.today() を関数内部で直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB の executemany に対する互換性配慮（空リストバインド回避）。
  - OpenAI API のリトライロジックと 5xx 判定の扱い、JSON モードでも前後余計なテキストが混在する場合の復元ロジックなど、実運用での堅牢性を重視。
  - ロギングを各モジュールに実装し、警告・情報ログで問題の可視化を行う。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI の API キーは直接コードに埋め込まず、api_key 引数または環境変数 OPENAI_API_KEY を利用する設計。
- .env 自動読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Known limitations
- OpenAI に関する動作は gpt-4o-mini（JSON Mode）を前提としているため、将来的なモデル変更や API 仕様の変更に影響を受ける可能性がある。
- jquants_client, quality モジュールや外部 API の実体は本ツリーに含まれない想定（依存実装が必要）。
- DuckDB バージョン差分により SQL バインド方式や型挙動が変化する可能性があるため、本番導入時は動作確認を推奨。
- ai スコア/レジーム判定はフェイルセーフ設計だが、LLM の不安定さや API 呼び出し制限により一部銘柄が未スコアになる場合がある。

作者
- KabuSys チーム

（以上）