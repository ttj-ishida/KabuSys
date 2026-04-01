# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

なお、本リリースはソースコードから推測して作成しています。実装の意図や使用方法については各モジュールのドキュメントやソースコメントを参照してください。

## [0.1.0] - 2026-04-01

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。

- 設定/環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。
  - ロード順: OS 環境変数 > .env.local > .env。OS 環境変数の保護、override 制御をサポート。
  - 自動ロード抑止用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサーを実装（`export KEY=val`、クォートのエスケープ、インラインコメント判定などに対応）。
  - Settings クラスを公開（settings インスタンス）。主なプロパティ:
    - J-Quants / kabu / Slack / DB パス / 監視閾値 / 環境 (development/paper_trading/live) / ログレベルなど。
  - 必須環境変数未設定時は ValueError を投げる `_require` 実装。

- データプラットフォーム関連 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーを扱う market_calendar テーブル向けユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得または未登録日の場合は曜日ベースでフォールバック（土日を休業日と扱う）。
    - 夜間バッチ: calendar_update_job を実装（J-Quants クライアント経由で差分取得し idempotent に保存、バックフィルと健全性チェックあり）。
    - 最大探索日数やバックフィル期間などの安全パラメータを設定して無限ループや異常値を防止。

  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラーなど）を構造化して返却・ログ化可能に。
    - pipeline モジュールを etl モジュールで再エクスポート（ETLResult を公開）。
    - 差分更新、バックフィル、品質チェックの設計に基づく処理フローを実装。DuckDB を想定したテーブル存在チェックや最大日付取得等のユーティリティを含む。

  - jquants_client など外部クライアントへの依存を想定した設計（fetch/save 関数を呼ぶ形）。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュール (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev) を計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率などを計算（true range の NULL 伝播制御等を考慮）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - DuckDB 内で SQL を駆使して効率的に取得・集計。データ不足時は None を返す設計。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）先の将来リターンを計算。ホライズンチェックと範囲バッファを実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None。
    - rank: 同順位は平均ランクを採るランク関数（浮動小数の丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。

- AI / ニュース NLP (kabusys.ai)
  - ニューススコアリング (news_nlp)
    - score_news: raw_news と news_symbols を元に銘柄ごとのニューステキストを集約し、OpenAI (gpt-4o-mini, JSON mode) にバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して検索（ルックアヘッド防止）。
    - バッチ・チャンク処理（_BATCH_SIZE=20）、1 銘柄あたり記事数・文字数の上限トリムを実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API 呼び出し時のエクスポネンシャルバックオフ（429/ネットワーク/TIMEOUT/5xx の再試行）、最大試行回数、ログ出力。
    - 応答の堅牢なバリデーション: JSON 抽出、"results" リスト存在確認、コード一致チェック、スコアの数値性確認、±1.0 でクリップ。
    - 部分失敗対策: 成功した銘柄コードのみ DELETE→INSERT で置換し、他の既存スコアを保護。
    - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api を patch 置換可能に設計。

  - 市場レジーム判定 (regime_detector)
    - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出は news_nlp.calc_news_window と raw_news を利用。マクロキーワードリストを元にタイトルを抽出。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - レジームスコアの合成ロジック、閾値定義、IDEMPOTENT な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- 共通設計方針（本リリース全体）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を内部処理で安易に参照しない設計。明示的な target_date を受け取る API を採用。
  - DuckDB を想定した SQL ベースのデータ操作。executemany の空リスト制約等の互換性考慮。
  - API 呼び出し失敗時のフェイルセーフ（スコア 0 で継続・部分書き込みで他データ保護）。
  - 詳細なログ出力と警告（warning/exception）を挿入して運用時のトラブルシュートに配慮。
  - テスト容易性: 外部 API 呼び出し部分を patch しやすいように分離。

Security
- 環境変数の直接上書き（override）を制御し、OS 環境変数を保護する仕組みを提供。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Notes / 今後の拡張想定（コードのコメントや設計意図から推測）
- 現フェーズでは sentiment_score と ai_score が同値だが将来的に差別化可能性あり。
- PBR・配当利回りなどのバリューファクターは未実装。raw_financials を用いた追加ファクターの拡張余地あり。
- monitoring / execution などの実運用モジュールの統合や Slack 通知等の実装が期待される（settings に Slack 設定があるため実装予定を示唆）。
- OpenAI のモデルや API バージョン変更への互換性対応が必要になる可能性あり（status_code の取り扱い等は既に考慮済み）。

---

問い合わせやリリースノートへの追加希望があれば、実装箇所や利用シナリオに応じて追記します。