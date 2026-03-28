# Changelog

すべての重要な変更履歴をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-28

初回リリース。

### Added
- パッケージエントリポイント
  - kabusys パッケージを追加。__version__ = 0.1.0、トップレベルの公開モジュールとして data / strategy / execution / monitoring を __all__ に設定。

- 環境変数 / 設定管理
  - kabusys.config モジュールを追加。
  - .env および .env.local ファイルをプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 複雑な .env 行のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / 実行環境（development / paper_trading / live）などの設定値をプロパティ経由で取得。未設定必須値は ValueError を発生させる。
  - デフォルト値、検証（有効な環境名・ログレベルのチェック）や is_live / is_paper / is_dev のヘルパーを実装。

- AI（LLM）関連
  - kabusys.ai パッケージを追加。news_nlp.score_news と regime_detector.score_regime を公開。
  - news_nlp:
    - raw_news と news_symbols から前日15:00 JST〜当日08:30 JST の記事を集約して、OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価を実装。
    - 銘柄ごとに記事を結合してトークン肥大対策（最大記事数・最大文字数）を実施。
    - 1チャンク最大 20 銘柄で API コール、JSON Mode を用いた応答バリデーション、スコアの ±1.0 クリップ、部分成功時も既存スコアを保護するための差分 DELETE → INSERT の冪等更新を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx について指数バックオフでリトライ。テスト目的で _call_openai_api を patch 可能。
  - regime_detector:
    - ETF 1321（Nikkei 225 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込みを行う機能を実装。
    - prices_daily からのデータ取り出しはルックアヘッド防止のため target_date 未満のデータのみを使用。OpenAI API 呼び出しは独立実装でモジュール結合を低く保つ。
    - API エラー時はフェイルセーフとして macro_sentiment = 0.0 を使用し処理を継続。

- データプラットフォーム（DuckDB ベース）
  - kabusys.data パッケージを追加（ETL / calendar / pipeline 等）。
  - calendar_management:
    - market_calendar テーブルを用いた営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB にデータがない場合は曜日ベースでフォールバック。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
  - pipeline / ETL:
    - ETLResult データクラスを追加して ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約するインターフェースを提供。
    - 差分取得・バックフィル・品質チェックの方針を実装（外部 save_* 関数や quality モジュールとの連携を想定）。
    - データベース存在チェックや最大日付取得等のユーティリティを実装。

- リサーチ / ファクター計算
  - kabusys.research パッケージを追加。以下を提供：
    - calc_momentum: 1M / 3M / 6M リターンと 200 日 MA 乖離率を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（単純平均）、相対ATR、20日平均売買代金、出来高比等の計算。
    - calc_value: raw_financials から最新の財務データを用いた PER, ROE の計算（EPS が 0/欠損時は None）。
    - feature_exploration: calc_forward_returns（将来リターン）, calc_ic（Spearman ランク相関）, factor_summary（統計要約）, rank（同順位は平均ランク）。
  - DuckDB の SQL と標準ライブラリのみで完結する設計。外部ネットワーク呼び出しなし。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー、Slack トークン、各種パス等は Settings を通じて環境変数から取得。必須値が未設定の場合は明示的にエラーを出すことで誤用を減らす設計。

---

注記（実装上の重要な設計・動作）
- ルックアヘッドバイアス対策：AI モジュール・リサーチモジュールは date.today() を直接参照せず、外部から target_date を与える設計。
- 冪等性：market_regime / ai_scores / 各データ保存処理は既存レコードを削除してからINSERTすることで冪等更新を保障（部分失敗時に他コードを保護する実装あり）。
- フェイルセーフ：LLM 呼び出し失敗時は例外を投げずフォールバック値（例: macro_sentiment=0.0）で処理継続する箇所があるため、実行は停止しにくい設計。ただしキー未設定時は明示的に ValueError を raise。
- テスト支援：OpenAI 呼び出し箇所は内部関数を patch して差し替え可能なように実装されている（ユニットテストでのモック容易性を考慮）。

もしリリースノートに追記したい項目（既知の制限、追加したい注意点、導入手順など）があれば教えてください。必要に応じて項目を追加・修正します。