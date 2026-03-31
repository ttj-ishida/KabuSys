CHANGELOG
=========
すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージエントリポイント: src/kabusys/__init__.py に __version__ と公開モジュールリストを設定。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
  - .env のパース機能（export 構文、クォート・エスケープ、インラインコメント対応）。
  - 環境変数保護（OS 環境変数を protected として上書き防止）。
  - Settings クラスを提供（J-Quants / kabu-station / Slack / DB パス / 監視閾値 / 環境種別 / ログレベル等のプロパティ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - env / log_level の入力検証（有効な値集合の定義）。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - calc_news_window: ニュース収集ウィンドウ（JST 基準 → UTC 変換）。
    - score_news: raw_news / news_symbols を集約し OpenAI（gpt-4o-mini, JSON mode）でセンチメントを取得、ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/回）、記事・文字数トリム、レスポンスバリデーション、スコアクリップ（±1.0）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - テスト用に _call_openai_api の差し替えを想定。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei225 連動 ETF）の 200 日 MA 乖離とマクロニュースの LLM センチメントを組み合わせ、日次で market_regime テーブルへ書き込み。
    - マクロニュースフィルタ（キーワードリスト）と OpenAI API 呼び出し、リトライ、フェイルセーフ（失敗時 macro_sentiment=0）。
    - スコア合成ロジック（重み付け: MA 70% / Macro 30%）とラベリング（bull/neutral/bear）。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。
- 研究用（research）モジュール（src/kabusys/research）
  - factor_research: calc_momentum / calc_volatility / calc_value（価格・財務データから複数ファクターを計算）。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（将来リターン、IC、統計サマリ等）。
  - zscore_normalize を data.stats から再エクスポート。
  - 実装方針: DuckDB 接続のみ使用、ルックアヘッドバイアス防止（date.today() 非参照）。
- データプラットフォーム（src/kabusys/data）
  - calendar_management: market_calendar テーブルを使った営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job（J-Quants からの差分フェッチと保存、バックフィル・健全性チェック対応）。
  - pipeline / etl: ETLResult データクラスと ETL パイプラインの骨組み（差分取得、保存、品質チェックの流れを想定）。
  - etl パッケージから ETLResult を再エクスポート。
  - 各所で DuckDB を前提とした SQL 実装と互換性配慮（executemany 空リスト対策等）。
- ロギングと設計上の配慮
  - 重要箇所での logger.info/debug/warning/exception による詳細なログ出力。
  - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - OpenAI API キーの注入（引数経由）をサポートし、テスト容易性を確保。

Security
- API キーやトークンは環境変数から取得する設計。config モジュールで必須パラメータ未設定時に ValueError を投げることで、秘密情報の未設定を検知可能に。

Changed
- 初回リリース — 変更履歴なし。

Fixed
- 初回リリース — 修正履歴なし。

Removed
- 初回リリース — 削除履歴なし。

Deprecated
- 初回リリース — 廃止予定の機能なし。

Known issues / Notes
- src/kabusys/data/pipeline.py の末尾付近に実装途上と思われる行（"return date.fro"）が存在します。これはタイポ／途中で切れたコードの痕跡であり、ETL 実行時に NameError/AttributeError を引き起こす可能性があります。意図としては date.fromisoformat 等を返す実装だったと推測されます。正式リリース前に該当箇所の修正が必要です。
- OpenAI 呼び出しは外部サービスに依存するため、実運用時は API クォータ・コスト・レイテンシに注意してください。
- DuckDB のバージョン差異（リスト型バインドの扱いなど）に対する互換性考慮が散見されます。実環境で使用する DuckDB バージョンで動作確認を行ってください。

Acknowledgements / Implementation notes
- OpenAI の呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用する設計。レスポンスの堅牢なパース・検証ロジックを実装しているため、多少の余計なテキスト混入にも耐性あり。
- モジュール間の結合を低く保つため、AI 関連の内部ユーティリティ（_call_openai_api 等）はモジュール毎に独立して実装されています（テスト時にパッチして差し替え可能）。

--------------------------------------------------------------------------------
（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時は差分履歴（git log 等）を参照し、リリース日・変更の責任者・チケット番号等を追加してください。）