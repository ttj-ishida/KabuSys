# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買プラットフォームのコアライブラリを追加します。主にデータ取得・ETL・カレンダー管理・ファクター計算・AIベースのニュース解析と市場レジーム判定・環境設定ユーティリティを含みます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数からの設定読み込みを実装。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - .env のパース機能を強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - コメント処理（クォート外での '#' 処理のルール）対応。
  - .env と .env.local の読み込み優先度: OS環境変数 > .env.local > .env。.env.local は上書き（override=True）。
  - OS 環境変数の保護（protected set）機能を実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを実装し、主要な設定プロパティを公開（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境判定、ログレベルなど）。
  - 設定値のバリデーション:
    - 必須キー未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック（不正な値は ValueError）。

- AI モジュール (src/kabusys/ai)
  - news_nlp モジュール:
    - raw_news + news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを算出して ai_scores テーブルへ保存する。
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたりの記事数・文字数上限、レスポンス検証ロジックを実装。
    - リトライ・バックオフ戦略（429、ネットワーク断、タイムアウト、5xx を対象）を備え、失敗時は対象銘柄をスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なパース・バリデーション（JSON 抽出、results の検証、コード照合、数値チェック、スコアクリッピング）。
    - テスト性のため OpenAI 呼び出し部分を patch 可能な private 関数で分離。
    - calc_news_window(target_date) により JST ベースのニュース収集ウィンドウを計算（ルックアヘッド回避）。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出用キーワードリスト、最大記事数制限、モデル gpt-4o-mini、JSON 応答パース、リトライ/バックオフを実装。
    - API 失敗時は macro_sentiment = 0.0 としてフェイルセーフ継続。
    - DB クエリは target_date 未満のみを参照し、ルックアヘッドバイアスを回避。
    - OpenAI 呼び出しは news_nlp と別実装で分離（モジュール結合を避ける設計）。

- データ関連 (src/kabusys/data)
  - calendar_management モジュール:
    - JPX カレンダー管理、is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar の有無により DB 値優先、未登録日は曜日ベースでフォールバック（土日非営業）。
    - 夜間バッチ calendar_update_job: J-Quants API から差分取得 → 冪等保存（ON CONFLICT 風の処理）、バックフィル・健全性チェックを実装。
    - 探索範囲上限 (_MAX_SEARCH_DAYS) により無限ループを防止。
  - pipeline / ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラス公開（ETL の集計結果・品質問題・エラー列挙）。
    - 差分取得・バックフィル・J-Quants クライアント呼び出し・品質チェック統合を想定した ETL 基盤を実装。
    - テーブル最大日付取得ユーティリティ等を提供。
    - jquants_client モジュールとの連携（fetch/save を前提）。
    - etl モジュールから ETLResult を再エクスポート。

- リサーチ / ファクター (src/kabusys/research)
  - factor_research:
    - モメンタム（1M/3M/6Mリターン、200日MA乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）などのファクター計算関数を実装（DuckDB SQL ベース）。
    - データ不足時の None 返し、ログ出力、集約結果を (date, code) キーの dict リストで返却。
    - 設計上、prices_daily / raw_financials のみ参照し外部副作用なし。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換ユーティリティ rank、統計サマリー factor_summary を実装。
    - スピアマン相関（ランク相関）による IC 計算、ties の平均ランク処理を含む実装。
    - pandas 等外部ライブラリに依存せず、標準ライブラリ + DuckDB を使用。

### 変更 (Changed)
- 初回公開のため該当なし。

### 修正 (Fixed)
- 初回公開のため該当なし。

### ドキュメント / 設計上の注意
- ルックアヘッドバイアス回避:
  - news_nlp / regime_detector / 各種計算は内部で datetime.today() / date.today() を直接参照しない（target_date を明示的に渡す設計）。
- OpenAI 呼び出し:
  - gpt-4o-mini を利用する想定。JSON Mode（response_format={"type": "json_object"}）を利用して厳密な JSON 応答を期待するが、パース頑健化処理あり。
  - リトライ / バックオフ戦略を実装。API の種類に応じてリトライ可否を分ける（RateLimit/ネットワーク/タイムアウト/5xx を再試行対象）。
  - テスト容易性のため、OpenAI 呼び出し箇所は private 関数で分離しモック可能。
- DB 書き込み:
  - 多くの書き込み処理で BEGIN / DELETE / INSERT / COMMIT の冪等書き込みパターンを採用。例外時は ROLLBACK を試行しログを出力。
  - DuckDB executemany の挙動に配慮（空リストバインド回避）。
- フェイルセーフ:
  - LLM/API 失敗時はゼロ値またはスキップして処理を継続する実装方針（運用で一部処理失敗しても全体が停止しない）。
- 必要テーブル（想定）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などを利用。

### 既知の制約 / 注意点
- Settings の必須環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出するため、運用前に .env を準備する必要があります（.env.example を想定）。
- OpenAI API キーは引数で注入可能（api_key 引数）になっているためテスト時は環境変数に依存せずに呼び出せます。
- news_nlp と regime_detector は共に OpenAI を使用するが、内部で呼ぶ private 関数実装を分離しており相互依存を避ける設計です。

---

今後のリリース案（例）:
- 「監視・実行モジュールの実装詳細」や「strategy モジュールの追加」「Slack通知・モニタリング統合」などの項目を予定。