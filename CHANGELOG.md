# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
安定した API を目指しており、リリースごとに後方互換性や重要な挙動変更はここに明記します。

## [Unreleased]
（該当なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株のデータ取得・ETL・研究・AI評価・カレンダー管理を含む自動売買・リサーチ基盤の骨格を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初版を追加。バージョンは 0.1.0。
  - __all__ と __version__ を定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml から探索）。
  - export KEY=val 形式・クォートやインラインコメントの解析に対応した .env パーサを実装。
  - 環境変数の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - Settings クラスを提供（J-Quants・kabuステーション・Slack・DB パス・実行環境・ログレベル等の取得）。
  - 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
  - 必須 env 取得時に未設定なら ValueError を発生させる _require を提供。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols から記事を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を生成する機能を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST の記事）を calc_news_window で提供。
    - バッチサイズ、記事数・文字数トリム、JSON Mode 応答バリデーション、リトライ（429/ネットワーク/5xx）や指数バックオフをサポート。
    - レスポンス検証・スコアクリップ（±1.0）・DuckDB への冪等的書き込みロジック（DELETE→INSERT）を実装。
    - テストしやすさのため _call_openai_api を patch 可能とする設計注記あり。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出・保存する機能を実装。
    - LLM 呼び出しのリトライ、API エラー時のフォールバック（macro_sentiment=0.0）、レスポンス JSON パース保護を実装。
    - DuckDB に対する冪等的な書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 設計方針としてルックアヘッドバイアス回避（date.today()/datetime.today() を使わない）を徹底。

- データ関連（kabusys.data）
  - calendar_management モジュール
    - market_calendar を用いた営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値優先・未登録日は曜日ベースのフォールバック、最大探索日数制限（_MAX_SEARCH_DAYS）などの堅牢な実装。
    - JPX カレンダーを J-Quants から差分取得して保存する calendar_update_job（バックフィル・健全性チェック付き）を提供。
  - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開して ETL 実行結果（取得・保存件数、品質問題、エラー）を管理。
    - 差分取得・バックフィル戦略・品質チェックとの連携方針を実装（詳細は pipeline モジュール）。
    - jquants_client へ依存して差分フェッチ・保存を行う設計（jquants_client の関数を利用）。

- 研究 / ファクター（kabusys.research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等のファクター計算を実装。
    - DuckDB の SQL ウィンドウ関数を利用した一括計算でパフォーマンスを考慮。
    - 結果は (date, code) ベースの dict リストで返す。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリー機能を実装。
    - 外部依存を持たない純 Python 実装（pandas 等非依存）。ties の取り扱い、丸めによる ties 検出安定化等を考慮。

- その他
  - ai パッケージで score_news を公開。
  - research パッケージで主要関数を再エクスポート。
  - data.etl で ETLResult を再エクスポート。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- OpenAI API キーは明示的に引数で注入可能（api_key）で、環境変数 OPENAI_API_KEY も利用可。未設定時は ValueError により明示的に失敗する。
- .env 自動ロード時に OS 環境変数を上書きしない（.env.local の上書きは可能だが、既存 OS 環境変数は protected）。

### Notes / 既知の注意点
- DuckDB 実行時の互換性により、executemany に空リストを渡せない点に対応するガードを実装（空の場合は実行しない）。
- LLM 呼び出しは外部 API（OpenAI）に依存するためネットワーク障害やレート制限に対して冗長化（リトライ・フォールバック）を行うが、API コストやレスポンスの変動に注意してください。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間で内部関数を直接共有しない設計。テスト時はそれぞれを patch して動作を制御できます。
- 市場カレンダーが取得されていない環境では曜日ベースのフォールバックが使われます（祝日を考慮しないため結果に差が出る可能性あり）。
- デフォルトで使用する OpenAI モデルは gpt-4o-mini。将来変更される可能性があります。

---

今後のリリースでは、テストカバレッジ、ドキュメント（API リファレンス・ER 図）、より細かな品質チェックルール、実運用のための監視/アラート機能、及び発注系（execution）やモニタリング周りの実装を追加予定です。