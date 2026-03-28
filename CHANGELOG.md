Keep a Changelog に準拠した CHANGELOG.md（日本語）

全体方針:
- フォーマット: Keep a Changelog（https://keepachangelog.com/ja/）準拠
- 日付: 2026-03-28（初回公開バージョン 0.1.0 のリリース日）
- 本リリースはソースコードから推測した初期実装の概要を記載しています。

フォーマット例や英語見出しは日本語化してあります。

Unreleased
- なし

[0.1.0] - 2026-03-28
Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。バージョンは 0.1.0。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__ によりエクスポート）。

- 設定管理 (.env / 環境変数)
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、主要設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev の便利プロパティ

- Data（データ基盤）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブル利用）。
    - 営業日判定・探索ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - カレンダー未取得時は曜日ベース（土日を非営業日）でフォールバックする一貫した振る舞い。
    - calendar_update_job: J‑Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェック機構あり。
    - 最大探索日数や先読み日数などの安全パラメータを設定（_MAX_SEARCH_DAYS, _CALENDAR_LOOKAHEAD_DAYS 等）。
  - ETL / pipeline:
    - ETLResult データクラス（target_date, fetched/saved カウント、quality_issues, errors 等）を公開。
    - ETLResult.to_dict により品質問題をシリアライズ可能。
    - DuckDB を想定したユーティリティ（テーブル存在確認、最大日付取得等）を実装。
    - 差分更新・バックフィル・品質チェックを想定した設計（実装の呼び口を提供）。

- AI / 自然言語処理
  - news_nlp モジュール:
    - calc_news_window: ニュース収集ウィンドウ計算（JST に基づく前日 15:00 ～ 当日 08:30 → UTC 変換）。
    - score_news: raw_news と news_symbols から記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode でバッチ評価して ai_scores テーブルに書き込む。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり最大記事数・文字数トリム、レスポンス検証、±1.0 クリップ、DuckDB 互換性のための executemany 空リスト対策などを実装。
    - API 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx）、指数バックオフ、失敗時はスキップかつフェイルセーフ（例外を上位に投げない）。
    - レスポンスの JSON パース堅牢化（前後余計なテキストが混在する場合の {} 抽出処理）。
    - テスト容易化のため _call_openai_api の差し替えポイントを用意（unittest.mock.patch を想定）。
  - regime_detector モジュール:
    - ETF（コード 1321）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200 比率計算、マクロキーワードでのニュース抽出、OpenAI 呼び出し（gpt-4o-mini / JSON mode）、リトライ・バックオフ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）する実装。

- Research（因子・特徴量）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足は None。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。真のtrue_range は high/low/prev_close の NULL を尊重。
    - calc_value: raw_financials から直近財務データと株価を組み合わせて PER/ROE を算出（EPS が 0/欠損の場合は None）。
    - DuckDB による SQL+ウィンドウ関数で実装。外部 API にはアクセスしない設計。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証と 1 クエリ取得による効率化。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効データが 3 件未満なら None）。
    - rank: 同順位は平均ランクとするランク関数（丸めを用いて ties の漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数読み込みで OS 環境を保護するため protected キー集合を使用（.env の上書き制御）。
- API キー等の必須値は Settings の _require 経由で取得し、不在時は明示的なエラーを発生させる（漏洩防止のため値をログに出力しない前提）。
- OpenAI の API 呼び出しはタイムアウト・リトライ制御あり。API 失敗時はデフォルトで安全な値にフォールバックして継続する設計。

Notes / Design decisions（実装上の留意点）
- ルックアヘッドバイアス対策:
  - datetime.today() や date.today() を判定処理の内部で用いない設計（target_date を明示的に渡す）。
  - prices_daily のクエリでは date < target_date といった排他条件を用いるなど、将来データ参照を防止。
- 時刻・タイムゾーン:
  - news ウィンドウは JST 基準で定義し、内部では UTC naive datetime を用いる（DB の raw_news.datetime は UTC で保存されている前提）。
- DuckDB 互換性:
  - executemany に空リストを渡せない（DuckDB 0.10 の制約）ため、空チェックを行ってから実行。
  - テーブル存在チェックや日付の変換ユーティリティを提供。
- テスト性:
  - OpenAI 呼び出し箇所に差し替えポイント（_call_openai_api）を提供し、ユニットテストで外部呼び出しをモック可能。
- エラーハンドリング:
  - LLM レスポンスのパース失敗や API エラーは例外を上位に投げずロギングしてフォールバックする箇所が多く、運用継続性を重視。

Known issues / Limitations
- strategy, execution, monitoring モジュールは __all__ で公開されているが、今回提供されたソース一覧ではその具体実装が含まれていない（今後追加想定）。
- pipeline や ETL の外部依存（jquants_client, quality モジュール）の実装は別モジュールに委譲されており、本リリースではインターフェース側の実装が中心。
- 一部ファイル（例: pipeline の最後）が切れているため、未完の内部ヘルパ等が存在する可能性あり。

作者・貢献
- 本 CHANGELOG はリポジトリ内のソースコードから自動推測して作成しています。実際のリリースノート作成時はコミット履歴や開発者の意図に基づく追記を推奨します。

ライセンス
- ソースコード内に明示的なライセンス表記がないため、実際の配布時は適切なライセンスファイルを追加してください。

--- 
（以上）