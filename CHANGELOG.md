# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

- リリースポリシー: 互換性に関する記載はセマンティックバージョニングに従います。  
- 日付はローカルリポジトリの最終更新を想定して設定しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買プラットフォームの基盤機能を実装しています。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ名 `kabusys` を追加。パッケージバージョンは 0.1.0。
  - __all__ により主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env ファイルのパース器を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数の保護（ファイル読み込み時に既存 OS 環境変数を protected として扱う挙動）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL 等）をプロパティで取得・バリデーション。
  - 必須環境変数未設定時に明確な ValueError を発生させる _require() を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - target_date に基づくニュースウィンドウ計算（JST基準 → UTC に変換）calc_news_window を実装。
    - raw_news と news_symbols から銘柄ごとに記事を集約する _fetch_articles 実装（件数・文字数上限、トリム）。
    - OpenAI（gpt-4o-mini）を用いたバッチ評価（最大 20 銘柄/チャンク）と JSON Mode を利用したレスポンス処理。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。リトライの上限と待機ロジックを導入。
    - レスポンスのバリデーションおよびスコアクリッピング（±1.0）。不正レスポンスはスキップして継続（フェイルセーフ）。
    - ai_scores テーブルへの冪等書き込み（該当コードのみ DELETE → INSERT）を実装。DuckDB executemany の空リスト制約に配慮。
    - public API: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。
    - テスト容易性のため _call_openai_api を内部関数として切り分け、テストで差し替え可能に。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み付き合成（70%/30%）して日次レジーム（bull/neutral/bear）判定を実装。
    - prices_daily と raw_news を利用し、calc_news_window に基づくマクロニュース抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時のフォールバック（macro_sentiment=0.0）、リトライ、ログ出力を実装。
    - public API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。
    - テスト用に _call_openai_api を独立実装（news_nlp と共有しないことによりモジュール分離）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定・探索関数を実装（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 未登録日は曜日ベースのフォールバック（土日非営業）を採用し、DBがまばらな場合でも一貫した判定を行う設計。
    - カレンダー夜間バッチ calendar_update_job を実装（J-Quants クライアント呼び出し、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲制限 (_MAX_SEARCH_DAYS) とサニティチェックを導入。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを追加（取得/保存件数、品質問題、エラー一覧、ユーティリティ変換 to_dict）。
    - 差分更新・バックフィル・品質チェックの方針に沿った設計（jquants_client と quality モジュールを使用）。
    - _table_exists / _get_max_date 等の内部ユーティリティ（DuckDB 特性に配慮）。
    - etl.py で ETLResult の再エクスポートを提供。

  - jquants_client との連携ポイントを想定（fetch/save 系関数を利用）。

- 研究ツール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB SQL ベースで実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返すなど、堅牢な挙動。
    - 出力は (date, code) を含む dict のリスト形式。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力バリデーション、1クエリ実行）。
    - IC（情報係数）計算 calc_ic（スピアマンのρ、rank による実装、最小サンプルチェック）。
    - rank ユーティリティ（同順位は平均ランク、丸めを用いた tie の抑制）。
    - factor_summary（count/mean/std/min/max/median）による統計サマリー。

- その他設計上の注意点・安全策
  - ルックアヘッドバイアス防止: 各処理は内部で datetime.today() / date.today() を参照せず、外部から target_date を明示的に渡す設計。
  - OpenAI API キーは引数で注入可能（テスト時の差替えや複数キー運用に対応）。環境変数 OPENAI_API_KEY からの取得もサポート。
  - API 呼び出しはリトライとフォールバックを備え、例外で処理が完全停止しないようフェイルセーフを採用（ログ記録は行う）。
  - DuckDB の特性（executemany に空配列不可等）に配慮した実装。
  - DB 書き込みは冪等性を意識（DELETE → INSERT または ON CONFLICT 相当の戦略）。失敗時にはROLLBACK を行い、ROLLBACK 自体の失敗もログに残す。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数読み込みの際、OS 環境変数を保護する仕組みを導入（protected set）。.env 自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini を想定。将来的なモデル変更や SDK バージョン差分に対し現行コードはステータスコードの扱い等で互換性を考慮しているが、実稼働前の確認を推奨。
- ai_scores / market_regime 等のテーブルスキーマは本CHANGELOGでは記載していません。実運用時はスキーマ設計・マイグレーションが必要です。
- 監視・実行・戦略（strategy, execution, monitoring）パッケージの公開インターフェースは宣言済みだが、本リリースでは基盤モジュールに重点を置いているため、個別戦略や注文実行ロジックは別フェーズで実装予定。

---

著者: kabusys コードベースから推測して作成。用途に応じて項目の追加・修正を行ってください。