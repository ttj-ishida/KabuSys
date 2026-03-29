# CHANGELOG

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース: kabusys - 日本株自動売買 / データ基盤 / リサーチ用ユーティリティ群を提供。
  - パッケージメタ: src/kabusys/__init__.py にバージョン "0.1.0" を設定。
- 環境設定管理モジュール（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパース機能を実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応）。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live を検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
    - is_live / is_paper / is_dev 判定ヘルパー
  - 未設定の必須環境変数に対しては明確な ValueError を送出。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を参照して銘柄別に記事を集約し、OpenAI（gpt-4o-mini）に JSON mode で問合せてセンチメントを算出。
    - JST ベースのニュースウィンドウ計算（前日15:00〜当日08:30 JST を UTC に変換）を実装（calc_news_window）。
    - 1チャンク最大20銘柄バッチ処理、1銘柄あたり最大10記事、最大文字数でトリムする仕組みを実装。
    - API 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライを実装（最大リトライ回数・待機基数を設定）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、"results" フォーマット検証、コード存在チェック、数値性・有限性検査）とスコアの ±1.0 クリップ。
    - 成功した銘柄のみを DELETE → INSERT（トランザクション）で置換して部分失敗時に既存データを保護。
    - API キー未指定時は例外を投げる（api_key 引数または環境変数 OPENAI_API_KEY を期待）。
    - フェイルセーフ: API 呼び出し失敗時は該当チャンクまたは銘柄をスキップして処理継続。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュース抽出はニュースタイトルにマクロキーワード群を使ってフィルタリング（上限 20 件）。
    - OpenAI（gpt-4o-mini）を利用したマクロセンチメント評価。API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - レジームスコアは合成後に -1..1 にクリップし閾値でラベル付け。結果は market_regime テーブルへ冪等的にトランザクションで保存。
    - ルックアヘッドバイアス防止のため、全ての処理は target_date 引数と DB 内データに基づき実行（datetime.today() を参照しない設計）。

- データモジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にカレンダーデータがない場合は曜日ベース（土日非営業）でフォールバック。
    - next/prev_trading_day は最大探索日数を設定して無限ループを防止。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、save_market_calendar による冪等保存）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加（ETL の各種件数・品質問題・エラーを集約）。
    - 差分取得ロジック、最小データ開始日、カレンダー先読み、デフォルトバックフィル日数等の定義。
    - テーブル存在確認・最大日付取得ユーティリティを実装。
    - jquants_client と quality モジュールに依存して差分取得・保存・品質チェックを行う設計。
  - etl へ ETLResult を再エクスポート（kabusys.data.etl）。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - モメンタムファクター（1M/3M/6M リターン、ma200_dev）、ボラティリティ/流動性（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時は None を返すなど、堅牢性を重視した実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、horizons のバリデーションあり）。
    - IC（Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - 研究向けユーティリティの再エクスポート（zscore_normalize を含む）。

- パッケージ初期化（各サブパッケージの __init__ による公開 API 整備）
  - kabusys.ai: score_news をトップレベルで公開
  - kabusys.research: 主な分析関数を __all__ で公開

### Changed
- なし（新規リリース）

### Fixed
- なし（新規リリース）

### Notes / Migration
- OpenAI API を使う機能（score_news, score_regime）は api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定する必要があります。未設定時は ValueError を送出します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。パッケージ配布後やテスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を保つ設計です。部分失敗時はロールバックを行い、ロールバック失敗は警告ログに記録されます。
- ルックアヘッドバイアス対策: すべての日次処理は target_date に基づいて実行するため、呼び出し側は正しい基準日を渡してください（内部で datetime.today() を参照しません）。

---

作業ログや既知制約、将来的な改善点（例: PBR・配当利回りの実装、外部ライブラリを使った高速化、追加の API エラー取り扱いなど）は別途 ISSUE/TRACKER にまとめることを推奨します。