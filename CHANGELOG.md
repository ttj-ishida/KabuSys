KEEP A CHANGELOG
すべての重要な変更を記録します。これは Keep a Changelog の形式に準拠しています。
リリース日はソースコードのバージョン (kabusys.__version__ = 0.1.0) に合わせて記載しています。

Unreleased
- （現時点のリポジトリは初期リリースのみのため未使用）

0.1.0 - 2026-03-28
Added
- パッケージの初期リリースを追加。
  - src/kabusys/__init__.py にてパッケージ名と __version__ を公開。
  - __all__ に data, research, ai, strategy, execution, monitoring 等のサブパッケージ名を宣言（将来拡張を想定）。
- 環境設定・自動 .env 読み込み機能を実装（src/kabusys/config.py）。
  - プロジェクトルートの検出: .git または pyproject.toml を起点に探索する _find_project_root を実装し、CWD に依存しない自動読み込みを実現。
  - .env 形式の堅牢なパーサー _parse_env_line を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - .env と .env.local の読み込み優先順位を実装。OS 環境変数を保護する protected 機能を持つ _load_env_file を提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能。
  - Settings クラスを追加し、J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等のプロパティを提供（未設定時に ValueError を送出する必須取得メソッド _require を利用）。
  - env 値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。
- AI モジュールを追加（src/kabusys/ai/*）。
  - news_nlp.score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。チャンク処理、最大文字数制限、最大記事数制限、バッチサイズ制御を実装。API リトライ（429/ネットワーク/5xx）とレスポンス検証・クリッピング（±1.0）を備える。
  - regime_detector.score_regime: ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み合成して market_regime テーブルへ冪等書き込み。OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
  - 共通設計方針として「datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）」を徹底。
  - OpenAI 呼び出しのラッパー _call_openai_api を個別実装し、テストで差し替え可能（unittest.mock.patch を想定）。
- データ処理・Research モジュールを追加（src/kabusys/data/*, src/kabusys/research/*）。
  - data.pipeline.ETLResult: ETL の実行結果を格納するデータクラスを提供（品質問題・エラー集約、to_dict メソッド等）。
  - data.pipeline: ETL の差分取得・バックフィル・品質チェック方針を反映するユーティリティ群（テーブル存在チェック、最大日付取得等）。
  - data.calendar_management: JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB に存在する場合は DB 値優先、未登録日は曜日ベースのフォールバックを採用。最大探索範囲の上限や健全性チェックを導入。
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算関数（calc_momentum, calc_volatility, calc_value）を提供。DuckDB 上で SQL＋Python による計算を行う（prices_daily, raw_financials を参照）。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク付け（rank）、統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ で主要関数を再エクスポート。
- データ ETL インターフェースの公開（src/kabusys/data/etl.py）で ETLResult を再エクスポート。

Changed
- 初期実装のため該当なし（新規追加リリース）。

Fixed / Robustness
- OpenAI 呼び出し失敗時のフォールバックを明確化。
  - news_nlp と regime_detector の両方でリトライ（指数バックオフ）と、最終的に API 呼び出しに失敗した場合は部分スキップまたは 0.0 フォールバックを行い、例外を上位に波及させない（ただし DB 書込みでの例外時はロールバックして伝播）。
- DuckDB 互換性考慮:
  - executemany に空リストを渡すと失敗する点を回避するため、事前に空チェックを行ってから executemany を呼ぶ実装に調整（score_news の書き込みロジック等）。
  - 日付値の DuckDB からの戻り値を安全に date に変換するユーティリティ _to_date を追加。
- .env パーサーの堅牢化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、空行／コメント行の無視などをサポート。
  - OS 環境変数を保護する protected 引数により自動読み込みで既存の OS 環境を上書きしない安全な動作を実現。
- calendar_update_job の健全性チェックを追加。market_calendar の last_date が極端に未来の場合は処理をスキップして警告。

Security
- 環境変数自動読み込み時に OS 環境変数を保護（protected set）し、重要な既存変数が意図せず上書きされないように実装。
- OpenAI API Key の未設定は ValueError を投げて明示的にエラー報告（score_news / score_regime）。

Known limitations / Notes
- OpenAI 依存:
  - gpt-4o-mini の JSON Mode を利用する設計だが、モデルや SDK の変更（レスポンス形式の変化等）に対しては将来の調整が必要。
- タイムゾーン取り扱い:
  - news ウィンドウは JST を基準に計算し、DB 比較用に UTC-naive datetime を返す（コード内で明示的に説明あり）。外部システムとのインターフェースで誤解が起きないよう注意が必要。
- 「ルックアヘッドバイアス防止」のため、各スコアリング関数は内部で現在時刻を参照せず、呼び出し側から target_date を受け取る API 設計を採用。
- 一部の DB 書込みは冪等（DELETE → INSERT / ON CONFLICT 予定）を想定しているが、実運用でのスキーマ・インデックス・パフォーマンス観点から追加の調整が想定される。

Contributors
- 初期実装（単一リポジトリ内の複数モジュール追加）によるリリース。

Appendix
- 追加 / 変更を行う際は以下を意識してください:
  - テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境依存性を切り離す。
  - OpenAI 呼び出しラッパーはテストで差し替え可能（unittest.mock.patch を想定）。
  - DuckDB バージョン互換性（executemany の振る舞い等）に注意。

--- 
（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして使用する場合は、開発履歴・コミット差分を確認のうえ必要に応じて追記・修正してください。）