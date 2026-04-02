# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。  

注: 本 CHANGELOG はリポジトリ内のソースコードから実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-02

### Added
- パッケージ基盤
  - パッケージルートを定義（kabusys パッケージ、`__version__ = "0.1.0"`、公開モジュールリスト `__all__`）。
- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env/.env.local の読み込み優先度実装（OS 環境変数 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 高度な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント処理の扱い）。
  - 環境設定のラッパークラス `Settings` を提供。J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（env, log_level）などのプロパティを提供し、値の検証を行う。
  - 必須環境変数未設定時に分かりやすいエラーメッセージを送出する `_require` 実装。
- データモジュール（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - JPX マーケットカレンダーの保守・問い合わせロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未登録の時の曜日ベースフォールバック、DB 優先の挙動、最大探索日数制限、バックフィル・健全性チェックを実装。
    - 夜間バッチジョブ `calendar_update_job` を実装（J-Quants API クライアント経由で差分取得・保存）。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETL 実行結果を表現するデータクラス `ETLResult` を実装（取得件数、保存件数、品質チェック結果、エラー一覧などを格納）。
    - ETL モジュールは差分更新、バックフィル、品質チェックの設計方針を反映（J-Quants クライアント連携）。
    - `kabusys.data.etl` から `ETLResult` を再エクスポート。
- AI モジュール（src/kabusys/ai）
  - ニュース NLP（news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini の JSON Mode）へバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込むロジックを実装。
    - チャンク処理（最大20銘柄／チャンク）、トークン肥大化対策（記事数/文字数制限）、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンスの厳格なバリデーションを実装。
    - DuckDB の executemany に関する互換性（空リスト不可）を考慮した DB 書き込み処理（DELETE → INSERT の置換戦略）。
    - 外部ライブラリ（pandas 等）に依存しない実装方針。
    - 公開関数: `score_news(conn, target_date, api_key=None)`（API キーは引数または環境変数 OPENAI_API_KEY）。
  - レジーム判定（regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出・保存する機能を実装。
    - マクロ記事抽出、OpenAI 呼び出し、スコア合成、冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出し失敗時はフェイルセーフで macro_sentiment=0.0 とする設計。
    - 公開関数: `score_regime(conn, target_date, api_key=None)`（API キーは引数または環境変数 OPENAI_API_KEY）。
- Research モジュール（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、ATR 比率、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（一定行数未満は None）やスキャン範囲のバッファ設計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns: 任意ホライズン）、IC（calc_ic: スピアマンのランク相関）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を用いない純 Python 実装。
  - research パッケージの __init__ で主要関数を公開（再エクスポート）。
- パッケージ内公開関数の整理
  - ai パッケージで `score_news` を公開。
  - research パッケージで主要関数を公開。
- 実装上の設計方針・安全策
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today()/date.today() を不必要に参照しない設計（target_date を明示的に渡す形式）。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスのパースエラーに対する復元ロジック（外側の {} を抽出）を実装。
  - DuckDB を前提としたクエリ／操作（互換性考慮の実装コメントあり）。
  - テスト容易性のため OpenAI 呼び出し箇所をモック可能に設計（関数分離）。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Security
- .env 読み込み時、既存の OS 環境変数を保護する仕組み（protected set）を実装。
- 機密情報（API キー）未設定時は明確なエラーを返す（OpenAI API キー、Slack トークン、kabu API パスワード など）。

### Notes / 開発者向けメモ
- AI 機能（score_news, score_regime）は OpenAI API キーが必要（引数または環境変数 OPENAI_API_KEY）。未設定だと ValueError を送出します。
- .env 自動読み込みを抑制するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- DuckDB の executemany における空リストの扱いに依存しないように保護コードを追加しています（DuckDB 0.10 互換性対応）。
- 外部 HTTP / API のエラーや予期しないレスポンスは多くの箇所でフェイルセーフ（スキップ or 0.0 スコア）となっており、処理の継続性を重視しています。

---

（本 CHANGELOG はソースコードからの推測に基づいており、実際のリリースノートと差異がある可能性があります。必要であれば、各コミットやリリースコメントに基づいて修正してください。）