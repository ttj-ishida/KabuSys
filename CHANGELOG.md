# Changelog

すべての注目すべき変更点を記録します。本書式は「Keep a Changelog」に準拠しています。

最新リリース
- リリース日や項目はコードベースから推測して記載しています。実際のリリース日や内容は必要に応じて調整してください。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初期リリース（推測）。日本株自動売買・研究・データ基盤向けのコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - バージョン情報を __version__ = "0.1.0" として定義。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを追加。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - export KEY=val 形式やクォート・エスケープ、行内コメント等を考慮した .env パーサを実装。
  - OS 環境変数の保護（protected set）をサポートし、.env.local による上書きを制御。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB /監視 / システム関連の設定プロパティ（環境変数読み取り・検証）を公開。
  - KABUSYS_ENV / LOG_LEVEL に対するバリデーション（許容値チェック）と is_live / is_paper / is_dev の便利プロパティを追加。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄別ニュース集約を行い、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントスコアを生成して ai_scores テーブルへ書き込み。
    - 時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST 相当）計算ユーティリティ calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの記事数・文字数制限、JSON レスポンス検証、スコア ±1.0 クリップなどを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ付きリトライ、及び失敗時のフェイルセーフ（該当チャンクをスキップして継続）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news からデータを取得、OpenAI API 呼び出し（gpt-4o-mini）でマクロセンチメント評価、スコア合成、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API エラー時は macro_sentiment=0.0 にフォールバックする等、堅牢なフェイルセーフ実装。
    - テスト用に _call_openai_api を差し替え可能に設計。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にカレンダーデータがない場合は曜日ベース（土日を休業日）でフォールバックする一貫した挙動。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ calendar_update_job の実装。バックフィル・健全性チェック（将来日チェック）を備える。
  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却。
    - 差分取得、バックフィル（既定3日）、J-Quants クライアント経由での保存、品質チェック呼び出し等の方針を実装（パイプラインの骨格）。
    - テーブル存在チェック等のユーティリティ関数を提供。
    - etl モジュールで ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上の SQL で計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - 入力は DuckDB 接続と target_date。結果は (date, code) をキーにした dict のリストで返却。データ不足時の None 処理を明示。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。
    - IC 計算（calc_ic）：ファクターと将来リターンのスピアマンランク相関を算出。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を持たない純粋 Python / DuckDB 実装を志向。

- その他
  - DuckDB を主要データストアとして想定した SQL 実行/変換ロジックを多数実装。
  - OpenAI SDK の利用を前提とした JSON mode 呼び出しとレスポンス整形を実装（テストでモックしやすい設計）。

### Changed
- （初期リリースのため特になし。将来のリリースで環境変数名やデフォルト値の変更が想定される点を留意。）

### Fixed / Robustness
- OpenAI 呼び出し周りの堅牢性向上
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx を想定したリトライと指数バックオフを実装。リトライ上限到達時は安全にフェイル（0.0 またはチャンクスキップ）して全体処理の停止を防止。
  - JSON パース失敗や不正レスポンスに対するサニティチェックを導入（部分復元やログ出力、該当レスポンスのスキップ）。
- DB 書き込み時の冪等性と障害対策
  - market_regime / ai_scores などへの書き込みは BEGIN/DELETE/INSERT/COMMIT の形で冪等に行い、例外発生時は ROLLBACK を試みる。ROLLBACK の失敗は警告ログに記録。
  - DuckDB の executemany の制約（空リスト不可）へ対応するガード（空の params を避ける処理）。

### Security
- API キーの解決で、api_key 引数優先→環境変数 OPENAI_API_KEY を参照する明確な挙動を定義。未設定時は ValueError を送出して誤実行を防止。

### Testing / Developer ergonomics
- OpenAI 呼び出しをラップした内部関数（_call_openai_api）をテスト時にパッチ可能に設計し、外部 API 呼び出しをモックしてユニットテストを容易に実行できるようにしている。
- .env 自動ロードはテスト実行時に環境変数で無効化できる（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注意:
- 本 CHANGELOG は提供されたソースコードから実装・設計意図を推測して作成したものであり、実際のリリースノートや変更履歴と差異がある可能性があります。公開用の CHANGELOG として使用する場合は、リリース日・項目の確定・表現の微調整を行ってください。