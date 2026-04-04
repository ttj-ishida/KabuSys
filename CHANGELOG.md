CHANGELOG
=========

すべての注目すべき変更は本ファイルに記載します。  
フォーマットは Keep a Changelog に準拠しています。

0.1.0 - 2026-04-04
------------------

Added
- 初回リリース。日本株自動売買プラットフォームのコア機能群を追加。
- パッケージ公開情報
  - pakage バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装（コメント対応、export KEY=val 形式対応、クォート内のエスケープ処理対応）。
  - デフォルト値・取得メソッドを持つ Settings クラスを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 経由での利用想定）。
  - 各種監視閾値（CPU/MEMORY/DISK）や DB パス、PID/KILL フラグの設定を環境変数経由で取得可能。
  - env 値検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL（DEBUG/INFO/...）に対するバリデーションを実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news + news_symbols を集計して、銘柄単位のニューステキストを OpenAI (gpt-4o-mini) の JSON Mode でセンチメント評価。
    - バッチ処理（最大 20 銘柄／チャンク）、1 銘柄あたり最大記事数・文字数でトリム。
    - リトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）とレスポンス検証を実装。
    - レスポンス検証: JSON 抽出・"results" リスト・各要素の code/score チェック・数値検証。スコアは ±1.0 にクリップ。
    - エラーや部分失敗時も他銘柄データを保護するため、ai_scores の置換は影響あるコードのみ DELETE → INSERT。
    - タイムウィンドウ: 対象日は「前日 15:00 JST 〜 当日 08:30 JST」を内部で計算（UTC naive datetime を DB クエリに使用）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（NIKKEI 225 連動型）200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュースは news_nlp のウィンドウ計算関数 calc_news_window を利用して抽出（最大 20 件）。
    - OpenAI 呼び出しは専用関数で行い、リトライ・エラーハンドリング（5xx/RateLimit/Timeout など）とフォールバック（失敗時 macro_sentiment=0.0）を実装。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - ルックアヘッドバイアス対策を設計目標に含む（date < target_date の排他条件を守るなど）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。

- リサーチ / ファクター群 (kabusys.research)
  - factor_research モジュール
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（calc_momentum）。
    - ボラティリティ / 流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比（calc_volatility）。
    - バリュー: PER、ROE を raw_financials と prices_daily から計算（calc_value）。EPS が 0/欠損時は None を返す。
    - 計算は DuckDB 上の SQL ウィンドウ関数を活用して効率的に実行。データ不足時は None を採用。
  - feature_exploration モジュール
    - 将来リターン計算 (calc_forward_returns)：複数ホライズン（デフォルト [1,5,21]）に対応、ホライズンは営業日単位で検証。
    - IC 計算 (calc_ic)：スピアマンのランク相関（ランクは同順位を平均ランクで処理）を実装。有効レコードが 3 件未満なら None。
    - rank, factor_summary（count/mean/std/min/max/median）などのユーティリティを提供。
  - 研究用 API はすべて prices_daily / raw_financials などの DB テーブルのみを参照し、外部発注や本番 API へアクセスしない設計。

- データ基盤 (kabusys.data)
  - calendar_management モジュール
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得時のフォールバックは曜日ベース（土日非営業日）。
    - DB 登録値優先で未登録日は曜日フォールバックし、API からの差分取得・バッチ更新ジョブ（calendar_update_job）を実装。取得は J-Quants client 経由。
    - update ジョブはバックフィル（直近 _BACKFILL_DAYS を再取得）と健全性チェック（未来日付の異常検出）を実装。
  - ETL / pipeline モジュール
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプライン設計: 差分更新、idempotent 保存（ON CONFLICT DO UPDATE）、品質チェックの収集（quality モジュール）を想定。
    - デフォルトのバックフィルとカレンダー先読みを設定し、安全な ETL 実行を重視。

Changed
- （初版のため履歴上の変更なし）

Fixed
- （初版のため履歴上の修正なし）

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス回避: すべての日付ロジックは target_date を明示的に受け取り、date.today()/datetime.today() に依存しない実装を心がけています。DB クエリでは target_date の「未満 / 以上 / 排他」などの条件を適切に使用しています。
- フェイルセーフ: OpenAI 等の外部 API 呼び出し失敗時は基本的に例外を上位へ投げず（ただし明示的な必須キー未設定は ValueError）、スコアやセンチメントは中立（0.0 や None）にフォールバックして処理を継続します。これにより ETL / 日次バッチの停滞を防止します。
- 冪等性: DB 書き込みは可能な限り冪等な操作（DELETE → INSERT、ON CONFLICT）またはトランザクションで保護して実装しています。
- DuckDB 互換性: executemany の空リストバインド制約（DuckDB 0.10 系）を考慮し、空リストは事前にチェックしてから実行しています。
- OpenAI 呼び出し: 現時点で gpt-4o-mini と JSON Mode を利用する設計。テスト容易性のため _call_openai_api をモック可能に分離しています。

Security
- OpenAI API キーや外部 API トークンは環境変数で取り扱う設計。Settings 経由での取得を推奨します。
- .env 自動ロードは OS 環境変数を上書きしない保護（protected set）を行い、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

今後の TODO / 想定追加
- Strategy / Execution / Monitoring の具体的実装と統合テストの追加。
- ai モジュールのレスポンス・プロンプト改善やセーフガード（トークン量制限、プロンプト長最適化）の強化。
- ETL の詳細実装（jquants_client 経由の差分取得処理、quality モジュールのルール実装）と監査ログの充実。

ライセンス、貢献、その他はリポジトリの README を参照してください。