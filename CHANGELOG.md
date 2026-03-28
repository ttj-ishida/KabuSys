# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog 準拠の形式を採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティの初期実装を追加。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョン "0.1.0" を定義。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート判定ロジック（.git または pyproject.toml を探索）を実装し、CWD に依存しない読み込みを実現。
  - .env パースの細かな仕様を実装：
    - export KEY=val 形式に対応
    - シングル/ダブルクォートとバックスラッシュエスケープの処理
    - インラインコメント処理（クォート無しの場合は直前にスペース/タブがあればコメント扱い）
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを実装（プロパティ経由で必須変数の検証・デフォルト値の提供）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー bool プロパティ: is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI (gpt-4o-mini) に送信して各銘柄のセンチメント（ai_score）を算出し、ai_scores テーブルに書き込むワークフローを実装。
    - ニュースウィンドウ計算（JST ベース、UTC に変換）を提供（calc_news_window）。
    - 銘柄毎に記事を集約しトリム（記事数/文字数上限）してバッチ送信（最大 20 銘柄/チャンク）。
    - OpenAI との堅牢なやりとり（JSON mode、リトライ（429/ネットワーク/5xx）、レスポンス検証、スコア ±1.0 でクリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時の既存データ保護を考慮）。
    - テスト容易性のため _call_openai_api をパッチ差替え可能。
  - regime_detector: ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロキーワードによる raw_news 抽出（最大件数制限）。
    - OpenAI 呼び出し（別実装にしてモジュール結合を避ける）、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）。
    - スコア合成ロジック（MA 重み 70%、マクロ重み 30%）、閾値によるラベリング。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）およびトランザクション失敗時の ROLLBACK 処理とログ。

- データ基盤 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB データ優先だが、カレンダー未取得や未登録日は曜日ベースのフォールバック（週末非営業）を使用。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新するバッチ処理を実装（バックフィル・健全性チェックあり）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
  - pipeline / etl:
    - ETLResult dataclass を実装し ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - ETL パイプライン設計に沿ったユーティリティ（差分取得、保存、品質チェックフック、バックフィル）を実装する基盤を追加。
    - DuckDB 互換性考慮（executemany に空リストを渡さないなどのワークアラウンド）。
  - etl モジュールで pipeline.ETLResult を再エクスポート。

- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）を計算する関数を実装。
    - DuckDB SQL を用いた効率的な一括取得ロジックを採用し、必要データ不足時の扱い（None）を明確化。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - Pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - research パッケージの __all__ に主要関数を公開。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- 環境変数の取り扱いに注意:
  - 必須トークンや API キーは Settings 経由で明示的に要求（未設定時は ValueError を送出）。
  - .env 自動ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Notes / Implementation decisions (設計上の注意点)
- ルックアヘッドバイアス対策:
  - 各種スコア計算・ウィンドウ計算で datetime.today()/date.today() を参照しない実装を徹底（target_date を明示的受け取り）。
- OpenAI 呼び出し:
  - JSON Mode を利用して厳密な JSON を期待するが、パースに失敗する場合の復元ロジックも実装（最外の {} を抽出）。
  - LLM 呼び出し部分はテスト時に差し替え可能（ユニットテスト容易性を考慮）。
- フェイルセーフ:
  - API 失敗時は例外を投げずにスキップやフォールバック（macro_sentiment=0.0 等）する設計を採用し、バッチ全体の耐障害性を高めている。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗する問題を回避するガードを入れている（DuckDB 0.10 対応）。
- 冪等性:
  - DB 書き込みは可能な限り冪等に実装（DELETE→INSERT / ON CONFLICT 等）して再実行耐性を確保。

### Known issues / Limitations
- OpenAI モデル名は _MODEL = "gpt-4o-mini" に固定（将来のモデル変更時は設定化を検討）。
- ai モジュールは OpenAI API キーに依存。API 利用制限やコストに注意。
- 一部の計算（MA200 等）は十分な過去データがない場合に中立値（例: ma200_ratio=1.0）を返すため、データ品質に依存する。

---

もしリリースノートに追加してほしい具体的なポイント（例えば環境変数一覧、API 使用上の注意、マイグレーション手順など）があれば教えてください。必要に応じて項目を追記・詳細化します。