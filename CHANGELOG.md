# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の構成に従っています。  
このファイルは、コードベースから推測される実装・設計の導入を元に作成した初期リリース向けの変更履歴です。

全般的な注意
- 本リリースはパッケージバージョン __version__ = 0.1.0 を基準にしています。
- 日付はコード解析時点（2026-03-29）を採用しています。
- 記載はコード内のモジュール・関数・設計方針・フェイルセーフ等から推測した機能・改善点です。

Unreleased
- (なし)

[0.1.0] - 2026-03-29
Added
- パッケージ基盤を追加
  - パッケージ名: kabusys（src/kabusys）。__init__.py にてサブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境変数/設定管理 (src/kabusys/config.py)
  - Settings クラスを導入し、環境変数から主要設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を取得する公開 API を提供。
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理
    - クォートなし値におけるインラインコメント認識（直前が空白/タブの場合）
  - 必須環境変数取得時に未設定なら ValueError を発生させる _require を提供。
  - KABUSYS_ENV / LOG_LEVEL の検証と is_live/is_paper/is_dev ヘルパーを提供。
  - デフォルト値（KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を設定。
- ニュースNLP（AI）モジュール (src/kabusys/ai/news_nlp.py)
  - score_news(conn, target_date, api_key=None) を実装。raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON モードでバッチ評価し、結果を ai_scores テーブルへ書き込む。
  - JST 時刻ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC 変換）を calc_news_window で提供。
  - バッチ処理（銘柄ごとに最大 _BATCH_SIZE=20）、記事トリム（最大記事数・最大文字数）を実装。
  - API のリトライ（RateLimit, 接続断, タイムアウト, 5xx）を指数バックオフで行うロジックを実装。非リトライ系エラーはスキップして継続（フェイルセーフ）。
  - レスポンス検証機構を実装（JSON復元処理、results 配列検査、コード/数値検証、スコアの ±1.0 クリップ）。
  - テスト容易性のため _call_openai_api を差し替え可能に実装。
  - DB 書き込みは冪等（対象コードのみ DELETE → INSERT）で実施、DuckDB の executemany の空パラメータ制約を考慮した実装。
- 市場レジーム判定（AI）モジュール (src/kabusys/ai/regime_detector.py)
  - score_regime(conn, target_date, api_key=None) を実装。ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、market_regime テーブルへ保存。
  - マクロニュース抽出（キーワードベース）と LLM 呼び出し（gpt-4o-mini JSON mode）、結果パース、リトライ/フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
  - ルックアヘッドバイアス防止のため、データフェッチ・集計は target_date 未満・以前のみ参照する方針を徹底。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作。例外時の ROLLBACK ハンドリングを実装。
- 研究（Research）モジュール (src/kabusys/research)
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を基に各種ファクター（モメンタム、MA200乖離、ATR、流動性、PER, ROE 等）を算出。
  - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（Spearman rank IC）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。外部ライブラリに依存せず標準ライブラリ + DuckDB で完結する設計。
  - zscore_normalize を data.stats から再エクスポート。
- データ・カレンダー管理 (src/kabusys/data/calendar_management.py)
  - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ロジックを実装。
  - market_calendar が未取得の場合は曜日ベース（平日を営業日）でフォールバックする設計。
  - calendar_update_job による J-Quants からの差分取得・バックフィル（直近 _BACKFILL_DAYS）・健全性チェック（未来日付の異常検出）を実装。jquants_client 経由で fetch/save を呼び出す。
- ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult dataclass を導入（取得数/保存数/品質問題/エラー等を保持）。to_dict() で品質問題を簡易表現に変換。
  - 差分更新・バックフィル・品質チェック方針を備えた ETL 設計を反映（jquants_client と quality モジュールを利用する想定）。
  - data.etl モジュールで ETLResult を公開。
- データ関連ユーティリティ
  - DuckDB の日付変換やテーブル存在チェック、最大日付取得等のユーティリティ実装（_table_exists, _get_max_date, _to_date など）。
- ロギングとフォールバック
  - 重要な操作や例外について logger に情報/警告/例外を残す実装を各所に追加。
  - API 呼び出し失敗時のフェイルセーフ（スコア0.0 で継続、部分的な DB 保護）を優先する堅牢設計。

Changed
- （初出のため該当なし）

Fixed
- トランザクション失敗時に ROLLBACK を試行し、さらに ROLLBACK 自体の失敗を警告ログに出すことでデータベース例外時の調査性を向上。
- DuckDB の executemany に空リストを渡さないようガードを追加（互換性のため）。

Deprecated
- （初出のため該当なし）

Removed
- （初出のため該当なし）

Security
- 環境変数（APIキー・Slackトークン等）は必須チェックを行い、未設定時には ValueError を発生させることで誤動作を防止。
- .env の自動ロードは保護された OS 環境変数を上書きしない仕組み（protected set）を採用。

Notes / Implementation Notes（設計上の重要ポイント）
- ルックアヘッドバイアス防止:
  - 各 AI / 研究処理で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す方式を採用。
  - DB クエリでも target_date 未満・以前のみを参照する等の対策を実施。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api 等）は unittest.mock.patch により差し替え可能に実装。
  - api_key は明示引数で注入可能（テスト時に環境変数に依存しない）。
- 冪等性:
  - DB 書き込みは対象行の DELETE → INSERT や ON CONFLICT 相当の方法で冪等化を図る。
  - 部分失敗が発生しても他のコードの既存スコアを消さないよう、書き込み対象を限定している。
- リトライ戦略:
  - OpenAI 呼び出しに対しては 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
  - 非 5xx の APIError は再試行せずフェイルセーフ挙動（スキップ・0.0 フォールバック）とする。
- タイムゾーン:
  - news ウィンドウ等は明示的に JST 基準 → UTC naive datetime に変換して DB 比較する設計。全て date / datetime を naive に扱うことを明記している。

今後の想定（参考）
- strategy / execution / monitoring パッケージにて実際の売買ロジック・注文送信・監視アラートが実装される想定。
- より詳細な品質チェック（quality モジュール）や jquants_client の具象実装、Slack 通知の実装が継続して追加される可能性あり。

--- 

この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートをご希望の場合は、Git のコミットメッセージ等の実データを提供してください。