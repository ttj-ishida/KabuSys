# CHANGELOG

すべての注目すべき変更点を記載します。このプロジェクトは Keep a Changelog の慣習に準拠します。  
初版の内容は、ソースコードから推測した機能・設計意図に基づいて記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初期リリース。プロジェクトのコア機能群を実装しました。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。公開モジュール: data, strategy, execution, monitoring（__all__ に列挙）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env および環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途向け）。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索する方式で実装。
  - .env パーサーは以下の仕様をサポート:
    - コメント行（#）と export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - クォート無しの値で # をコメントとみなす際の文脈判定
    - 読み込み時に既存 OS 環境変数を保護する機能（protected set）
  - Settings クラス提供（settings インスタンスをエクスポート）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティ
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス（data ディレクトリ）
    - KABUSYS_ENV (development / paper_trading / live) と LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev の便捷プロパティ

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores に書き込む処理を実装。
    - スコアリングの時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリを実行）。
    - バッチ処理: 最大 20 銘柄／回、1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON-mode を使用、レスポンスのバリデーションと厳密なパースを実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフを実装。
    - 部分失敗時でも他銘柄の既存スコアを消さない（個別 DELETE → INSERT の冪等保存）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
    - パブリック API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei 225 連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロキーワードで raw_news をフィルタして最大 20 記事を LLM に送信して macro_sentiment を算出（API失敗時は 0.0 にフォールバック）。
    - レスポンスパース・OpenAI エラー処理（リトライ／5xx 判定）を実装。
    - DuckDB に対して冪等に market_regime レコードを書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - パブリック API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 約1か月/3か月/6か月リターンと ma200 乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER, ROE（raw_financials から target_date 以前の最新財務データを取得）。
    - 不足データ時には None を返す設計（安全性重視）。
    - DuckDB を用いた SQL ベース実装で外部 API への依存なし。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）。デフォルト horizons=[1,5,21]、ホライズン検証あり。
    - IC（Information Coefficient）計算（calc_ic）：Spearman のランク相関（ランクは平均順位の tie 処理）。
    - ランク付けユーティリティ（rank）。
    - ファクター集計サマリー（factor_summary）：count/mean/std/min/max/median を計算。
    - pandas 等に依存せず、標準ライブラリ + DuckDB のみで実装。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがある場合は DB 値を優先、無い日付は曜日ベース（土日非営業日）でフォールバック。
    - カレンダー更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得して保存（バックフィル、健全性チェック、ON CONFLICT 相当の保存）。
    - 探索上限 (_MAX_SEARCH_DAYS) を導入して無限ループを防止。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開（ETL 実行結果の集約）。
    - 差分取得・保存・品質チェックの設計に基づくユーティリティを実装。J-Quants クライアントとの連携を想定。
    - バックフィルや最小データ日付 (_MIN_DATA_DATE) などの設定。
    - 品質チェックはエラーを集約して ETL を継続する設計（Fail-Fast ではない）。
    - jquants_client, quality モジュールを利用する設計で、保存処理は冪等化を前提。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーや外部トークンは環境変数での提供を想定。設定が無い場合は明確なエラー（ValueError）を発生させる箇所を用意。
- .env 自動ロードでは OS 環境変数を保護する仕組みを導入（上書き防止）。

### 注記 / 実装上の設計意図（重要）
- ルックアヘッドバイアス防止: AI モジュールやリサーチモジュールの全てで datetime.today() / date.today() を直接参照しない（外部から target_date を渡す設計）。
- テスト容易性: OpenAI 呼び出し部分は patch による差し替えを想定して設計（ユニットテストでモックしやすい）。
- フェイルセーフ: 外部 API の失敗時は例外を崩壊させずフェイルセーフなデフォルト（例: macro_sentiment=0.0、スコア取得失敗はスキップ）を採用。
- DuckDB ベース: データ処理・集計は DuckDB 上で SQL を主体に実装。executemany の空リスト取り扱い等、DuckDB の挙動に配慮した実装。

### 既知の前提 / 要求
- OpenAI API（gpt-4o-mini）の利用には OPENAI_API_KEY が必要（score_news / score_regime は未設定時に ValueError を送出）。
- J-Quants 連携機能は jquants_client を経由する前提（JQUANTS_REFRESH_TOKEN 等の環境変数が必要）。
- DuckDB / raw_news, prices_daily, raw_financials, market_regime, ai_scores, news_symbols など所定のテーブルが存在することを前提に動作。

---

（今後のリリースでは各機能の安定化、ユニットテストの追加、監視/実行モジュールの実装詳細、パフォーマンス改善・エラーハンドリング強化等を記載予定です。）