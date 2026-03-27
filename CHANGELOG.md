# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

[Unreleased]

## [0.1.0] - 2026-03-27

Added
- 初回リリース。
- パッケージ構成
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0、data / strategy / execution / monitoring を __all__ で公開）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートなしでは '# ' または '\t#' をコメントと判別）
    - 無効行（空行、コメント行、等号なし行）を無視
  - protected（OS 環境変数）の上書き制御をサポート（.env と .env.local の優先度制御）。
  - Settings クラスに主要設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、既定値（KABU_API_BASE_URL、DBパス等）と検証（KABUSYS_ENV, LOG_LEVEL）を実装。
- データプラットフォーム（kabusys.data）
  - ETL パイプライン API（pipeline.ETLResult を etl モジュールで再エクスポート）。
  - calendar_management モジュール
    - JPX マーケットカレンダーの夜間更新ジョブ（calendar_update_job）
    - 営業日判定ユーティリティ群：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日（週末）ベースのフォールバックを使用
    - _MAX_SEARCH_DAYS 等の探索上限、バックフィル・健全性チェックを実装
  - pipeline モジュール（ETL）
    - 差分取得・バックフィル・品質チェック（quality モジュールに依存）を想定した ETLResult データクラス
    - DuckDB を用いる想定のユーティリティ（テーブル存在確認、最大日付取得など）
- 研究用機能（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算
    - calc_value: EPS/ROE から PER/ROE を算出（raw_financials / prices_daily を参照）
    - 全関数は DuckDB 上の prices_daily / raw_financials のみ参照（取引 API 等には接続しない）
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を算出
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めによる ties 対策あり）
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出
- AI 関連（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメント（-1.0〜1.0）を算出・ai_scores テーブルへ保存
    - 処理の流れ：ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）、記事集約（最大記事数・文字数トリム）、バッチ送信（最大20銘柄/チャンク）、レスポンス検証、スコアの ±1 クリップ、部分失敗を避けるための個別 DELETE → INSERT の冪等更新
    - 再試行ロジック：429・ネットワーク・タイムアウト・5xx に対して指数バックオフでリトライ
    - テスト容易性：_call_openai_api をモック可能
  - regime_detector モジュール
    - ETF 1321 の 200日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み
    - マクロニュース抽出はニュースタイトルをキーワードフィルタ（日本・米国等のマクロキーワード）で取得
    - OpenAI 呼び出しは専用実装で、エラー時は macro_sentiment=0.0 でフェイルセーフ継続
    - 設計方針としてルックアヘッドバイアス防止のため date パラメータベースで動作（datetime.today() 参照なし）
- 汎用設計・運用性
  - DuckDB を主要な分析 DB として採用（関数は DuckDB の SQL と Python を組み合わせて高速に動作する想定）
  - DB への書き込みは冪等性を考慮（BEGIN/DELETE/INSERT/COMMIT、例外時は ROLLBACK と警告）
  - OpenAI との連携は api_key を引数で注入可能（テストで環境変数に依存させない設計）
  - ロギングを広く導入し、失敗時は WARN/INFO/DEBUG で詳細を出力
  - テストフレンドリーなフック：内部の API 呼び出し関数をパッチ可能（unittest.mock.patch を想定）

Changed
- 新規リリースのため、該当なし（初版）。

Fixed
- 新規リリースのため、該当なし（初版）。

Deprecated
- なし。

Removed
- なし。

Breaking Changes
- なし（初回公開）。

Notes / 実装上の重要ポイント（開発者向け）
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を使用。レスポンスは厳密な JSON を期待するが、余計な前後テキストが混入する場合へも対処するパーサを実装している（{} の抽出）。
- news_nlp と regime_detector はどちらも OpenAI を使用するが、_call_openai_api を各モジュールで独自実装しておりモジュール間でプライベート関数を共有しない設計になっている（結合を避けるため）。
- ルックアヘッドバイアス防止のため、全ての定期処理関数は target_date を明示的に受け取り、内部で date.today()/datetime.today() を参照しない。
- DuckDB の executemany に対する互換性考慮（空リストを渡さない等）や、テーブル未存在時のフォールバック処理を多用しているため、運用時は期待テーブルが存在するかを確認のこと。
- 必須環境変数（Settings が _require でチェックするもの）は未設定時に ValueError を送出する。CI/本番では .env や環境変数の準備を忘れないこと。
  - 例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（各 AI 関数の呼出し時）

もし、CHANGELOG に追記したい未記載の目的（例: リリース日の変更、追加の既知の制限、将来の予定）や、別の言語での出力が必要であれば教えてください。