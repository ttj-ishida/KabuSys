# CHANGELOG

すべての重要な変更をこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。  
初期リリース相当の状態を、コードベースから推測して記載しています。

注: 日付はコード解析時点の想定日です（2026-03-31）。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31

### Added
- パッケージ概要
  - kabusys パッケージを導入。日本株の自動売買 / データ処理 / 研究用ユーティリティ群を提供するモジュール群を含む。
  - パッケージバージョン: 0.1.0

- 環境変数・設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）または OS 環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。
  - Settings クラスで主要設定をプロパティとして提供（J-Quants, kabuAPI, Slack, DB パス, 監視閾値, 環境フラグ等）。
  - 必須環境変数未設定時は明示的な ValueError を発生させる _require を提供。
  - KABUSYS_ENV, LOG_LEVEL の値検証（許容値セットを定義）。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols をソースに、銘柄ごとのニュース集合を集約して OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST （UTC に変換して比較）。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数/文字数制限（トリム）、レスポンス検証、スコア ±1.0 クリップ。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ。
    - レスポンスの頑強なパース（JSON mode の余計な前後テキストへの耐性）と未知コード無視ロジック。
    - フェイルセーフ: API エラー時は該当チャンクをスキップし処理継続。
    - DuckDB executemany の互換性考慮（空リスト処理回避）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出はマクロキーワード（日本・米国など主要語）でフィルタ。
    - OpenAI 呼び出しは専用関数に分離、リトライ/バックオフ、フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアス対策: internal で date.today()/datetime.today() を参照しない設計。prices_daily クエリは target_date 未満のデータのみ使用。

- Data / ETL（kabusys.data）
  - ETL インターフェース（etl.py）: pipeline.ETLResult を公開。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラス（取得数・保存数・品質問題・エラーの集約）を実装。品質問題の辞書化メソッド to_dict を提供。
    - 差分取得 / バックフィル / 品質チェックの設計方針を反映したユーティリティ関数群を実装（テーブル存在チェック、最大日付取得等）。
    - DuckDB を前提とした互換性・例外ハンドリングを組み込む。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定、next/prev_trading_day, get_trading_days, is_sq_day を実装。
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得・冪等保存・バックフィル・健全性チェック）。
    - DB にデータがない/未登録日の場合は曜日ベースのフォールバック（土日非営業日扱い）。
    - 探索範囲上限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。

- Research / ファクター計算（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200日MA乖離、ATR（20日）、20日平均売買代金・出来高変化率、PER/ROE（raw_financials 参照）などの計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL ウィンドウ関数を活用して営業日ベースで計算。データ不足時は None を返す挙動。
    - 設計上、外部 API に依存せず prices_daily / raw_financials のみ参照。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの将来終値からリターンを計算（複数ホライズン対応、入力チェックあり）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランク処理と同順位の平均ランク対応）。
    - ランク変換ユーティリティ（rank）。統計サマリ（factor_summary）: count/mean/std/min/max/median を計算。
    - 外部ライブラリに依存しない純 Python 実装（DuckDB のみ利用）。

- パッケージ API エクスポート
  - 複数サブパッケージを __all__ で公開（data, strategy, execution, monitoring 等。いくつかのサブモジュールは実装の一部を含む）。

### Changed
- （初期リリースのため過去からの変更事項なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Deprecated
- なし

### Removed
- なし

### Security
- なし特記事項。ただし OpenAI API キーや各種トークンは環境変数で管理する想定。

## 既知の制約・注意事項（使用時のポイント）
- OpenAI API
  - news_nlp / regime_detector は OpenAI の API（gpt-4o-mini）を利用するため、OPENAI_API_KEY の設定が必須。api_key を引数で直接渡すことも可能。
  - API レートや障害に対してリトライ・バックオフを実装しているが、コストやレート制限には留意してください。
- 環境変数（主な必須キー）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- DuckDB 前提
  - 多くの処理は DuckDB 接続およびテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）を前提にしています。テーブルスキーマ・存在を確認の上利用してください。
- ルックアヘッドバイアス対策
  - AI スコアリング・レジーム判定・将来リターン計算などは内部で現在日時を直接参照せず、明示的な target_date を受け取る設計です（バックテストや再現性の担保に有利）。
- DuckDB executemany の互換性
  - 一部処理は DuckDB のバージョン差を考慮した回避実装（空パラメータの executemany を避ける等）を行っています。

---

（注）本 CHANGELOG は提供されたコードの実装内容から推測して作成したものです。実際のリリースノートやバージョン管理履歴がある場合はそちらを優先してください。