CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。
安定バージョンに関してはセマンティック バージョニングを使用します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-03
--------------------

Added
- 初期リリース。KabuSys 日本株自動売買システムの基礎機能を実装。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - top-level __all__ に data, strategy, execution, monitoring を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を提供。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルートの検出は __file__ を基準に .git または pyproject.toml を探索（配布後も CWD に依存しない実装）。
  - .env パーサ実装:
    - コメント行 / 空行の無視、export KEY=val 形式の対応。
    - シングル・ダブルクォート中のバックスラッシュエスケープ処理、インラインコメントの扱い。
    - クォートなし値では '#' の前にスペース/タブがある場合をコメント開始と認識。
  - _load_env_file による安全な読み込み（エンコーディング・I/O エラー時の警告処理）。
  - Settings クラスを公開（settings インスタンス）。
    - J-Quants / kabuステーション / LINE / DB / 監視 / システム設定のプロパティを提供。
    - 必須環境変数未設定時は ValueError を送出する _require を実装。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL 値検証を実装。
    - Path を返すプロパティは expanduser() を適用。
    - 監視用の閾値やフラグ（CPU/MEM/DISK の閾値、PID/KILL フラグパス等）を設定可能。

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事のセンチメントスコアリング機能を実装。
    - タイムウィンドウ計算（JST ベース → UTC naive datetime で処理）。
    - raw_news / news_symbols から銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
    - 銘柄チャンク単位（デフォルト 20 銘柄）で OpenAI Chat Completion（gpt-4o-mini, JSON mode）へ送信。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx を指数バックオフで再試行）。
    - レスポンス検証: JSON パース回復ロジック、"results" キー/要素チェック、スコア数値化、既知コード以外の無視、±1.0 でクリップ。
    - 処理後は ai_scores テーブルへ冪等的に置換（該当コードのみ DELETE → INSERT）。
    - API キー注入オプション（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
    - テスト容易性のため _call_openai_api を切り替え可能としている（unittest.mock などで差し替え）。
  - regime_detector: 市場レジーム判定（bull/neutral/bear）を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を統合。
    - マクロニュースは news_nlp の calc_news_window を使用して抽出し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - API 呼び出しのリトライ、API 失敗時は macro_sentiment = 0.0 でフェイルセーフ。
    - スコア合成後に market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - API キー注入オプション（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- データ基盤モジュール (kabusys.data)
  - calendar_management: JPX カレンダー管理と営業日判定機能を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar テーブルが存在しない場合は曜日ベースのフォールバック（週末を休業日扱い）。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した動作を確保。
    - calendar_update_job: J-Quants API からカレンダー差分を取得して market_calendar を冪等的に更新。バックフィルや健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl 経由でも再エクスポート）。
    - ETL の設計方針に基づく差分取得 / 保存 / 品質チェックフローを実装（jquants_client / quality と連携を想定）。
    - テーブル存在チェックや最大日付取得等のユーティリティを用意。
    - デフォルトの backfill や calendar lookahead の定数を設定。

- リサーチモジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタム指標を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の計算。
    - 実装は DuckDB 上の SQL ウィンドウ関数を活用し、必要行数不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 指定基準日から複数ホライズンの将来リターンを一括取得する汎用処理を実装。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を実装。データが不足すると None を返す。
    - rank: 同順位は平均ランクとするランク変換を実装（丸めで ties の判定安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能を実装。
  - research パッケージの __all__ に主要関数をエクスポート。

Other notable details
- DuckDB を主要なローカル DB として利用する設計。関数群は DuckDB 接続を受け取り SQL と Python を組み合わせて処理する。
- 日付操作はすべて date/datetime オブジェクトで扱い、datetime.today() / date.today() の不適切な参照によるルックアヘッドバイアスを避ける設計方針を明記。
- 外部 API 呼び出し（OpenAI / J-Quants 等）は失敗時に例外直撃で停止しないようフェイルセーフやログ出力、部分的な結果保持を重視した実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- 一部モジュール（jquants_client 等）は参照されているが本差分では実装の詳細を含まない（外部クライアントとして依存）。
- news_nlp / regime_detector は OpenAI の JSON mode を利用するため、利用時は対応する API とモデルの可用性に依存する。
- DuckDB バージョン差異により executemany の空リストバインドが不安定なため、空チェックを挟む実装がある（互換性対応）。

---