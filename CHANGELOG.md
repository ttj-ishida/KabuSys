# CHANGELOG

すべての重要な変更を Keep a Changelog 準拠で日本語で記載します。

フォーマット:
- 変更は [バージョン] - 日付 の見出しで管理しています。
- セクション: Added / Changed / Fixed / Security / Breaking Changes を使用します。

なお、本リリースはコードベースから推測して作成した初期リリースノートです。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-28
最初の公開リリース。日本株自動売買プラットフォームのコア機能群を提供します。主にデータ取得・ETL・カレンダー管理・リサーチ（ファクター計算）・AI ベースのニュース解析・市場レジーム判定・設定管理などを含みます。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開。パッケージバージョンは 0.1.0。
  - __all__ による公開モジュール: data, strategy, execution, monitoring（将来拡張用の名前空間を含む）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）。カレントワーキングディレクトリに依存しない読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - .env パーサーは export 形式、クォート、エスケープ、インラインコメント処理に対応。
  - Settings クラスを提供し、以下の設定をプロパティとして取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 必須変数未設定時は ValueError を送出するユーティリティを実装。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（1 API コールあたり最大 20 銘柄）・1 銘柄あたり最大記事数と文字数トリム制御。
    - JSON mode を利用した応答解析、レスポンス検証、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワークエラー/タイムアウト/5xx）を指数バックオフで実装。
    - DuckDB への書き込みは冪等性（DELETE → INSERT）で実施し、部分失敗時に既存スコアを保護。
    - 公開 API: score_news(conn, target_date, api_key=None)
    - テスト容易性: _call_openai_api の差し替えで API 呼び出しをモック可能。
    - タイムウィンドウ設計（JST 前日 15:00 ～ 当日 08:30 相当）とルックアヘッドバイアス回避の方針を明記。

  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベースのフィルタリング（複数キーワードを定義）。
    - OpenAI（gpt-4o-mini）を JSON mode で呼び出し、JSON パース失敗や API エラー時はフォールバック（macro_sentiment=0.0）して継続。
    - リトライ・バックオフ処理、レスポンスパースの堅牢化を実装。
    - DuckDB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に行い、失敗時は ROLLBACK を試行。
    - 公開 API: score_regime(conn, target_date, api_key=None)
    - ルックアヘッドバイアス防止（target_date 未満のデータのみ参照）を明確に設計。

- データ管理（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理機能（market_calendar テーブルとの同期）。
    - 営業日判定ユーティリティ群を提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB データ優先、未登録日は曜日ベースのフォールバック（末尾の整合性を保証）。
    - calendar_update_job: J-Quants API から差分取得し冪等保存、バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の構造化）。
    - ETL パイプライン設計に基づく差分取得・保存・品質チェックのための基盤（jquants_client 経由での保存、品質チェックフックを想定）。
    - テーブル存在確認や最大日付取得、トレーディング日調整等のユーティリティを実装。

- Research（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER、ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金・出来高比率）等の計算関数を提供。
    - DuckDB 上で SQL と Python の組み合わせで高速に計算。
    - 公開関数: calc_momentum, calc_value, calc_volatility
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン対応）を提供。
    - IC（Information Coefficient）計算 calc_ic（Spearman ρ の実装）を提供。
    - ファクター統計サマリー factor_summary、ランキング変換 rank を提供。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし特記事項。ただし OpenAI API キーや各種認証トークンは環境変数で管理することを想定。Settings は必須変数未設定時に明示的に例外を投げるため、運用時に環境設定漏れに気づきやすくなっています。

### Breaking Changes
- なし（初回リリース）

### Notes / 運用メモ
- 必須環境変数:
  - OPENAI_API_KEY（score_news / score_regime 実行時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みはデフォルトで有効。テストや CI で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を用いたローカル DB 操作を行います。既定のパスは data/kabusys.duckdb。
- AI 呼び出しのテストは、内部の _call_openai_api をユニットテストでモックすることを推奨します（news_nlp と regime_detector はそれぞれ独立した内部呼び出し関数を持ち、テスト差し替え可能）。
- ルックアヘッドバイアス対策として、target_date の取り扱いは厳格に過去データのみを使用する設計になっています。

---

以上がコードベースから推測した CHANGELOG の初期リリースノートです。必要であれば、より細かな関数別の説明や使用例、リリース日や移行ガイドの追記を行います。どの程度の詳細を出力しますか？