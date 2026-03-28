Keep a Changelog に準拠した CHANGELOG.md

すべての重要な変更点をここに記録します。フォーマットは Keep a Changelog を基本とし、後方互換性のある変更は明確に分類しています。

Unreleased
----------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-03-28
-------------------

Added
- 全体
  - 初回公開リリース。パッケージ名: kabusys、バージョン 0.1.0。
  - パブリックモジュールのエクスポートを定義（kabusys.__all__ に data, strategy, execution, monitoring を設定）。
- 設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - プロジェクトルート探索: __file__ を起点に .git または pyproject.toml を検出してルートを特定（CWD 非依存）。
  - .env パーサ実装:
    - コメント行と export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無しの行でのインラインコメント判定（直前が空白/タブの場合のみ '#...' をコメントとみなす）。
  - Settings クラス提供: 必須項目取得ヘルパー（_require）と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DBパス、環境種別、ログレベル 判定など）。
    - KABUSYS_ENV の妥当性チェック（development, paper_trading, live）。
    - LOG_LEVEL の妥当性チェック（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを合成して OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供する calc_news_window。
    - バッチサイズ、1銘柄当たり記事数/文字数制限、JSON mode レスポンス検証、スコアクリッピング、指数バックオフによるリトライを実装。
    - DuckDB の executemany の挙動に配慮し、空リストバインドを回避する処理を実装。
    - API キーは引数または環境変数 OPENAI_API_KEY で注入可能。テスト容易性のため _call_openai_api を patch 可能。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタしてマクロ記事のみを LLM に送る実装。
    - API障害時は macro_sentiment=0.0 のフェイルセーフ、LLM レスポンスの JSON パース失敗でも継続。
    - OpenAI 呼び出しは内部で OpenAI クライアントを生成し、最大リトライ回数と指数バックオフを適用。
    - ルックアヘッドバイアス防止の設計: date 比較は target_date 未満／未満等で厳格に処理し、datetime.today()/date.today() を参照しない。
- データ処理 (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値がない場合は曜日ベースのフォールバック（週末は非営業日）を使用。DB と曜日判定の一貫性を確保。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装し、J-Quants から差分取得して冪等的に保存。バックフィル、健全性チェック、例外ハンドリングを組み込み。
  - pipeline / ETL:
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー一覧）を保持・辞書化可能に。
    - 差分取得、バックフィル、品質チェックの設計方針を反映するユーティリティを用意（jquants_client, quality と連携想定）。
  - etl モジュールで ETLResult を公開再エクスポート。
- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER、ROE を計算（PBR・配当利回りは未実装）。
    - DuckDB を活用した SQL ベースの実装。結果は (date, code) をキーとする辞書のリストで返却。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算（最低 3 件以上で計算）。
    - rank: 同順位は平均ランクで処理（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算。
- 互換性・テスト支援
  - OpenAI 呼び出し箇所に patch 可能な内部関数を用意してテストしやすくしている（news_nlp._call_openai_api, regime_detector._call_openai_api）。
  - DuckDB のバージョン差分（executemany 空リスト不可など）に配慮した実装。

Changed
- 初版のため、内部設計方針・安全策（ルックアヘッドバイアス回避、フェイルセーフ、冪等書き込み、リトライ戦略等）を明確に反映。

Fixed
- 該当なし（初期リリース）。ただし各所で潜在的失敗に対するロギングとフォールバックを追加。

Security
- OpenAI API キーや各種シークレットは環境変数経由で管理する設計。
- .env 読み込み時に OS の既存環境変数を保護するため protected キーセットを用いる（.env.local は override=True でも OS 環境変数は上書きされない）。

Notes / 注意事項
- AI 機能（score_news, score_regime）は OpenAI API キー（OPENAI_API_KEY）が必要。未設定時は ValueError を送出する。
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring 用): data/monitoring.db
- News/Regime スコアは常に -1.0～1.0 にクリップされる。
- market_regime / ai_scores への書き込みは冪等（DELETE→INSERT / トランザクション）を意識しているが、DB の実装や権限設定によっては挙動が異なる可能性があるため運用環境での検証を推奨。
- jquants_client, quality など外部連携クライアントは本リリースで参照を行うが、実装は別モジュール（このコードベース内で想定）を使用。

今後の予定（例）
- 更なるファクター追加（PBR、配当利回り等）
- モデル評価・バックテスト用ユーティリティの追加
- J-Quants / kabuAPI クライアントの堅牢化と統合テスト

References
- パッケージバージョンは kabusys.__version__ = "0.1.0" に一致します。