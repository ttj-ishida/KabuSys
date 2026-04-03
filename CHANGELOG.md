# CHANGELOG

すべての注目すべき変更はここに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-03

初期リリース。日本株自動売買・データ基盤・リサーチ向けのコアユーティリティ群を実装しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルから data, strategy, execution, monitoring 等を公開する構成を用意。
  - バージョン情報: 0.1.0

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出は .git / pyproject.toml を参照）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理）。
  - 読み込み時の上書き制御（override）と保護キーセット（protected）をサポート。OS 環境変数を保護する仕組みを導入。
  - Settings クラスを追加し、以下の設定をプロパティで提供:
    - J-Quants / kabuステーション / LINE API の認証関連設定
    - データベースパス (duckdb, sqlite) のデフォルト
    - 監視用ファイルパス（pid / kill flag）および kill flag の開始時クリア挙動
    - CPU / メモリ / ディスク閾値のデフォルト
    - 環境（development / paper_trading / live）とログレベル検証
    - is_live / is_paper / is_dev の簡易判定プロパティ
  - 必須環境変数未設定時に _require が ValueError を送出。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - target_date に対するニュース収集ウィンドウ計算関数 calc_news_window を実装（JST 基準、DB は UTC 前提）。
    - raw_news / news_symbols を集約して銘柄ごとに記事を統合し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを取得する score_news を実装。
    - バッチ処理（最大 20 銘柄／回）、記事数・文字数のトリミング、JSON レスポンスのバリデーション、スコア ±1.0 でクリップ。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフ、API 失敗時は個別チャンクをスキップして残り継続するフェイルセーフ設計。
    - DuckDB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存スコアを保護。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - マクロニュースの抽出（キーワードベース）、OpenAI 呼び出し、スコア合成（重み: MA 70% / マクロ 30%）、クリップ、閾値判定を実装。
    - DB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない／未登録日は曜日ベース（平日のみ営業）でフォールバック。DB 登録値優先の一貫した挙動。
    - 夜間バッチ calendar_update_job を実装。J-Quants API から差分取得し保存、バックフィル・健全性チェック機能付き。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧を保持）。to_dict によるシリアライズを提供。
    - 差分取得、バックフィル、品質チェックの設計方針とユーティリティ関数を実装。
    - etl モジュールから ETLResult を再エクスポート。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を DuckDB SQL で計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - DuckDB のウィンドウ関数を利用した実装で、結果は (date, code) をキーとした dict のリストで返却。
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の妥当性検査を実装。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算する実装。データ不足や同順位処理を考慮。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装。

- 共通実装・設計上の注意点
  - DuckDB を主要なローカル DB として利用。
  - AI 関連は gpt-4o-mini を利用する想定で JSON mode を利用した厳密なパースを行う。
  - API 呼び出しは特定の例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対するリトライ戦略を実装。
  - 多くの処理で「look-ahead バイアス防止」のため datetime.today() / date.today() を内部参照せず、target_date 引数ベースで処理を行う設計。
  - テスト容易性を考慮し、外部 API 呼び出しを差し替え可能に設計（関数単位での patch を想定）。
  - DuckDB のバージョン差異（ex: executemany に空リストを渡せない問題）を考慮した防御的実装。

### 修正 (Fixed)
- （初期リリースのため特定の「修正」はなし。設計上のフォールバック・例外処理を多数実装して堅牢性を確保。）

### 変更 (Changed)
- （初回リリースのため履歴上の変更はありません。）

### 既知の注意点 (Notes)
- OpenAI API キーが必須な機能（score_news, score_regime）では、api_key 引数か OPENAI_API_KEY 環境変数のいずれかを設定する必要があります。未設定時は ValueError が発生します。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境設定することを推奨します。
- DuckDB スキーマ（テーブル名やカラム）が前提になっているため、既存データベースの構造に一致することが必須です。
- AI 呼び出しは外部 API（OpenAI）に依存するため、レート制限やサービス障害時は部分的にスコアが得られない挙動になります（フェイルセーフとしてスコアはスキップまたは 0.0 にフォールバック）。

--- 

開発上の詳細（設計方針、SQL クエリの意図、テストフック等）は各モジュールの docstring および実装コメントを参照してください。