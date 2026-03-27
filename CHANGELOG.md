CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリース v0.1.0
- パッケージのエントリポイントを追加
  - kabusys.__version__ = "0.1.0"
  - kabusys.__all__ を通じて主要サブパッケージを公開（data, research, ai 等）
- 環境設定管理
  - 環境変数／.env ファイル読み込みモジュールを追加（kabusys.config）
  - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
  - .env パーサ実装（export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱い等を考慮）
  - .env 読み込み時に OS 環境変数を保護する protected キー集合のサポート（.env.local が override）
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）をプロパティ経由で取得
  - 必須設定未定義時は明示的な ValueError を送出
  - 有効値チェック（KABUSYS_ENV, LOG_LEVEL）

- AI（OpenAI）関連
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news + news_symbols を用いて銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを取得
    - チャンク（最大 20 銘柄）単位でのバッチ実行、1銘柄あたりの記事数・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - 再試行（429・ネットワーク断・タイムアウト・5xx）用の指数バックオフ実装
    - レスポンスの厳密バリデーション（JSON 抽出、results リスト、既知コードのみ許容、数値チェック）と ±1.0 のクリップ
    - DuckDB 側の互換性考慮（executemany に空リストを渡さないガード）
    - calc_news_window による JST ベースの時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - 日次で市場レジーム（bull / neutral / bear）を判定
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）の合成
    - OpenAI API 呼び出し、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）
    - レジームスコアのクリップ・閾値判定、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）、例外発生時の ROLLBACK ハンドリング
    - LLM 呼び出しはモジュール内専用関数で実装しモジュール結合を低減

- データプラットフォーム（DuckDB を想定）
  - ETL パイプライン関連（kabusys.data.pipeline）
    - ETLResult dataclass（取得数・保存数・品質問題・エラーの集約、to_dict）
    - 差分取得・バックフィル・品質チェックの方針を実装（設計ドキュメントに準拠）
    - DuckDB の最大日付取得ヘルパ等
  - ETL インターフェース再エクスポート（kabusys.data.etl -> ETLResult）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 未整備時の曜日ベースフォールバック（週末は非営業日扱い）
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック（_BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）と冪等保存
    - 最大探索日数制限による無限ループ回避（_MAX_SEARCH_DAYS）

- リサーチ／ファクター
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）等を DuckDB の prices_daily / raw_financials から計算
    - データ不足時の None 扱い、結果を (date, code) ベースの辞書リストで返却
    - スキャン範囲にバッファを持たせ週末・祝日を吸収する実装
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns（任意 horizon の将来リターン）、calc_ic（Spearman ランク相関による IC）、rank（平均ランクでの ties 処理）、factor_summary（基本統計量）
    - pandas 等の外部依存を排し標準ライブラリと DuckDB で実装
    - 入力検証（horizons の範囲チェック等）、統計計算の取り扱い（None の除外、有限値チェック）

Changed
- 設計方針の明確化（コード内ドキュメント）
  - ルックアヘッドバイアス防止の徹底: datetime.today()/date.today() を内部処理で参照しない設計を各モジュールで採用
  - OpenAI 呼び出しのエラー取り扱いとフォールバック戦略を明示

Fixed
- 初回リリースにつき過去のバグ修正履歴はなし

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取り扱いについては環境変数（OPENAI_API_KEY）か関数引数で明示的に渡す方式を採用し、未設定時は ValueError で失敗させることで不意の公開を防止

Notes / 実装上の注意
- DuckDB のバージョン間差異（executemany に空リストを渡せない等）に配慮した実装を行っています。運用環境で使用する DuckDB のバージョンに応じた確認を推奨します。
- OpenAI 呼び出し部分はテスト容易性のため内部関数（_call_openai_api）を経由しており、unittest.mock.patch による差し替えが可能です。
- .env の自動ロードはプロジェクトルート検出に依存します（配布後の動作を考慮して __file__ を起点に探索します）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

--- 

今後のリリースでは、API 実行部分の追加テストカバレッジ、より詳細な品質チェックルール、実戦用の Execution / Monitoring サブパッケージの公開などを予定しています。