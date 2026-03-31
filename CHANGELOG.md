# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本CHANGELOGは提示されたコードベースの内容から実装意図・機能を推測して作成しています。実際のコミット履歴とは異なる可能性があります。

## [Unreleased]

- 今後のリリースに向けた未確定の改善点・追加機能の記載領域。

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を包含する基盤的実装を提供します。

### Added
- パッケージ基礎
  - kabusys パッケージの公開バージョンを 0.1.0 として設定。
  - パッケージのトップモジュールで主要サブパッケージ (data, strategy, execution, monitoring) を __all__ に公開。

- 環境設定・読み込み (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロードの仕組みを実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - .env のパース機能を強化：
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント処理（クォート外での '#' の扱いを考慮）。
    - 無効行やキーなし行の無害化。
  - .env 自動ロードの制御環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 環境変数保護（既存 OS 環境変数を protected として上書き回避）に対応。
  - Settings 上で必要なキー取得メソッド（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）とデフォルト値（KABU_API_BASE_URL、データベースパス等）を提供。
  - KABUSYS_ENV / LOG_LEVEL の入力バリデーション（許容値の検査）を実装。
  - 設定からの環境判定ユーティリティ（is_live, is_paper, is_dev）を追加。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出し ai_scores テーブルへ書き込む。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換ロジックを提供（calc_news_window）。
    - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事かつ 3000 文字までのトリムを行う。
    - API 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。非再試行エラーはスキップするフェイルセーフ設計。
    - OpenAI レスポンスの堅牢なバリデーション（JSON 抜き出し、results リスト構造・コード照合・数値チェック）と ±1.0 でのクリップ処理。
    - DuckDB の executemany の制約を考慮し、空リスト回避ロジック（空の場合は実行しない）を実装。
    - テスト用に内部の _call_openai_api をパッチ差し替え可能（unittest.mock 対応）に設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news の参照と、レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）する処理を提供。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 取得、API エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - リトライ・エラーハンドリング（RateLimitError, APIConnectionError, APITimeoutError, APIError の 5xx 判定）を備える。
    - ルックアヘッドバイアスを防ぐ設計（内部で date.today() を参照せず、target_date 未満条件などを厳格化）。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを使った営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時の曜日ベースのフォールバック（週末=非営業日）を実装。
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得し保存）。バックフィル・健全性チェックを含む。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETL 実行結果を表す ETLResult データクラスを公開（fetch/save カウント、品質チェック結果、エラー集約等）。
    - 差分更新・バックフィル方針、品質チェック（quality モジュールとの連携）を想定した設計。
    - DuckDB 上でのテーブル存在確認・最大日付取得ユーティリティを提供。
    - ETLResult.to_dict により品質問題をシリアライズして監査ログ等に利用可能。

- リサーチ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用し、欠損・データ不足時の None 戻しによる堅牢化を行う。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で完結する実装方針。

### Changed
- 初回リリースのため該当なし（初期実装）。

### Fixed
- 初回リリースのため該当なし（初期実装）。

### Security
- 初回リリースのため該当なし。

### Notes / 実装上の注意
- DuckDB 0.10 系の挙動（executemany に空リストが与えられると失敗する等）を考慮した実装が随所にあるため、DuckDB のバージョン差異に注意。
- OpenAI API 呼び出しは gpt-4o-mini を前提とした JSON Mode の利用を想定。API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給可能。API 呼び出しの堅牢化（再試行・フォールバック）を実装しているが、API 利用制限やコストに配慮すること。
- 時刻・ウィンドウ計算は JST/UTC を明示的に扱っている（ニュース集約の時間窓等）。target_date ベースでの処理に統一し、ルックアヘッドバイアス回避に配慮。
- テストの容易性を考慮して、一部の内部 OpenAI 呼び出し関数はパッチ差し替えを想定している（ユニットテストでのモック化が可能）。

---

以上。必要であれば各モジュールごとの詳細な変更一覧（関数シグネチャ・例外挙動・DBスキーマ要件など）を追記します。どのレベルの詳細が必要か教えてください。