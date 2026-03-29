CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
次のバージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリースを追加。
  - パッケージ定義: kabusys.__version__ = "0.1.0"、公開サブパッケージの __all__ を定義（data, research, ai, など）。
- 環境設定/ローディング機能（kabusys.config）を追加。
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - export 形式・クォート・インラインコメント等に対応した .env パーサー実装。
  - OS 環境変数を保護する protected オプション、.env.local による上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの取得とバリデーションを行う。
- データ基盤機能（kabusys.data）を追加。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定（is_trading_day）、翌/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ判定（is_sq_day）。
    - J-Quants からの差分取得と夜間更新ジョブ（calendar_update_job）、バックフィル、健全性チェック実装。
    - market_calendar 未取得時は曜日ベースでフォールバック。
  - ETL パイプラインインターフェース（kabusys.data.pipeline, etl）
    - ETLResult データクラス（取得数・保存数・品質問題・エラー集計など）を公開。
    - 差分更新、バックフィル、品質チェック（quality 連携）の設計に対応するユーティリティを提供。
  - jquants_client 連携を想定した安全な保存処理（冪等性を重視）。
- 研究用分析機能（kabusys.research）を追加。
  - factor_research: calc_momentum、calc_volatility、calc_value を実装。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離を計算（データ不足時は None を返す）。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（必要行数未満は None）。
    - Value: raw_financials から最新財務を取り、PER/ROE を計算（EPS 無し/0 の場合は None）。
    - 全て DuckDB を用いた SQL 実装で外部 API へアクセスしない設計。
  - feature_exploration: calc_forward_returns、calc_ic（Spearman）/rank、factor_summary を実装。
    - 将来リターンのまとめ取得、ランク相関（IC）計算、統計サマリを提供。
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
- AI / ニュース NLP 機能（kabusys.ai）を追加。
  - news_nlp.score_news
    - 前日15:00 JST〜当日08:30 JST のタイムウィンドウで raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI（gpt-4o-mini, JSON mode）へバッチ送信。
    - 1チャンク最大 20 銘柄。リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results フォーマット、既知コードのみ採用、数値チェック、±1.0 にクリップ）。
    - ai_scores テーブルへ安全に置換（DELETE→INSERT、部分失敗時に他銘柄スコアを保護）。
    - テスト用に OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）200日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から MA200 乖離を計算、raw_news からマクロキーワードでフィルタしたタイトルを抽出し LLM（gpt-4o-mini） へ送信して macro_sentiment を算出。
    - API エラー時は macro_sentiment=0.0 としてフォールバック。計算結果を market_regime テーブルへ冪等的に書き込み。
    - lookahead バイアス回避（target_date 未満データのみ使用、datetime.today() を使わない設計）。
- ログ・堅牢性
  - 各モジュールで詳細なログ出力（INFO/DEBUG/WARNING）。
  - API 呼び出し・DB 書き込み失敗に対して適切に ROLLBACK、警告/例外処理を実装。
  - DuckDB 互換性考慮（executemany の空リスト回避など）。

Security
- 外部 API 利用に必要な機密情報は環境変数で管理（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は ValueError を発生させる箇所あり。

Known issues / Notes
- 依存・前提:
  - DuckDB に所定のテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が存在することを前提としている。
  - jquants_client（kabusys.data.jquants_client）や quality モジュールの実装が存在することを想定している（このコードベースでは関数呼び出しを行うが、その実体は別モジュール）。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON mode を使用するため、モデル/API の変更によりパース処理の調整が必要になる可能性がある。
- 一部関数はテスト時に差し替え可能（_call_openai_api など）だが、統合テストでは実際の API キーや DuckDB のテストデータが必要。
- 現バージョンは初期実装のため、追加のエラーハンドリング・性能改善やスキーマ検証が今後の課題。

Footer
------
この CHANGELOG はソースコード（src/kabusys 以下）の実装内容から推測して作成しています。実際のリリースノートとして使用する場合は、リリースに含める変更点や文言を適宜調整してください。