# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本CHANGELOGは与えられたコードベース（初期リリース想定）から推測して作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初期リリース。システム全体のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys Python パッケージを公開。バージョンを __version__ = "0.1.0" と設定。
  - パッケージの公開対象モジュールを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート判定: .git または pyproject.toml）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 構文パーサの実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォート無しでのインラインコメント扱い（直前が空白／タブの場合に '#' をコメントとみなす）
  - 環境変数上書き挙動（.env と .env.local の読み込み優先度）と「保護された」OS環境変数セットを考慮した読み込みロジックを実装。
  - 必須値チェック（_require）や各種プロパティを実装（J-Quants、kabuステーション、Slack、DBパス、監視しきい値、実行環境・ログレベル判定など）。
  - KABUSYS_ENV / LOG_LEVEL の値検証。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）。
    - raw_news と news_symbols を結合して銘柄ごとに記事集約（記事数・文字数上限でトリム）。
    - バッチ送信（1 API コールあたり最大 _BATCH_SIZE=20 銘柄）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフとリトライの実装。
    - OpenAI JSON mode レスポンスの堅牢なバリデーション（余分な前後テキストの復元、結果フォーマット検証、スコアの数値化とクリップ）。
    - テスト用に _call_openai_api を patch して差し替え可能。
    - 部分失敗時に既存スコアを消さない idempotent な DB 書き換え（対象コードのみ DELETE → INSERT）。
  - regime_detector: マクロセンチメントと ETF (1321) の 200 日移動平均乖離を合成して市場レジーム（bull/neutral/bear）を判定・保存する機能を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用、データ不足時は中立扱い）。
    - raw_news からマクロキーワードでフィルタしたニュースタイトルを抽出。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを評価（空記事時は LLM 呼び出しを行わず 0.0 を返す）。
    - API のリトライ（RateLimit / Connection / Timeout / 5xx を考慮）とフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジームスコア合成ロジック（重み: MA 70%、マクロ 30%）、閾値設定、結果の market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - news_nlp と内部の _call_openai_api 実装を共有しない設計（モジュール結合を避ける）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB データ存在時は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に保存する夜間バッチジョブ（バックフィル・健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得件数／保存件数／品質問題／エラー集約）。
    - ETL パイプライン設計（差分更新、保存、品質チェックのフロー）を実装するための基礎を実装。
    - DuckDB を想定したテーブル存在チェック、最大日付取得等のユーティリティ。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily から PER / ROE を算出（EPS が 0 または欠損の場合は None）。
    - DuckDB 上で SQL を駆使して高速に計算する実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得できる実装。入力検証（horizons の制約）あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位に対して平均ランクを与えるランク関数（丸めによる tie の扱いに配慮）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
  - これらリサーチ機能は外部 API を呼ばず、prices_daily / raw_financials 等ローカル DB のみを参照する安全設計。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は明示的に例外を投げることで誤動作を防止。

---

補足（設計上の注意点・テストフック）
- ルックアヘッドバイアス対策: 各モジュールは datetime.today()/date.today() を内部ロジックで直接参照せず、target_date 引数に基づく処理を行うように設計されています。
- OpenAI 呼び出しはテスト容易性のため _call_openai_api を patch して差し替え可能です（news_nlp と regime_detector は独立実装）。
- DuckDB 0.10 の制約（executemany に空リストを渡せない等）へ配慮した実装になっています。
- .env パーサは様々な実用ケース（export付き、クォート、エスケープ、インラインコメント）に対応しています。

もし特定モジュールについてより詳細な CHANGELOG 項目（例: SQL クエリの変更、閾値調整、エラー処理の詳細など）が必要であれば、対象ファイル/関数を指定してください。コードから推測して追記します。