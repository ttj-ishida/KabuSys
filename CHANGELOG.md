CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-03
-------------------

Added
- 初期リリース。KabuSys: 日本株自動売買／データ基盤／リサーチ支援用ライブラリ群を追加。
- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱い）。
  - 既存 OS 環境変数を保護する protected オプションを搭載（.env.local は上書き可能だが OS 変数は保護）。
  - Settings クラスを提供（J-Quants / kabu / LINE / DB / 監視 / システム設定などのプロパティ、必須項目のチェック、env/log level のバリデーション、is_live 等のユーティリティ）。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算（UTC 変換）、1 銘柄当たり記事数/文字数トリム、最大バッチサイズ・リトライ／指数バックオフ、レスポンス検証（JSON 抽出・results 検証・コード照合・数値検証）、スコア ±1.0 クリップ。
    - API 失敗時は部分的にスキップする設計（フェイルセーフ）。DuckDB executemany の空リスト制約へ対応。
    - テスト用に _call_openai_api をパッチ可能に設計。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - マクロニュースはキーワードフィルタリングして最大 N 件を LLM に送信。LLM 呼び出しは独立実装でモジュール結合を避ける。
    - レジームスコアのクリップ、閾値判定による 'bull' / 'neutral' / 'bear' ラベリング、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM / ネットワークエラーに対する再試行（429/接続エラー/タイムアウト/5xx を考慮）と、全リトライ失敗時は macro_sentiment=0.0 で継続。
- データモジュール（kabusys.data）
  - calendar_management
    - market_calendar を用いた営業日判定・SQ 判定・前後営業日の取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベース（週末除外）でフォールバック。探索範囲上限により無限ループ防止。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック（未来日付の異常検出）を実装。
  - pipeline / etl
    - ETLResult dataclass を公開（kabusys.data.etl 経由で再エクスポート）。ETL 実行メタ情報（取得件数・保存件数・品質問題・エラー）を保持。
    - 差分更新・バックフィル・品質チェック（quality モジュールと連携）・idempotent な保存方針を実装。
- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR（true range の NULL 伝播を適切に扱う）、相対 ATR、20 日平均売買代金、出来高比率等。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS が 0 や欠損の場合は None）。
    - DuckDB のウィンドウ関数を利用した効率的な実装。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン先の将来リターン（複数ホライズンをまとめて1クエリで取得）。horizons の入力検証あり。
    - calc_ic: スピアマンランク相関（ランク関数は同順位の平均ランク処理を実装）。有効レコードが 3 未満なら None。
    - rank, factor_summary: ランク化と基本統計量（count/mean/std/min/max/median）を提供。
  - すべて標準ライブラリと DuckDB のみで実装（pandas 等外部依存なし）。
- その他
  - パッケージのトップレベル __version__ = "0.1.0" を設定。
  - ロギングと詳細な警告メッセージを多用し、運用時の原因特定を容易にする設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや各種シークレットは Settings で環境変数から取得する設計。必須キー未設定時は ValueError を送出して明示的に検出可能。

Notes / Known limitations
- OpenAI API（gpt-4o-mini）利用箇所は外部 API 依存のため、API キー未設定時は例外。API の失敗時はフェイルセーフでスコアを 0.0 または該当銘柄をスキップする挙動を取る（運用上は再実行や監視が必要）。
- DuckDB の executemany に対する空リストバインディング制約を考慮した実装（空リストの場合は SQL 実行をスキップ）。
- 日付計算やスコア生成では datetime.today()/date.today() を直接参照しない設計にしており、ルックアヘッドバイアスを防止。
- テスト容易性のため OpenAI 呼び出し部分は内部関数をモックできる設計になっている（例: unittest.mock.patch）。

Contributors
- 初期実装（単一リポジトリのコードベース）としてまとめての公開。

今後の予定（例）
- ai モジュールのモデル切替やローカル LLM 対応、より細かい品質チェックルール追加、ETL の並列化や監視ダッシュボードの実装など。