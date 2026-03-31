CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 以下は提示されたソースコードから機能・設計方針を推測して作成した変更履歴です。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - モジュール構成を公開:
    - kabusys.config: 環境変数 / .env 管理（自動ロード・保護機能・必須キー検査）
    - kabusys.ai:
      - news_nlp.score_news: ニュース記事を集約して OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを算出し ai_scores テーブルへ書き込むバッチ処理。
      - regime_detector.score_regime: ETF (1321) の 200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
      - 両モジュールとも OpenAI 呼び出し用の内部ラッパーを提供し、テスト時に差し替え可能な設計。
    - kabusys.data:
      - calendar_management: JPX カレンダーの管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）および夜間アップデートジョブ（calendar_update_job）。DB 登録値優先だが未登録日は曜日ベースでフォールバック。
      - pipeline / etl: ETL の公開 API（ETLResult）と ETL パイプラインのユーティリティ（差分取得・バックフィル・品質チェック方針）。
      - jquants_client を利用したカレンダー取得・保存（実装箇所は参照）。
    - kabusys.research:
      - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR 等）、バリュー（PER, ROE）等のファクター算出関数（calc_momentum, calc_volatility, calc_value）。
      - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）などの分析ユーティリティ。
    - kabusys.data.etl: ETLResult を再エクスポート。
  - パッケージメタ:
    - バージョン: 0.1.0（src/kabusys/__init__.py）

Added — 実装上の主要な振る舞い・設計方針
- DuckDB を主要な分析データベースとして利用。各分析/ETL/カレンダー処理は DuckDB 接続を受け取る設計。
- ルックアヘッドバイアス防止:
  - 日次判定ロジック（news/ regme / research 関数）は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満／指定範囲でフィルタすることで将来データを使用しないよう配慮。
- OpenAI API 呼び出し:
  - gpt-4o-mini を使用し JSON モードでレスポンスを期待するプロンプトを使用。
  - レート制限・接続断・タイムアウト・5xx 等に対するエクスポネンシャルバックオフのリトライ実装（最大試行回数設定あり）。API 失敗時はフェイルセーフによりスコアをデフォルト値（0.0）にフォールバックし処理継続。
  - テスト容易性のため API 呼び出し関数をモジュール内で独立実装しており、unittest.mock.patch により差し替え可能。
- .env / 環境変数管理:
  - プロジェクトルート検出（.git または pyproject.toml を上位ディレクトリから探索）に基づいて .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - OS 環境変数（既存の os.environ）を保護する機能（protected set）あり。.env.local は override=True でローカル上書き可能。
- DB 書き込みの冪等性とトランザクション管理:
  - ai_scores / market_regime / market_calendar 等への書き込みは BEGIN / DELETE / INSERT / COMMIT を組み合わせた冪等的手順。
  - 例外発生時は ROLLBACK を試み、失敗ログを記録して上位へ例外伝播する。

Fixed / Improved (実装上の堅牢性)
- .env パースの頑健化（空行／コメント／export 形式／クォート内のエスケープ処理／インラインコメント除去）。
- OpenAI レスポンスの JSON パース失敗時の復元処理（news_nlp の _validate_and_extract で文字列中の最外側 {} を抽出して再パースを試行）。
- API エラー種別に応じたログ・リトライ制御（RateLimitError / APIConnectionError / APITimeoutError と、APIError の status_code に基づく振る舞いを区別）。
- DuckDB executemany に関する互換性配慮（空リスト渡しを避けるチェック）。

Documentation / Notes
- 各モジュールの docstring に設計方針・処理フロー・フェイルセーフ挙動を明記。
- AI 用システムプロンプトは厳密な JSON 出力を要求するように設計（レスポンスバリデーション前提）。

Removed
- （なし）

Security
- OpenAI API キーの取り扱いは環境変数（OPENAI_API_KEY）または明示的引数経由を想定。必須チェックを実装しており未設定時は ValueError を送出。

Breaking Changes
- （初期リリースのためなし）

Notes / 今後の考慮点（ソースコードからの推測）
- jquants_client の実装に依存する箇所（データ取得/保存）は存在するため、外部 API クレデンシャル・レスポンス仕様に依存する。
- DuckDB バージョンによるバインド挙動の違いを意識して実装されている（executemany の空パラメータ回避等）。
- 将来的に ai スコアの正規化・スキーマ変更・追加の品質チェックが必要になり得る。