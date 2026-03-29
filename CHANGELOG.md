# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
慣習: 重要な変更はカテゴリ（Added, Changed, Fixed, Security など）ごとにまとめています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能を実装しました。以下は主要な追加点・設計上の注意点です。

### Added
- パッケージ基盤
  - パッケージ情報 (src/kabusys/__init__.py) を追加。バージョン = 0.1.0。
  - 公開サブパッケージ候補として data, strategy, execution, monitoring を列挙。

- 設定 / 環境読み込み（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テストで有効）。
  - export KEY=val 形式、シングル／ダブルクォート、エスケープ、行内コメントなど多様な .env 記法のパース処理を実装。
  - override / protected（OS 環境変数保護）オプション付き .env 読込処理を実装。
  - Settings クラスを提供し、必要な環境変数取得メソッドを実装：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック（未設定時は ValueError を送出）。
    - デフォルトの API ベース URL、デフォルト DB パス（DuckDB / SQLite）を提供。
    - KABUSYS_ENV（development/paper_trading/live）の値検証とログレベル検証、is_live / is_paper / is_dev の便利プロパティ。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols テーブルを対象に、銘柄ごとのニュース統合センチメントを計算して ai_scores テーブルへ書き込む score_news 関数を実装。
  - JST ベースのニュース収集ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST）を実装（calc_news_window）。
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出すバッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数・文字数トリミング、レスポンスバリデーションを実装。
  - リトライポリシー（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフ、失敗時のフェイルセーフ（スキップして継続）を実装。
  - DuckDB への冪等的書込み（DELETE → INSERT、executemany を使用）を実装。部分失敗時に他銘柄データを保護する設計。

- マーケットレジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存する score_regime を実装。
  - DuckDB から ma200_ratio を計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
  - マクロニュースは news_nlp.calc_news_window に基づくウィンドウで抽出し、OpenAI により JSON で macro_sentiment を取得。
  - API 失敗時は macro_sentiment = 0.0 のフェイルセーフ、レスポンスパース失敗時も 0 にフォールバック。
  - レジームスコア合成時にクリップ処理を行い、market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- 研究用モジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）などを計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER・ROE を計算（PBR 等は未実装）。
    - いずれも DuckDB の prices_daily / raw_financials のみ参照し、ルックアヘッドバイアスに配慮。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得するクエリを実装。
    - calc_ic: スピアマンランク相関（IC）をコード結合して算出する実装（有効レコードが 3 件未満なら None を返す）。
    - rank: 同順位は平均ランクを返す実装（浮動小数誤差対策に round）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを実装。
  - research/__init__.py で主要関数を再エクスポート。

- データ管理（src/kabusys/data/*）
  - calendar_management:
    - market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録あり → DB 値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチ処理（バックフィル、健全性チェック、API エラー処理を実装）。
  - pipeline:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー情報を保持）。to_dict によるシリアライズを提供。
    - ETL 用ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
  - etl.py で ETLResult を公開再エクスポート。

- 汎用設計 / テスト対応
  - OpenAI 呼び出し（_call_openai_api）は各モジュールで独立実装し、テスト時に unittest.mock.patch で差し替え可能。
  - DuckDB を前提とした SQL 実装で、executemany に空リストを渡さない等の互換性対応を行った。
  - ルックアヘッドバイアス対策: date/datetime の参照を関数引数ベースに限定（内部で date.today()/datetime.today() を参照しない設計）。

### Changed
- （初版のため変更履歴はなし）

### Fixed
- （初版のため修正履歴はなし）

### Security
- 環境変数チェックを厳格化（必須トークン未設定時は明示的にエラーを投げる）。.env の読み込みで OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Implementation details
- 多くの処理は DuckDB（ローカル分析 DB）を前提に実装されています。実行前に適切なテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が存在することが必要です。
- OpenAI API の利用は JSON Mode（response_format={"type":"json_object"}）を前提としており、レスポンスの堅牢なパース・バリデーション処理を実装しています。API エラーは再試行・ログ出力の上で安全にフォールバックしますが、実運用時は API キー管理やコスト制御に注意してください。
- 一部モジュール（jquants_client 等）は参照されますが、このリリースでは外部クライアント実装は含まれていないため、実運用環境では適切な実装またはモックの提供が必要です。

---

将来的なリリースでは以下を検討しています（TODO）:
- strategy / execution / monitoring の具現化とテスト。
- ai モジュールのモデル切替やローカルモデル対応。
- ETL のスケジューリング・監査ログ強化。
- テストカバレッジの追加（ユニット・統合テスト）。