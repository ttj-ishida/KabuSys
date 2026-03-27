Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-27
--------------------

初回リリース。日本株自動売買プラットフォームの基礎機能を実装しました。主な追加点は以下のとおりです。

Added
- パッケージ基盤
  - kabusys パッケージ初期化。__version__ = 0.1.0、主要サブパッケージを __all__ で公開。
- 環境設定（kabusys.config）
  - .env および .env.local を自動読み込みする仕組みを実装（プロジェクトルートは .git / pyproject.toml から探索）。
  - 複雑な .env 行のパース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理）。
  - 自動ロードの無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスで主要設定をプロパティとして提供（J-Quants / kabu ステーション / Slack / DB パス / 環境・ログレベル判定）。
  - 環境変数未設定時に明確なエラーを発生させる _require ユーティリティ。
  - env / log_level の妥当性検査（許容値セットによる検証）。
- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini、JSON Mode）でセンチメント評価し、銘柄単位の ai_score を ai_scores テーブルへ書き込む。
    - ニュース収集ウィンドウは JST ベースで定義（前日 15:00 ～ 当日 08:30、内部は UTC naive datetime）。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの最大記事数・文字数制限でトークン肥大化に対応。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・code/score の検査、スコアの数値化とクリップ）。
    - DuckDB との互換性考慮（executemany の空パラメータ回避、ai_scores の部分置換戦略）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - regime_detector: ETF 1321（日経225連動）200日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily と raw_news を参照して ma200_ratio とマクロ記事抽出を行い、OpenAI でセンチメントを取得。
    - レジームスコア合成、ラベル付与、market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - ルックアヘッドバイアス回避のため日付の扱いに注意（datetime.today()/date.today() を参照しない方針）。
- Data モジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末は非営業日）。
    - データがまばらな場合でも DB 値優先・未登録日は曜日フォールバックを一貫して使用。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得・バックフィル・健全性チェックを実施。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧などを集約）。
    - ETL 設計方針とユーティリティを実装（差分更新、バックフィル、品質チェック連携、DuckDB テーブル状態チェック等）。
  - jquants_client 経由の差分取得・保存（クライアントは別モジュールとして分離想定）。
- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を prices_daily から計算。データ不足時に None を返す設計。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出（EPS 欠損時は None）。
    - 出力は (date, code) キーの辞書リスト。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル数不足時は None。
    - rank: 同順位は平均ランクとするランク付け実装（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
- 一般的な実装方針・堅牢化
  - DuckDB を前提に SQL + Python で計算・更新を実施。executemany の空配列問題など DuckDB 特有の挙動に対応。
  - 外部 API 呼び出し時のリトライ・フォールバックを徹底（LLM 呼び出しは失敗しても部分処理継続）。
  - ルックアヘッドバイアス防止：内部処理で date.today()/datetime.today() を参照しない設計が多くのモジュールに適用。
  - idempotent な DB 書き込み（DELETE→INSERT / ON CONFLICT 戦略）を採用。
  - ロギングによる運用可視化（INFO/WARNING/DEBUG の適切な出力）。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Security
- 該当なし

Deprecated
- 該当なし

Notes / 開発者向け補足
- OpenAI の呼び出しは OpenAI SDK（OpenAI クラス）を利用する想定。テスト時は内部関数（_call_openai_api）をパッチしてモック可能。
- 外部 API キーは Settings を通して管理（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。
- DuckDB テーブルスキーマ（prices_daily / raw_news / news_symbols / ai_scores / market_regime / market_calendar / raw_financials など）の存在が前提。
- 日付/時間は明示的に date / UTC naive datetime を使い、タイムゾーン混入に注意する設計方針。

今後の計画（例）
- more: 発注・実行（execution）モジュールの実装とテスト
- monitoring: Slack 等へのアラート送信ロジック統合
- CI テストでの DuckDB テストデータ整備と OpenAI 呼び出しモックの充実

---- 

（本 CHANGELOG は提供されたソースコードから実装内容を推測して作成しています。実際のコミット履歴やリリースノートに沿って適宜調整してください。）