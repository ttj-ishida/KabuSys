# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。本リポジトリは日本株のデータ処理・研究・AIスコアリング・市場レジーム判定・ETL・カレンダー管理・環境設定等を含む自動売買補助ライブラリとして公開されます。

### Added
- パッケージ基盤
  - パッケージ名 kabusys として公開。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を定義（公開モジュールの想定）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装：
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（_find_project_root）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env のパースはシェル風の書式に対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理など）。
  - _load_env_file による protected（既存OS環境変数保護）や override フラグをサポート。
  - Settings クラスを提供し、環境変数から各種設定を安全に取得：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須取得メソッド（未設定時は ValueError）。
    - データベースパス（duckdb / sqlite）、監視設定（PIDファイルパス、CPU/MEM/DISK閾値）などのプロパティ。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の妥当性チェック、is_live/is_paper/is_dev の補助プロパティ。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）:
    - raw_news と news_symbols を集約して銘柄別に記事をまとめ、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して ai_scores テーブルへ保存。
    - バッチサイズ制御（最大20銘柄／チャンク）、1銘柄あたりの記事数・文字数トリミング、リトライ（429・ネットワーク・5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - 時間ウィンドウは target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と照合）。ルックアヘッドバイアス対策を明示。
    - OpenAI 呼び出しはテスト容易性のため差し替え可能（_call_openai_api を patch 可能）。
    - DB 書き込みは部分失敗に備えて該当コードのみ DELETE→INSERT（冪等）する実装。DuckDB の executemany の制約への対応あり。
  - 市場レジーム判定（regime_detector.score_regime）:
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はニュースタイトルでマクロキーワード検索。LLM は gpt-4o-mini を使用し JSON で macro_sentiment を取得。
    - API リトライ・フェイルセーフ（API 失敗時 macro_sentiment=0.0）、レスポンスパース失敗時のロギングとフォールバック。
    - レジーム結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データモジュール（src/kabusys/data）
  - カレンダー管理（calendar_management）:
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先だが、データ未取得日は曜日ベースのフォールバックを提供。探索上限 _MAX_SEARCH_DAYS により無限ループ回避。
    - 夜間バッチ job（calendar_update_job）で J-Quants から差分取得して market_calendar を更新。バックフィルと健全性チェックを実装。
  - ETL パイプライン（pipeline）:
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を行う ETLフレームワーク。
    - ETLResult dataclass を定義し、実行結果（取得数・保存数・品質問題・エラーなど）を集約。to_dict により品質問題を辞書化。
    - デフォルトのバックフィル日数、カレンダー先読み等の設定を組み込み。
  - etl モジュールから ETLResult を再エクスポート（短い公開インターフェース）。

- 研究（research）モジュール（src/kabusys/research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）やバリュー（PER, ROE）を DuckDB 上の SQL で計算する関数を提供（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理、返却形式は (date, code) をキーとする dict のリスト。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンをサポートし一括クエリで取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装。充分なレコードがない場合は None を返す。
    - ランク変換（rank）: 同順位は平均ランク、丸め処理で ties 検出の安定化。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - 研究モジュールは外部ライブラリ（pandas 等）に依存せず、DuckDB と標準ライブラリで実装。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Removed
- （新規リリースのため該当なし）

### Deprecated
- （新規リリースのため該当なし）

### Security
- （特になし）

### Notes / 使用上の注意
- 多くの機能が OpenAI API（環境変数 OPENAI_API_KEY）および J-Quants API 等の外部 API に依存します。未設定時は明示的に ValueError を返す箇所があるため、環境変数の設定に注意してください。
- DB は DuckDB を想定しており、DuckDB のバージョン差分（executemany の空リストの扱い等）に配慮した実装になっています。
- 設計上、datetime.today() や date.today() を直接参照しないことでルックアヘッドバイアスを避ける設計方針を採用しています（すべて target_date を明示的に渡す）。
- OpenAI 呼び出し部分はテストのため差し替え可能な設計（モジュール毎に private な呼び出し関数を持ち、意図的に共有しない）です。
- 現時点で Strategy / Execution / Monitoring に関する実装は公開インターフェースを想定したモジュール名のエクスポートがあるものの、詳細な実装や統合テストは別途必要です。

---

参考:
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください。