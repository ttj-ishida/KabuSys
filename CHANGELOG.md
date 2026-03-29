# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日付は本リポジトリ内の __version__（0.1.0）および作成日（本日）に基づいています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29

導入:
このリリースは KabuSys の初期公開バージョンです。日本株自動売買システムのための以下主要サブシステムを実装しています：
- 環境設定管理（.env 自動読み込み）
- データ ETL とカレンダー管理（DuckDB ベース）
- ニュース NLP（LLM を使ったセンチメント評価）と市場レジーム判定
- リサーチ（ファクター計算・特徴量探索）
- テスト容易性・冪等性やフォールトトレランスを重視した設計

主要な追加（Added）
- パッケージ公開
  - パッケージメタ: kabusys.__version__ = 0.1.0
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__ に記載）

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱いを考慮
  - Settings クラスを提供（settings インスタンス）
    - 必須環境変数の検査（_require）
    - 主要設定プロパティ:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH, SQLITE_PATH（デフォルト値あり）
      - KABUSYS_ENV（development/paper_trading/live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルプ・エラーメッセージを明示的に出力

- データモジュール（kabusys.data）
  - calendar_management
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）
    - 営業日判定ユーティリティ群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB（market_calendar）が存在しない場合の曜日ベースフォールバック
    - 最大探索日数制限、バックフィル、健全性チェックの実装
  - pipeline / etl
    - ETLResult: ETL 実行結果を表す dataclass（品質問題とエラーを収集）
    - ETL パイプライン方針とユーティリティ（差分取得・バックフィル・品質チェックを想定）
    - テーブル存在チェック、最大日付取得などの内部ヘルパー実装
  - jquants_client と quality など外部クライアントを呼び出す想定（インターフェース設計）

- AI モジュール（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメント評価
    - ウィンドウ定義（前日15:00 JST ～ 当日08:30 JST を UTC に変換して扱う）
    - バッチ処理（1回あたり最大 20 銘柄）、1銘柄あたり記事と文字数のトリム制御
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）
    - レスポンス検証とクリッピング（±1.0）
    - DuckDB へ冪等書き込み（DELETE → INSERT、executemany の空チェック対応）
    - テスト容易性: _call_openai_api を patch して差し替え可能
  - regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定
    - ma200 計算（target_date 未満のデータのみ使用しルックアヘッドを防止）
    - マクロキーワードによる raw_news フィルタ、LLM 呼び出し、リトライ、フェイルセーフ（API失敗時 macro_sentiment=0.0）
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、ROLLBACK への安全処理）

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（cnt 200 未満は None）
    - calc_volatility: 20 日 ATR（atr_pct を含む）、20 日平均売買代金、出来高比率
    - calc_value: raw_financials から最新財務を取り PER/ROE を計算
    - DuckDB を用いた SQL ベース実装、欠損時の None 扱い
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）
    - calc_ic: ファクタと将来リターンのスピアマンランク相関（IC）計算
    - rank: 平均ランク（同順位は平均ランク）実装（丸めで ties の安定化）
    - factor_summary: count/mean/std/min/max/median の統計サマリー

品質・設計（Changed / Improved）
- ルックアヘッドバイアス対策
  - AI スコアリング・レジーム判定・ファクター計算はいずれも内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に渡して処理（検証・再現性を確保）
  - prices_daily クエリは date < target_date / date BETWEEN 範囲でルックアヘッドを回避
- フォールトトレランス
  - LLM 呼び出しの失敗は例外を投げずフェイルセーフなデフォルト（0.0 またはスキップ）にフォールバック
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、ROLLBACK に失敗した場合は警告ログを出力して上位へ例外伝播
- テスト支援
  - OpenAI 呼び出し箇所に対して _call_openai_api を分離、ユニットテストで差し替え可能

バグ修正（Fixed）
- 本初版リリースに際して既知のバグ修正履歴は無し（初期実装）

非互換（Breaking changes）
- なし（初期リリース）

セキュリティ（Security）
- 特にセキュリティ関連の緊急修正はなし。ただし以下に注意：
  - 必須トークンや API キー（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN 等）は環境変数で管理すること（.env を利用）
  - .env 自動読み込みはテスト等で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能

マイグレーション / 利用開始時の注意事項（Migration notes）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を設定してください。
- オプション環境変数:
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_DISABLE_AUTO_ENV_LOAD
- データベース（DuckDB）スキーマ:
  - このライブラリは以下のテーブルを前提にクエリを実行します。事前にスキーマを準備してください（ETL の save_* を利用して初期ロード可能）。
    - prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_regime, market_calendar
- OpenAI API:
  - news_nlp と regime_detector は OpenAI（gpt-4o-mini）を利用します。OPENAI_API_KEY を環境変数か関数引数で渡してください。
  - テスト時は kabusys.ai.*._call_openai_api をモック/パッチしてください。
- DuckDB の executemany に対する互換性:
  - DuckDB のバージョンによっては executemany に空リストを渡すとエラーになるため、空チェックを行ってから実行します。

内部仕様メモ（開発者向け）
- LLM 関連:
  - news_nlp: バッチサイズ _BATCH_SIZE=20、1銘柄あたり _MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000
  - regime_detector: ETF 1321 を対象、MA ウェイト 0.7、マクロウェイト 0.3、閾値等はコード内定数で管理
  - 両モジュールとも JSON mode を想定し、レスポンスのバリデーションと JSON 抽出ロジックを実装
- ログと警告:
  - 各所で logger を利用して情報・警告・例外を記録しています（テスト/運用監視に利用可能）
- トランザクション:
  - market_regime / ai_scores などは DELETE → INSERT の冪等操作をトランザクション内で行う

今後の予定（短期）
- ETL 実行スクリプトや CLI、db スキーマ定義ファイルの追加
- strategy / execution / monitoring サブパッケージの実装補完（現在は名前空間のみ公開）
- 追加の品質チェックルールとスキーマ検証ユーティリティ

---

著者: KabuSys 開発チーム  
初版リリース: 0.1.0 (2026-03-29)