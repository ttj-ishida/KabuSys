CHANGELOG
=========

このプロジェクトは "Keep a Changelog" の形式に準拠しています。
リリース日付はコードベースの公開バージョン（src/kabusys/__init__.py の __version__ = "0.1.0"）および本ファイル作成日時に基づいて記載しています。

Unreleased
----------
今後の変更予定・検討事項をここに記載します。

0.1.0 - 2026-03-27
------------------

Added
- 初回公開リリース (v0.1.0)
- パッケージ公開インターフェース
  - pakage: kabusys（トップレベル __all__ に data, strategy, execution, monitoring を定義）
- 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み
  - .env 解析は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能（テスト用）
  - Settings クラスを公開（J-Quants / kabu / Slack / DB パス等のプロパティ）
  - 必須環境変数未設定時は _require() により ValueError を送出
  - KABUSYS_ENV / LOG_LEVEL の値検証と便利な bool プロパティ（is_live, is_paper, is_dev）
- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを参照した営業日判定（is_trading_day）、SQ 判定（is_sq_day）
    - next_trading_day / prev_trading_day / get_trading_days を提供（DB 優先、未登録日は曜日ベースでフォールバック）
    - calendar_update_job: J-Quants API から差分取得して冪等的に保存するバッチ処理（バックフィル・健全性チェック含む）
    - DB 未取得時の振る舞い（曜日フォールバック）や最大探索日数制限を実装
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー等の集約）
    - 差分更新・バックフィル・品質チェック設計（jquants_client 経由で idempotent に保存）
  - etl モジュールは ETLResult を再エクスポート
- リサーチ（kabusys.research）
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離(ma200_dev) を DuckDB で計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/NULL の場合は None）
    - 関数は prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない設計
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）
    - calc_ic: スピアマン順位相関（IC）を実装（欠損や ties を考慮）
    - rank / factor_summary: ランク化・基本統計量の計算（外部依存なし）
  - research パッケージは主要関数を __all__ で再エクスポート
- AI / NLP 機能（kabusys.ai）
  - news_nlp
    - score_news: raw_news + news_symbols を集約し、OpenAI (gpt-4o-mini, JSON Mode) を使って銘柄ごとのセンチメント（ai_score）を生成して ai_scores に書き込む
    - ニュースウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して比較（calc_news_window）
    - バッチ処理: 1回あたり最大 20 銘柄、1銘柄あたりの記事数・文字数でトリム（トークン肥大対策）
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ、部分失敗時は取得済みコードのみを置換（DELETE→INSERT）して既存スコアを保護
    - レスポンス検証: JSON パース補正（前後の余計なテキスト切り出し）、results フォーマット検証、未知コード除外、スコアを ±1.0 にクリップ
    - テスト性: OpenAI 呼び出し箇所を _call_openai_api として切り出し、patch による差し替えを想定
  - regime_detector
    - score_regime: ETF 1321 の 200日MA乖離(ma200_ratio) とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime に冪等書き込み
    - 合成重み: ma 70%, macro 30%（MA は scale=10、clip -1..1）
    - マクロニュースのフィルタリングはキーワードリストを利用し、最大 20 記事を LLM に送信
    - API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作。DB 書き込み失敗時は ROLLBACK を試み例外を伝播
    - LLM とのやりとりでのリトライ/エラー処理を実装
- OpenAI 統合
  - gpt-4o-mini を使用（JSON Mode による厳密な JSON 出力想定）
  - RateLimitError / APIConnectionError / APITimeoutError / APIError に対する適切なリトライ方針を実装
- 一貫した設計方針（全体）
  - ルックアヘッドバイアス防止: モジュール内で datetime.today() / date.today() を直接参照しない（target_date を明示的に受け取る）
  - DuckDB を主要な永続層として使用し、SQL + Python で処理を実装
  - 部分失敗耐性（フェイルセーフ）を重視。外部 API エラーが発生しても全体を停止させずデフォルトやスキップで継続する設計
  - テスト容易性のため、外部呼び出しを差し替え可能にしてある箇所を明示

Changed
- 新規リリースのためなし

Fixed
- 新規リリースのためなし

Security
- 環境変数に機密情報（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）を期待
- Settings は必須トークン未設定時に明示的に例外を発生させる（早期検出）

Notes / Known limitations
- 一部の関数（例: _adjust_to_trading_day の実装継続）はコードベースの一部で未完了の場所がある可能性あり（実装の継続が想定される）
- DuckDB の executemany に対する制約（空リスト不可）を考慮した防御的実装を行っている
- OpenAI のレスポンスは LLM の挙動次第でフォーマットが崩れることがあるため、JSON 抽出・バリデーションロジックを含む
- 本リリースでは pandas 等の外部解析ライブラリに依存せず標準ライブラリと DuckDB のみで実装している

Contributing
- バグ修正・機能追加の際は必ずルックアヘッドバイアスに注意し、target_date を明示的に渡す設計に従ってください
- OpenAI まわりはテストのため差し替え可能な設計になっているので、ユニットテストでは _call_openai_api をモックすることを推奨します

-- End of CHANGELOG --