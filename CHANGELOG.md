# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog に準拠しており、セマンティックバージョニングを採用しています。

- リリース日付はコミット時点の推定値です。
- ここに列挙されている内容はコードベースから推測してまとめたものであり、実装の意図や設計方針（フェイルセーフやルックアヘッドバイアス回避等）も反映しています。

## [Unreleased]

（今後の変更をここに記述）

---

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買プラットフォームのコアライブラリ群を実装・公開しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージエントリポイント
  - kabusys パッケージを定義（src/kabusys/__init__.py）。バージョンは `0.1.0`。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を安全に読み込むユーティリティを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml による探索）により CWD に依存しないロードを実現。
  - .env/.env.local を読み込む際の優先度制御（OS 環境変数保護、.env.local による上書き対応）。
  - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、行末コメント処理などを考慮した .env パーサを実装。
  - 自動ロード無効フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD の導入（テスト等で利用可能）。
  - Settings クラスを公開（各種必須設定の取得・妥当性チェック）：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- AI 関連 (src/kabusys/ai)
  - ai パッケージのエントリ（news_nlp.score_news を公開）。
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）を実装：
    - OpenAI（gpt-4o-mini）の JSON Mode を用いた銘柄別センチメント評価。
    - 対象時間ウィンドウ（JST 基準：前日 15:00 ～ 当日 08:30）を計算する calc_news_window。
    - raw_news + news_symbols から銘柄ごとに記事を集約（記事数・文字数のトリム制御）。
    - 1 API 呼び出しで最大 20 銘柄をバッチ送信（_BATCH_SIZE）。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の整合性、スコアの数値化・有限値チェック）。
    - スコアの ±1.0 クリッピング。
    - DuckDB への冪等書き込み（該当 date と code を DELETE → INSERT）仕様、executemany の空リスト問題への対応。
    - テスト容易性のため _call_openai_api を分離してモック可能に実装。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）を実装：
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュースはタイトルをキーワード検索で抽出（マクロキーワードリストを定義）。
    - OpenAI 呼び出しによる macro_sentiment を取得し、失敗時は 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成・閾値判定・market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出し用に独立した _call_openai_api 実装（モジュール間結合を避けるため news_nlp とは別実装）。
    - API レート制限や 5xx を考慮したリトライ・バックオフを実装。

- データ基盤 (src/kabusys/data)
  - カレンダー管理（src/kabusys/data/calendar_management.py）を実装：
    - market_calendar テーブルの存在確認、データ有無判定、曜日ベースのフォールバック（market_calendar が未取得でも動作）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の提供。
    - 夜間更新ジョブ calendar_update_job：J-Quants クライアント経由で差分取得 → 保存（バックフィル・健全性チェックを含む）。
    - 検索範囲上限（_MAX_SEARCH_DAYS）やバックフィル（_BACKFILL_DAYS）、先読み（_CALENDAR_LOOKAHEAD_DAYS）等の制御。

  - ETL パイプライン補助（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題とエラーの収集）。
    - 差分更新・バックフィル、J-Quants クライアントとの連係、品質チェックの設計方針を実装（pipeline モジュールのインターフェース）。
    - DuckDB のテーブル最大日付取得などのユーティリティを実装。

- リサーチ機能 (src/kabusys/research)
  - factor_research.py：
    - モメンタム（1M/3M/6M リターン、ma200 偏差）、ボラティリティ（20日 ATR・相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）等のファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、date/code ごとの結果を辞書リストで返却。
    - データ不足時の None 取り扱い、ログ出力あり。
  - feature_exploration.py：
    - 将来リターン計算（calc_forward_returns）。複数ホライズン対応、入力検証（horizons の制約）。
    - IC（Information Coefficient）計算（calc_ic）：ランク相関（Spearman）を再現するためのランク付けと計算を実装。
    - 統計サマリー（factor_summary）とランク化ユーティリティ（rank）。

- 内部実装上の設計方針（全体）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接スコア計算に使用しない設計（target_date を引数に取る関数群）。
  - API 呼び出しは失敗時にシステム全体を停止させないフェイルセーフ（API 失敗時は 0.0 やスキップで継続）。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 想定）。
  - テスト容易性を考慮し、外部呼び出し（OpenAI 呼び出し等）をモック可能に実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の注意点 / 設計上の制約
- OpenAI 依存部分は API キー（OPENAI_API_KEY）に依存。未設定の場合は ValueError を発生させる設計。
- DuckDB の executemany は空リストを受け付けないバージョン依存の注意点が存在し、空の場合は実行しない安全策を実装済み。
- calendar_update_job などは外部 J-Quants クライアント（kabusys.data.jquants_client）に依存しており、実行には外部 API クレデンシャルやネットワークアクセスが必要。
- news_nlp/regime_detector の LLM 呼び出しは gpt-4o-mini を使用するプロンプト設計だが、将来的にモデル名や API 仕様変更があり得る。

---

Developers: この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートや利用上の注意（API キーの配布方法、db スキーマ、外部依存バージョン等）は別途プロジェクトのリリース手順書やドキュメントに追記してください。