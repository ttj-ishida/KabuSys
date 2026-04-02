Keep a Changelog
=================
このファイルは「Keep a Changelog」形式に準拠しています。  
リリースはセマンティックバージョニングを用います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-02
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
- パッケージメタ:
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - public API: data, strategy, execution, monitoring を __all__ に公開
- 設定/環境変数管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 探索）から自動読み込みする機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサー: export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理（クォートあり/なしでの挙動の差分）に対応。
  - .env 読み込み時に OS の既存環境変数を保護する protected キーセットをサポート。override オプションあり。
  - Settings クラスを実装し、アプリで利用する主要設定値をプロパティとして提供（J-Quants、kabuステーション、Slack、データベースパス、監視パラメータ、環境/ログレベル判定など）。必須環境変数未設定時は _require で明示的に例外を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値セット）を実装。is_live / is_paper / is_dev の簡易プロパティを提供。
- AI 関連 (kabusys.ai)
  - ニュースNLP (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news/news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出。結果を ai_scores テーブルへ冪等的に書き込む処理を実装。
    - ニュース時間ウィンドウ計算 calc_news_window を実装（JST基準の前日15:00〜当日08:30 を UTC に変換）。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数/文字数のトリム、JSON レスポンスのバリデーション、スコアの ±1.0 クリッピング、部分失敗時に他銘柄データを保護する更新ロジックを実装。
    - リトライと指数バックオフ（429/ネットワーク/タイムアウト/5xx）、OpenAI 呼び出しのラッパー、レスポンス JSON の前後余分テキストに対する復元ロジックを実装。
    - DuckDB の executemany 空リスト制約（バージョン互換）への対処（空リストは実行しない）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime テーブルに書き込む処理を実装。
    - MA200 計算（ルックアヘッド防止のため target_date 未満データのみ使用、200 行未満は中立 1.0 を採用して警告ログ出力）。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0 にフォールバック）、スコアの閾値に基づくラベル化（bull/neutral/bear）を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。ロールバック時のログ処理。
- リサーチ/ファクター解析 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum(conn, target_date): 1M/3M/6M リターンと ma200_dev（200日 MA 乖離率）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。データ不足時は None を返す。
    - calc_value(conn, target_date): raw_financials と prices_daily を組み合わせて PER、ROE を計算（EPS 欠損/0 の場合は None）。
  - feature_exploration モジュール:
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズンの将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク相関）による IC 計算。データ不足時は None。
    - rank(values), factor_summary(records, columns): ランキングと統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージの __init__ で主要関数を再公開。
  - data.stats の zscore_normalize を再利用可能にした export を用意。
- データ/ETL/カレンダー (kabusys.data)
  - calendar_management:
    - 市場カレンダーの判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末は非営業日）を行い、一貫した振る舞いを保証。
    - calendar_update_job(conn, lookahead_days): J-Quants API（jquants_client 経由）から差分取得して market_calendar を冪等更新。バックフィル、健全性チェック、例外ハンドリングを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーの集約、has_errors / has_quality_errors / to_dict を提供）。
    - ETL の設計方針に関する実装ノート（差分更新・バックフィル・品質チェックの扱い・id_token 注入可など）。
    - data.etl で ETLResult を再エクスポート。
  - DuckDB に対する互換性配慮（テーブル存在チェック、日付変換ユーティリティなど）を多数実装。
- テスト容易性の考慮:
  - OpenAI 呼び出し関数を内部で分離（_call_openai_api）して unittest.mock.patch により差し替え可能に実装。
  - 各種フェイルセーフ（API エラー時のフォールバック）やログ出力を多用して運用しやすく設計。

Changed
- 日付取り扱い方針の明文化: LLM 評価・ETL・スコア計算等の関数は内部で datetime.today()/date.today() を直接参照せず、必ず target_date を引数で受けてルックアヘッドバイアスを防止する設計を採用。
- OpenAI レスポンスパースの堅牢化: JSONDecodeError 時に文字列中の最外層の {} を抽出して復元を試みるロジックを追加（news_nlp 側）。
- DuckDB 互換性: executemany に空リストを投げない実装に変更（実行前に空チェック）。
- .env パーサーの強化: クォート中のエスケープ、export プレフィックス、コメント判定ロジックを実装しより多くの .env パターンに対応。

Fixed
- データ不足時の安全なフォールバック:
  - ETF 1321 のデータが不足する場合、ma200_ratio を中立値 1.0 として処理を継続する実装を追加（regime_detector）。
  - ニュース対象ゼロ件の場合、LLM 呼び出しを行わず 0 スコア（neutral）を返すようにした（news_nlp / regime_detector）。
- OpenAI API 呼び出し時のリトライロジック:
  - RateLimitError / 接続エラー / タイムアウト / 5xx を対象に指数バックオフで再試行し、最終的に失敗した場合は安全側のデフォルト値で継続する挙動に統一。
- DB 書き込みの冪等性確保:
  - ai_scores / market_regime への書き込みで DELETE → INSERT の手順を採用し、部分失敗時に既存データを不必要に削除しないように設計。
- 環境変数未設定時の明確なエラー: OpenAI API キーや必須トークンが未設定の場合、ValueError で明確にエラーを通知するようにした。

Notes
- 現状外部依存: OpenAI（gpt-4o-mini）と J-Quants API クライアント（kabusys.data.jquants_client）への依存がある。テスト時は API 呼び出し部分をモックすることを想定。
- ロギング: 各処理で情報・警告・例外ログを出力する設計（運用時の監視/デバッグに有利）。
- 破壊的変更: なし（初回リリース）。
- 未実装/今後の候補: PBR・配当利回りなどのバリューファクター追加、strategy / execution 実装の拡充、より詳細な品質チェックルールの追加。

脚注
- 上記はソースコードの構成・実装コメントと docstring から推測して作成した変更履歴です。実際のリリースノート作成時はコミットログ・issue トラッキング情報に基づく追記を推奨します。