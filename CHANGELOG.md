# CHANGELOG

すべての注記は Keep a Changelog のフォーマットに準拠しています。

なお、以下の変更履歴は提供されたコードベースの内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージを初期実装。公開 API として data, research, ai, execution, strategy, monitoring 等を想定したモジュールを提供（__all__ にてエクスポート）。
  - バージョン情報を src/kabusys/__init__.py にて管理（__version__ = "0.1.0"）。

- 環境設定 / .env 読み込み
  - .env / .env.local を自動的にロードする機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env のパース機能を強化:
    - 空行・コメント行（#）無視、先頭に `export ` を許容。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートのない値に対するインラインコメント判定（直前がスペース/タブの場合のみ）。
  - 環境変数上書きルール:
    - OS 環境変数を保護する protected セットを導入。
    - .env.local は .env を上書き（override=True）する挙動を持つ。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを実装し、アプリケーションで必要な設定（J-Quants / kabu / Slack / DB パス / 実行環境 / ログレベル等）をプロパティとして提供。
    - 必須値（トークン等）は未設定時に ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（許容値セットあり）。
    - duckdb / sqlite のデフォルトパスを指定。

- AI（ニュース NLP / レジーム判定）
  - news_nlp モジュール（score_news）:
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメント評価。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して扱う calc_news_window を提供。
    - 銘柄ごとに記事を結合し、文字数や記事数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）で API 呼び出し、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - OpenAI の JSON mode を利用しレスポンスをバリデーション（JSON 抽出、results キー・型検証、未知コード無視、数値検証）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ安全に置換（DELETE → INSERT、DuckDB executemany の空リスト制約に配慮）。
    - テスト容易性のため API 呼び出し関数をモジュール内で定義しモック可能に実装。
  - regime_detector モジュール（score_regime）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp により得られるマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - マクロニュースはキーワードでフィルタ（複数の日本語／英語キーワード）。
    - OpenAI 呼び出しは news_nlp と別実装として分離（モジュール結合を避ける）。
    - LLM エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - look-ahead バイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date に依存）。

- Research（ファクター計算・特徴量探索）
  - factor_research:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（duckdb SQL ベース）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - Value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損のときは None）。
    - データ不足時は None を返す挙動。
  - feature_exploration:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（結合・欠損除外・有効レコード数検査）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）、各ファクターの基本統計量（count/mean/std/min/max/median）を提供。
    - 外部依存を用いず標準ライブラリのみで実装（研究環境で安全に利用可能）。

- Data プラットフォーム
  - calendar_management:
    - market_calendar テーブルを基に営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがある場合は DB 値を優先し、未登録日は曜日ベース（平日）でフォールバックする一貫した挙動を実装。
    - calendar_update_job: J-Quants クライアント（jquants_client）経由で差分取得し market_calendar を冪等保存。バックフィル・健全性チェック（将来日付が異常に遠い場合はスキップ）を実装。
  - pipeline / ETL:
    - ETLResult データクラスを導入し、ETL の各段階（prices, financials, calendar）の取得/保存件数、品質問題、エラーを集約。
    - _get_max_date 等のユーティリティで差分取得ロジックを支援。
    - 実装方針として「営業日 1 日分の差分取得をデフォルト」「backfill による再取得」「品質チェックは収集して呼び出し元で判断」などを明記。
  - ETL 実行での DuckDB 周りの互換性対策（executemany の空リスト回避、date 型変換ユーティリティ _to_date）を実装。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Deprecated
- （初版につき該当なし）

### Removed
- （初版につき該当なし）

### Security
- （現時点で特記なし）

---

補足（設計上の重要ポイント・既知の挙動）
- Look-ahead バイアス防止
  - AI スコア算出やレジーム判定、ETL の各処理は、内部で datetime.today()/date.today() を直接参照せず、必ず target_date を明示的に受け取る設計になっているため、バックテストや研究用途でのリークを防ぐことが意図されている。
- フェイルセーフ
  - LLM/API 関連でエラー発生時はゼロスコアやスキップで継続する実装方針（例: macro_sentiment=0.0、失敗チャンクは空辞書返却）を取っており、外部サービス障害による全体停止を避ける設計。
- テスト性
  - OpenAI 呼び出し部分はモジュール内関数として分離してあり、ユニットテストで簡単にモック差し替えが可能。
- DuckDB 互換性
  - executemany に空リストを渡せないバージョンへの配慮や、配列バインドの不安定さを避けるための実装（個別 DELETE の繰り返し等）を含む。

既知の制約・注意事項
- OpenAI API の利用には OPENAI_API_KEY が必要。関数呼び出しでは api_key を引数で注入可能。
- J-Quants クライアント（jquants_client）は外部依存であり、実際の API 動作は別途設定と認証が必要。
- 一部のロジックは DuckDB の SQL 機能（ウィンドウ関数等）に依存しているため、使用する DuckDB バージョンの互換性に注意。

もし加筆・修正したい点（例えば実際のリリース日、特別に強調したい修正や既知のバグ）などがあれば指示ください。