CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
形式は「Keep a Changelog」に準拠します。

Unreleased
----------

- （今後の変更をここに記載）

0.1.0 - 2026-03-29
------------------

初回リリース。KabuSys のコア機能群を実装しています。主な追加点は以下の通りです。

Added
- パッケージ初期化
  - パッケージ version を `0.1.0` として公開（src/kabusys/__init__.py）。
  - サブパッケージとして data, research, ai, などのモジュール群をエクスポート。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動探索（CWD に依存しない）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルトの設定値: KABUSYS_ENV=development（有効値: development, paper_trading, live）、LOG_LEVEL=INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - DB パスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
  - 未設定の必須環境変数は ValueError を送出する挙動を採用。

- AI（自然言語処理）機能（src/kabusys/ai）
  - ニュースセンチメントスコアリング（score_news, src/kabusys/ai/news_nlp.py）
    - OpenAI（gpt-4o-mini）を用いたニュース記事の銘柄別センチメント解析。
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 参照）。
    - 銘柄ごとに最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄を1チャンクとしてバッチ送信（_BATCH_SIZE）。
    - JSON Mode を使用し厳格な JSON レスポンスを期待。レスポンスは検証・クリップ（±1.0）して ai_scores テーブルへ書き込み。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。その他のエラーはスキップして継続する（フェイルセーフ設計）。
    - テスト容易性のため OpenAI 呼び出しを _call_openai_api を通して差し替え可能（unittest.mock でモック可能）。
    - score_news は処理して DB に書き込んだ銘柄数を返す。API キー未設定時は ValueError。

  - 市場レジーム判定（score_regime, src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに日次判定を書き込む。
    - マクロ記事抽出のためのキーワードリストを内蔵（日本・米国・グローバルの主要語）。
    - OpenAI 呼び出しは JSON レスポンスを期待し、失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。リトライ実装あり。
    - 出力は regime_score をクリップしてラベル化（bull / neutral / bear）し、冪等的に market_regime に保存（BEGIN/DELETE/INSERT/COMMIT）。API キー未設定時は ValueError。

- 研究用ファクター計算（src/kabusys/research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE 結合で PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - いずれも DuckDB の prices_daily / raw_financials を参照し、結果は (date, code) をキーとする辞書リストを返す。
  - feature_exploration モジュール:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて計算。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効レコード < 3 の場合は None を返す）。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を算出。
  - 依存: pandas 等に依存せず標準ライブラリと DuckDB を使用。

- データプラットフォーム（src/kabusys/data）
  - calendar_management モジュール:
    - market_calendar を使った営業日判定 (is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days) を実装。DB にデータがない場合は曜日ベース（土日休）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新。バックフィルや健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETL パイプラインのユーティリティを実装（差分取得、バックフィル、品質チェックの考え方を実装方針として定義）。
    - DB 操作は冪等（DELETE→INSERT や executemany の扱い等）を意識した実装。
  - ユーティリティ: テーブル存在チェックや日付最大値取得などのヘルパーを提供。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 既知の制約・運用上の注意
- OpenAI API
  - AI 機能は OpenAI の利用を前提とします。API キーは引数で注入可能（テスト向け）か、環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。
  - 使用モデルは gpt-4o-mini。レスポンスは JSON Mode を前提とし、モジュール側で厳密なパースと検証を行いますが、LLM 側の出力不備はスキップやフォールバック（0.0 等）で安全に扱います。

- DB トランザクションと冪等性
  - market_regime / ai_scores 等への書き込みは明示的な BEGIN/DELETE/INSERT/COMMIT を使って冪等性を担保し、例外時には ROLLBACK を試行します。ROLLBACK が失敗した場合は警告ログを出力します。

- テストしやすさ
  - OpenAI 呼び出し点はモジュール内部の _call_openai_api を通しており、unittest.mock.patch による差し替えが想定されています。

- 自動 .env ロードの挙動
  - プロジェクトルートが見つからない場合は自動ロードをスキップします。
  - OS 環境変数は保護され、.env/.env.local の上書き対象から除外されます（.env.local は override=True で読み込み、ただし OS 環境変数に対しては上書きしない）。

依存関係（実行時に必要）
- duckdb
- openai (OpenAI SDK)
- 標準ライブラリ（datetime, json, logging 等）

今後の予定（例）
- AI モデルの入れ替えや追加パラメータ化（モデル選択の外部化）
- ETL の具体的なスケジューリング / 実行ラッパーの提供
- 監視・アラート機能（Slack 通知等）とモニタリング用 DB スキーマの拡充

--- 

この CHANGELOG はソースコードから推定して作成しています。実際のリリースノート作成時はリリース日、責任者、互換性ポリシーなどを正式に追記してください。