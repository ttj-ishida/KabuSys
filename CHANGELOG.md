# Keep a Changelog

すべての変更はセマンティックバージョニングに従います。  
このファイルはプロジェクトの主要な変更点を人間が読みやすい形で記録したものです。

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システム "KabuSys" の基幹モジュール群を追加しました。
主にデータ取得・ETL・マーケットカレンダー管理・ファクター算出・AI によるニュースセンチメント評価・設定管理を提供します。

### 追加
- パッケージ初期化
  - src/kabusys/__init__.py によるパッケージ定義（バージョン "0.1.0"）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（プレースホルダ含む）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env のパースは以下をサポート:
    - 空行 / コメント（#）行を無視
    - export KEY=val 形式に対応
    - シングル・ダブルクォートのエスケープ処理を考慮
    - インラインコメントのロジック（クォート有無で振る舞いを分離）
  - 読み込み優先順位: OS環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを提供（プロパティ経由で設定値を取得）:
    - J-Quants / kabuステーション / LINE / データベースパス / 監視閾値 等の設定項目
    - 環境値検証（KABUSYS_ENV の許容値チェック、LOG_LEVEL 検証）
    - 必須変数未設定時は明示的な ValueError を送出する _require 関数

- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとの記事を作成。
    - gpt-4o-mini を用いた JSON Mode 呼び出しで銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - チャンク処理（1 API コールで最大 20 銘柄）、1 銘柄は最大 10 記事・3000 文字にトリム。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ）。
    - レスポンスバリデーション（JSON 抽出、results 配列、既知コードチェック、数値確認）、スコアは ±1.0 にクリップ。
    - DB 書き込みは idempotent に実行（対象コードのみ DELETE → INSERT）。DuckDB の executemany 空リスト制約に対応。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - calc_news_window(target_date) を提供（JST ベースの収集ウィンドウを UTC naive datetime で返す）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - マクロキーワードフィルタで raw_news からタイトルを抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - LLM 呼び出しは独自実装でモジュール結合を避ける（news_nlp と共有しない）。
    - API エラー時は macro_sentiment=0.0 でフェイルセーフ継続。
    - レジームスコアは clip(-1..1)、計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - リトライ / バックオフ実装、API パラメータや閾値（MA ウェイト・スケール・閾値等）が定数化。

- 研究（Research）モジュール（src/kabusys/research/*）
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）
    - Volatility: 20日 ATR / ATR率、20日平均売買代金、出来高比率
    - Value: PER（EPS が 0/欠損のとき None）、ROE（raw_financials から取得）
    - DuckDB を用いた SQL 主導の実装。返却は (date, code) をキーとする dict のリスト。
    - データ不足時は None を返す扱い（安全設計）。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 指定 horizon（営業日）ごとの fwd_Xd を計算（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を独自実装で算出（ties は平均ランク）。
    - ランク関数（rank）: 同順位は平均ランク、浮動小数丸めで ties 取りこぼしを防止。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの値優先で営業日判定。未登録日は曜日（土日）フォールバック。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - 夜間バッチ更新 calendar_update_job: J-Quants API (jquants_client) から差分取得 → 保存（バックフィルと健全性チェックあり）。
    - 最大探索日数、ルックアヘッド、バックフィル日数、健全性チェック等を定数化。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を定義（取得件数、保存件数、品質問題、エラー一覧などを集約）。
    - 差分更新・backfill の方針、品質チェックの扱い（致命的問題が発生しても全件収集して呼び出し元に判断を委ねる）を実装方針として明文化。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
  - etl モジュールの公開インターフェース（src/kabusys/data/etl.py）で ETLResult を再エクスポート。

- テスト性・安全設計上の配慮（クロスモジュール）
  - LLM 呼び出し箇所はテストのため差し替え可能（unittest.mock.patch を想定）。
  - データ取得・スコアリング処理は datetime.today()/date.today() に依存しない設計（ルックアヘッドバイアス防止）。
  - DB 書き込みは冪等操作 / トランザクション（BEGIN/COMMIT/ROLLBACK）で行い、部分失敗時の既存データ保護を考慮。

### 変更
- （初回リリースのため、過去バージョンからの変更はありません）

### 修正
- （初回リリースのため既知のバグ修正はありません）

### 注意事項 / 既知の設計上の制約
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY にて指定する必要があります。未設定時は ValueError を発生させます。
- DuckDB に対する executemany の空リストバインド制約（バージョン依存）に対応するため、空パラメータのときは DB 操作をスキップするガードを入れています。
- news_nlp / regime_detector ともに gpt-4o-mini の JSON Mode を使用する前提の実装になっています。プロバイダ側の応答形式変更や SDK のバージョン差分に注意してください。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar に依存しています（外部クライアント実装が必要）。

---

将来的なリリースでは以下のような点を改善予定です（例）:
- strategy / execution / monitoring の具体実装（現状はパッケージ公開プレースホルダ）
- 追加の品質チェックルールやモニタリングアラートの強化
- AI モデルの選択肢拡張と応答検証の強化
- DuckDB スキーマの初期化ユーティリティとマイグレーション機能の追加

（以上）