# CHANGELOG

全ての変更は Keep a Changelog のフォーマットに準拠します。  
このファイルはコードベース（src/kabusys 以下）の状態から推測して作成しています。

注意: バージョンはパッケージの __version__("0.1.0") に合わせています。

## [Unreleased]
- （現在のブランチに未リリースの変更はありません）

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買 / データプラットフォーム / 研究用ユーティリティ群を提供。
  - ルートパッケージエクスポート:
    - kabusys.__all__ に data, strategy, execution, monitoring を定義。
- 環境変数・設定管理モジュール（kabusys.config）を追加。
  - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）を実装。
  - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
  - Settings クラスで主要設定値をプロパティとして公開（必須値は _require により ValueError を送出）。
  - 主要環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID、デフォルトパス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH）と閾値（CPU/MEM/MEMORY/DISK）をサポート。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）を実装。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントを算出、ai_scores テーブルへ書込み。
    - タイムウィンドウの計算（JST 前日15:00〜当日08:30 を UTC に変換）を実装。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数上限（保護のため）をサポート。
    - レスポンス検証・クリップ（±1.0）、部分成功時の idempotent な DB 更新（DELETE → INSERT）を実装。
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - リトライ（429, ネットワーク, タイムアウト, 5xx）に対する指数バックオフを実装し、致命的ではない失敗はスキップ（フェイルセーフ）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動ETF）の 200 日 MA 乖離（重み 70%）とマクロ新聞の LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily, raw_news, market_regime を参照し、計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロキーワードによるタイトル抽出、OpenAI 呼び出し（gpt-4o-mini, JSON 出力）、リトライとフォールバック（API 失敗時 macro_sentiment=0.0）。
    - API キー解決は api_key 引数または OPENAI_API_KEY。未設定時は ValueError。
- データモジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar 未取得時は曜日（土日）ベースでフォールバック。DB 登録があれば DB 値を優先。
    - calendar_update_job: J-Quants API から差分取得して market_calendar に冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラスを追加（取得・保存件数、品質チェック結果、エラー一覧を保持）。to_dict() により品質問題を辞書化して出力可能。
    - _table_exists / _get_max_date 等の内部ユーティリティ（DuckDB 前提）を追加。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- 研究モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）等を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、atr_pct、avg_turnover、volume_ratio を計算。データ不足時は None。
    - calc_value: raw_financials と prices_daily を結合し PER/ROE を計算（EPS 0/欠損時は None）。
    - DuckDB のウィンドウ関数を用いた効率的な実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。ホライズン値の検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクで扱うランク関数を実装（丸め処理で ties 対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。
  - 研究モジュールは zscore_normalize（kabusys.data.stats）と各計算関数を再エクスポート。
- テストしやすさ・堅牢性:
  - OpenAI 呼出しはモジュール内で _call_openai_api を定義しており、ユニットテスト時に patch して差し替え可能。
  - 各所でログ出力（logger）と例外制御を丁寧に実装（トランザクション失敗時の ROLLBACK 試行、WARN/INFO レベルの記録など）。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（全て target_date ベース）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト安全性）かつ環境変数 OPENAI_API_KEY から取得。未設定時はエラーを明示。

---

開発上の注意・補足
- DuckDB を前提とした SQL 実装が多く含まれます。バインド引数や executemany の振る舞い（空リスト不可など）に対する互換性考慮が行われています。
- AI（OpenAI）呼出しは gpt-4o-mini + JSON Mode を想定。API 仕様変更やレスポンスの不整合に備えたパース復元・バリデーション処理を実装しています。
- 各モジュールは「本番口座・発注 API にはアクセスしない」方針で設計されており、データ取得・解析・保存に集中した実装になっています。

（この CHANGELOG はコードベースからの推測に基づいて作成しています。実際のコミット履歴やリリースノートに合わせて適宜修正してください。）