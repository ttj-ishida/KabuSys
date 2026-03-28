# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

全般な方針:
- 日付は変更を取り込んだ想定日を記載しています（実装日と合わせてください）。
- 各項目はコードベースから推測できる機能追加・設計方針・重要な振る舞いをまとめています。

## [Unreleased]
- 今後の変更・修正をここに記載します。

## [0.1.0] - 2026-03-28
最初の公開リリース。主要コンポーネントを実装し、日本株のデータ取得・特徴量計算・ニュースNLP・市場レジーム判定などの基盤機能を提供。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開用 __all__ 定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml 基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト時に便利）。
  - .env パーサの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの判定ロジック（クォート有無による挙動差分）
  - 環境変数保護機能（.env 読み込みで OS 環境変数を protected として上書き抑制）。
  - Settings クラスによる設定プロパティ群を追加（J-Quants / kabuステーション / Slack / DB パス / 実行環境・ログレベル判定等）。
  - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）と便捷プロパティ（is_live / is_paper / is_dev）。

- AI（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news, news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチ処理（デフォルト 20 銘柄/回）・1銘柄あたり記事数/文字数上限を実装（トークン膨張対策）。
    - JSON Mode を用いた厳格なレスポンス検証、部分失敗時に他銘柄スコアを保護する DB 書き換え（DELETE→INSERT）ロジックを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスパースのフォールバック（出力前後に余計なテキストが混入した場合に {} を抽出）を実装。
    - score_news 関数はルックアヘッドバイアスを避けるため datetime.today() を参照しない設計。
    - テスト容易性のため OpenAI 呼び出しを _call_openai_api で抽象化（unittest.mock.patch で差し替え可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で market_regime を算出。
    - マクロニュース抽出のためのキーワード群を実装（日本・米国・グローバルの主要語）。
    - OpenAI（gpt-4o-mini）呼び出しのリトライ・フォールバック（API 失敗時は macro_sentiment = 0.0）。
    - score_regime は DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - モジュール間の結合を避けるため、regime_detector と news_nlp は内部の OpenAI 呼び出し実装を共有しない。

- データ（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を実装し、ETL のフェッチ件数・保存件数・品質チェック結果・エラーを集約。
    - 差分取得・バックフィル・品質チェック（quality モジュール利用）の枠組みを実装。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値を優先し、未登録日や NULL 値は曜日ベースでフォールバックする一貫した挙動を提供。
    - calendar_update_job により J-Quants からの差分取得・冪等保存（ON CONFLICT 相当）とバックフィルを実装。
    - 最大探索日数や健全性チェック（将来日付の異常検出）を実装して安全性を確保。
  - jquants_client との連携を想定（fetch / save 系関数を利用）。

- 研究用ユーティリティ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M）、200日移動平均乖離、ATR ベースの Volatility、流動性（20日平均売買代金・出来高比率）、Value（PER/ROE）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL を利用した実装で外部 API へはアクセスしない設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns：任意ホライズンに対応、引数検証あり）。
    - IC（Information Coefficient）計算（calc_ic：スピアマンランク相関を実装、最小サンプル検査）。
    - ランク変換ユーティリティ（rank：同順位は平均ランク）。
    - 統計サマリー（factor_summary：count/mean/std/min/max/median）を実装。
  - zscore_normalize を data.stats から再エクスポートするインターフェースを用意。

### Changed
- (初版リリースのため履歴はありません。内部設計注記として以下を明記)
  - DuckDB 互換性に配慮した実装（executemany に空リストを渡さない等の防御策）。
  - ルックアヘッドバイアス防止のため日付取得にグローバルな現在時刻参照を行わない設計を徹底（すべての score / calc 関数で target_date を明示的に受け取る）。

### Fixed
- (初版リリース時点で顕在バグ修正履歴はなし。ただし多数のフェールセーフ処理とロギングを実装)
  - DB 書き込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出力する安全処理を追加。
  - OpenAI レスポンスパース失敗や API エラー時は例外を投げずフェイルセーフ（ゼロやスキップ）で処理継続する挙動を採用。

### Security
- 機密情報（OpenAI API キー等）は引数注入 or 環境変数で提供する設計。環境変数が未設定の場合は明示的な ValueError を送出して安全性を担保。

### Notes / Developer hints
- OpenAI 呼び出しはテスト容易性のため _call_openai_api を通す実装になっており、unit test で patch して例外・戻り値を差し替え可能。
- .env パーサは UNIX 系の典型的な .env 書式に配慮しているが、極端なケースでは期待通りに動作しない可能性があるため .env.example を参照して正しい形式を使ってください。
- DuckDB の日付や型に依存する実装があるため、DuckDB バージョン差異に注意（コメント中にも互換性に関する注記あり）。
- news_nlp / regime_detector の LLM 呼び出しは gpt-4o-mini と JSON Mode を前提に設計されているため、将来のモデル・API 変更時には response_format やパースロジックの見直しが必要。

---

[0.1.0]: https://example.com/release/0.1.0  (実運用時はリリースノート URL を更新してください)