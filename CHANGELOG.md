# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルは、提供されたコードベースから実装内容・設計意図を推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-04
初期リリース。日本株自動売買／リサーチ用ライブラリの基盤機能を実装。

### Added
- パッケージのエントリポイントとバージョン
  - kabusys.__version__ = 0.1.0、パッケージ公開用の __all__ を定義。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序と上書きルール: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - .env パーサーの実装:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理などを考慮。
  - 重要環境変数取得ユーティリティ `_require` を追加（未設定時は ValueError を送出）。
  - Settings クラスを実装し、J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供。
    - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値など）。
    - 監視用しきい値 (CPU/MEM/DISK)、PID / kill フラグパス、kill フラグの起動時クリアフラグ等をプロパティ化。

- AI 関連機能 (kabusys.ai)
  - ニュースセンチメント分析モジュール (kabusys.ai.news_nlp)
    - raw_news と news_symbols をもとに銘柄毎に記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたりの最大記事数・文字数トリム制御を実装。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、コード照合、数値検証、±1.0 クリップ）。
    - DuckDB への冪等書き込み戦略（部分失敗時に既存スコアを破壊しないため code を絞って DELETE→INSERT）。
    - テスト容易性のため OpenAI 呼び出し箇所に差し替え可能なポイントを提供（_call_openai_api の差し替え）。
    - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウを UTC naive datetime で返す）。
  - 市場レジーム判定モジュール (kabusys.ai.regime_detector)
    - ETF 1321（225連動）について 200 日移動平均乖離（重み 70%）とマクロ要因（LLM センチメント、重み 30%）を合成してデイリーで市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、OpenAI（gpt-4o-mini）でマクロセンチメントを取得。
    - API エラー・パース失敗時はフェイルセーフで macro_sentiment = 0.0 を採用。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）およびエラー時の ROLLBACK/ログ対応。
    - ルックアヘッドバイアス対策: target_date 未満のみのデータ参照、datetime.today() を参照しない設計。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理モジュール (calendar_management)
    - market_calendar テーブルを参照した営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録が無い場合の曜日ベースフォールバック（週末は非営業日扱い）を提供し、DB 登録ありの場合は DB 値を優先。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に保存（バックフィル、健全性チェックを実装）。
  - ETL パイプライン基盤 (pipeline)
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - テーブル存在チェック、最大日付取得などのユーティリティを用意。
    - デフォルトの差分更新方針、バックフィル挙動、品質チェックの扱い（重大度を返すが ETL を継続）を設計に反映。
  - パイプライン型の再エクスポート (etl)
    - ETLResult を外部公開インターフェースとして再エクスポート。

- リサーチ / ファクター群 (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）等の計算関数を実装。
    - DuckDB 上の SQL とウィンドウ関数を使った効率的な計算を行う。
    - データ不足時の None 処理、ログ出力を考慮。
  - feature_exploration モジュール
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（Spearmanランク相関）calc_ic、ランク変換 rank、統計サマリー factor_summary を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。ロバストな欠損/非有限値処理を含む。

### Changed
- （初版のため変更履歴はなし。実装時点の設計方針・フェイルセーフや互換性配慮を注記）

### Fixed
- （初版のため修正履歴はなし）

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組みを導入（読み込み時に protected set を用いて上書きを制御）。
- OpenAI API キー取得は明示的に引数で注入可能（テスト容易性）かつ環境変数（OPENAI_API_KEY）もサポート。未設定時は ValueError を送出して安全に停止。

### Notes / Implementation details
- DuckDB を主要なローカルデータストアとして使用。トランザクション（BEGIN/COMMIT/ROLLBACK）を用いて冪等性と整合性を保つ実装を行っている。
- LLM 呼び出しに対しては、JSON mode の利用、応答の堅牢なパース、クリップ処理、失敗時のフェイルセーフなど生産運用を考慮した実装を行っている。
- ルックアヘッドバイアス防止のため、すべての「date を基準にする」処理は target_date 引数を受け取り、現在時刻を直接参照しない方針で設計されている。
- テスト容易性のため、OpenAI API 呼び出し箇所をパッチ差し替え可能にしている（ユニットテストでのモックが容易）。

---

（注）この CHANGELOG は提供されたコードスニペットの内容から推測して作成したものであり、実際のリリースノートはプロジェクト運用方針に合わせて適宜調整してください。