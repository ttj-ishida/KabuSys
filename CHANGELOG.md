Keep a Changelog に準拠した変更履歴

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

[0.1.0] - 2026-04-04
====================

Added
-----
- 基本パッケージ初期リリース。
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - パッケージ公開APIに data, strategy, execution, monitoring を含める（__all__）。

- 環境変数・設定管理（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動検出して読み込む自動ロード機能を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env（.env.local は上書き可）。
  - Settings クラスを提供。J-Quants / kabu / LINE / DB パス / 監視・閾値設定 / システム環境（KABUSYS_ENV）や LOG_LEVEL の検証を含む便利プロパティ群を公開。

- ニュースNLP（src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py）
  - raw_news / news_symbols に基づいて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを算出して ai_scores テーブルへ書き込む機能を実装（score_news）。
  - タイムウィンドウ計算（calc_news_window）、記事収集(_fetch_articles)、チャンク処理(_score_chunk)、レスポンス検証(_validate_and_extract) を含む。
  - バッチ処理（最大20銘柄 / チャンク）、トークン肥大対策（記事数・文字数上限）、エクスポネンシャルバックオフ付きリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を実装。
  - JSON レスポンスの前後余分テキスト対策（最外の {} を抽出して復元）やスコアクリップ（±1.0）など堅牢化ロジックを導入。
  - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（"bull" / "neutral" / "bear"）を判定し market_regime テーブルに冪等書き込みする機能を実装（score_regime）。
  - MA200 計算(_calc_ma200_ratio)、マクロ記事抽出(_fetch_macro_news)、OpenAI 呼び出し実装(_call_openai_api)、マクロスコア算出(_score_macro) を含む。
  - API エラー時のフォールバック（macro_sentiment=0.0）、エクスポネンシャルバックオフリトライ、JSON パースエラーハンドリングを備える。
  - lookahead バイアス防止（target_date 未満のみを使用）や冪等 DB 更新（BEGIN/DELETE/INSERT/COMMIT）を採用。

- リサーチ（src/kabusys/research/*.py, src/kabusys/research/__init__.py）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（calc_momentum）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比（calc_volatility）。
    - バリュー: PER、ROE（raw_financials から最終報告を取得）（calc_value）。
    - DuckDB SQL を活用した効率的実装。データ不足時は None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を提供。
    - horizons の検証、重複排除、パフォーマンス配慮（1クエリで取得）を実装。
  - research パッケージで主要関数を再エクスポート（__all__）。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）と営業日判定・探索ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。DB 値優先、未登録日はフォールバックで一貫した挙動を実現。
    - 安全策（最大探索日数制限、バックフィル、健全性チェック）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを定義（取得数・保存数・品質チェック・エラー一覧などを保持）。etl.py で ETLResult を公開再エクスポート。
    - 差分取得・バックフィル・品質チェック方針を文書化し、内部ユーティリティ（テーブル存在チェック、最大日付取得等）を実装。
    - DuckDB を前提とした互換性配慮（executemany に空リストを渡さない等）の注記を実装。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- 環境変数読み込み、OpenAI レスポンス処理、DB 書き込みに関する堅牢性向上を実施。
  - .env 読み込み時の I/O エラーは警告ログにフォールバックして処理継続。
  - OpenAI 呼び出しでの RateLimit / 接続エラー / タイムアウト / 5xx に対するリトライとログ出力を導入。最終的に失敗した場合はフェイルセーフな既定値（0.0）で継続。
  - OpenAI の JSON 応答が前後テキストを含むケースへ復元処理を追加。
  - DuckDB への複数行 DELETE/INSERT の際、executemany へ空リストを渡さない安全チェックを実装（DuckDB 互換性対策）。

Security
--------
- （公開 API キーや本番発注機能はこのリリースで直接操作しない設計。OpenAI API キーは引数で注入可能または環境変数 OPENAI_API_KEY を利用する。設定漏れ時は ValueError を送出して明示的に失敗させる。）

Known issues / Notes
--------------------
- OpenAI 依存:
  - 実行には openai（OpenAI SDK）と DuckDB が必要。テスト用に _call_openai_api をモックすることを想定。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになるバージョンがあるため、その回避コードを実装済み。
- lookahead バイアス防止:
  - すべての AI / リサーチ処理は内部で datetime.today() や date.today() を参照しない設計。ただし利用側は target_date を正しく与えること。
- 部分失敗時のデータ保護:
  - ai_scores / market_regime 等への書き込みは「既存の無関係データを消さない」方針（書き込み対象コードだけを DELETE → INSERT）で実装。

BREAKING CHANGES
----------------
- 初回リリースのため該当なし

開発者向け補足
--------------
- テスト時の環境変数自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しをモックする場合は、news_nlp/regime_detector の _call_openai_api を unittest.mock.patch で差し替えることを推奨します。
- DuckDB 接続は各関数に注入する形（引数 conn）を採用しているため、テスト時はメモリ上の DuckDB 接続等で容易に検証できます。

----- 

（以降のリリースでは機能追加・バグ修正・互換性変更をこのファイルに記載してください）