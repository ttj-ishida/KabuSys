# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリース方針: 重大変更は Breaking Change として明記します。
- 日付はパッケージ内の __version__ を基準にしています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-02

初回公開リリース。日本株自動売買プラットフォームの基盤機能群を実装しました。主に以下の領域を含みます。

### Added
- パッケージ基本
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - サブパッケージの公開インターフェースに data, strategy, execution, monitoring を含める初期構成。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込み（プロジェクトルート検出ロジック: .git または pyproject.toml）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いの定義。
  - 保護（protected）キー概念: OS 環境変数を上書きから保護。
  - 必須 env の取得ヘルパー (_require) と検証:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティを提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証（有効な値でない場合は ValueError）。
  - デフォルト値付きの Path/閾値プロパティを提供（DuckDB/SQLite パス、PID ファイル、CPU/MEM/DISK 閾値など）。

- AI（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を基に銘柄別ニュース集約→OpenAI（gpt-4o-mini）でバッチ評価 → ai_scores へ書き込み。
    - JST時間ウィンドウ（前日15:00〜当日08:30）を UTC に変換する calc_news_window を提供。
    - バッチ処理（最大20銘柄/回）、1銘柄あたり記事上限・文字数トリム、レスポンス検証とスコアクリップ（±1.0）。
    - API リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。非リトライエラーはスキップして継続するフェイルセーフ設計。
    - テストのために _call_openai_api に差し替え可能な設計。
    - レスポンス整形/復元（JSON mode でも余計なテキストが混入する場合の最外部 {} 抽出）や知らない銘柄コードの無視など堅牢なバリデーション。
  - regime_detector モジュール
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによるニュース抽出、OpenAI（gpt-4o-mini）へのプロンプト設計、JSON レスポンスパース。
    - API 呼び出しでのリトライ/バックオフ、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - DuckDB へ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込む実装。
    - ルックアヘッドバイアス回避設計（date < target_date の排他条件、datetime.today() を参照しない等）。
    - テスト容易性のため API キー注入が可能（引数 or 環境変数 OPENAI_API_KEY）。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金/出来高比率）、バリュー（PER/ROE）の計算関数を実装。
    - DuckDB に対する SQL による効率的なウィンドウ集計を採用。データ不足時の扱い（None）やログ出力あり。
  - feature_exploration モジュール
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）等の統計ユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - market_calendar を用いた営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と夜間バッチ更新（calendar_update_job）。
    - DB がまばらな場合は曜日ベースのフォールバックを行い、一貫性を保つ設計。
    - API からの差分取得、バックフィル、健全性チェックを実装。
  - pipeline / etl モジュール
    - ETLResult データクラスを公開（etl の集計結果・品質問題・エラー情報を保持）。
    - ETL パイプライン設計（差分取得、保存、品質チェック）に沿ったユーティリティ群（実装の一部を含む）。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティ関数を実装。
  - jquants_client と quality 等の外部連携用モジュール群と連携できる構成（実際のクライアント実装は別モジュール想定）。

- その他設計/運用面の配慮
  - ルックアヘッドバイアス防止（AI/リサーチ処理で現在時刻を参照しない設計）。
  - DB 書き込みは基本的に冪等化（DELETE→INSERT、ON CONFLICT 相当の方針）。
  - OpenAI 呼び出し回りはテスト差替えポイントを設けておりユニットテストの容易性を考慮。
  - ロギングと警告により失敗時の情報を残す（API パース失敗・ROLLBACK 失敗など）。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- OpenAI API キーや各種トークンは環境変数から取得することを想定。必須設定がない場合は ValueError を送出し、秘密情報のハードコードを防止。
- .env 自動ロードで OS 環境変数を保護する仕組み（protected keys）を実装。

### Known limitations / Notes
- 外部 API（J-Quants、OpenAI 等）への依存があるため、実行環境で適切な API キーやエンドポイントが必要です。
- strategy / execution / monitoring の具体的な発注ロジックや監視実装は本リリースでは最小限または未実装（パッケージの公開インターフェースとして存在）で、データ取得・研究・NLP 部分に重点を置いた初期版です。
- DuckDB のバインド挙動（executemany の空リスト等）に合わせたガードロジックを導入しています。

---
フィードバックやバグ報告、機能要望は issue にて受け付けてください。