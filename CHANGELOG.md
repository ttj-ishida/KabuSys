KEEP A CHANGELOG
すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
---------
（現在のブランチ上の未リリース変更はありません）

[0.1.0] - 2026-04-03
-------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ概要:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を公開。主要サブパッケージを __all__ でエクスポート (data, strategy, execution, monitoring)。
- 環境変数・設定管理モジュール (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定をロードする自動読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索するため CWD に依存しない動作。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース前の # をコメントと判断）などに対応。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数を保護する protected オプションをサポート。
  - 環境変数ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（自動読み込みを無効化可能）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視 /システム設定をプロパティとして取得。
  - 入力値検証: KABUSYS_ENV や LOG_LEVEL の許容値チェック、必須値未設定時は ValueError を送出。
- AI（自然言語処理）モジュール
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとの記事を構築し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを算出。
    - バッチサイズ、最大記事数、文字数上限、時間ウィンドウ (前日15:00 JST ～ 当日08:30 JST) を定義。
    - レスポンスの厳格なバリデーションと ±1.0 のクリッピング。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - 部分成功に備え、ai_scores へは取得できた銘柄のみを DELETE → INSERT により置換（冪等性・部分失敗耐性）。
    - テスト容易性: _call_openai_api をモック差し替え可能に設計。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（Nikkei連動 ETF）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードリストに基づき raw_news からタイトルを取得。
    - OpenAI 呼び出しは独立実装（news_nlp と結合しない）で retry とエラー処理を実装。API 失敗時は macro_sentiment を 0 にフォールバック（フェイルセーフ）。
    - レジーム判定結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照せず、prices_daily クエリは target_date 未満を使用。
- Data（データ基盤）モジュール
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を使った営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得のときは曜日ベース（平日のみ営業）のフォールバックを提供。
    - 最大探索日数を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job を実装し、J-Quants から差分取得→保存（バックフィル・健全性チェックを含む）を行う。J-Quants クライアント経由の取得/保存に依存。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult データクラスを公開（etl.py で再エクスポート）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した ETL の設計を実装。
    - ETL 実行結果は品質問題やエラーのリストを収集し、 has_errors / has_quality_errors プロパティおよび to_dict() を提供。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得ユーティリティを追加。
- Research（リサーチ）モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、ma200乖離）、Volatility（20日 ATR、相対ATR、出来高関連）、Value（PER, ROE）を DuckDB SQL を用いて実装。
    - データ不足時の None ハンドリング、ログ出力、結果は辞書リスト形式で返却。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns（horizons 引数の検証、一括 SQL 取得）、IC（calc_ic: スピアマンランク相関）の実装。
    - ランキング関数 rank（同順位は平均ランク、丸めで ties 対応）、factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等非依存で標準ライブラリ + DuckDB による実装。
- パッケージ内の公開 API 整備
  - ai/__init__.py, research/__init__.py 等で関数やユーティリティの公開（__all__）を設定。

Changed
- 初期リリースのため特記すべき変更履歴はなし。

Fixed
- 初期リリースのため過去のバグ修正履歴はなし。
- 実装上の堅牢性対応（例: JSON レスポンスの前後余計テキストを復元するロジック、DuckDB executemany の空リスト回避、API エラー分類によるリトライ判定等）を実施。

Security
- OpenAI API キーは引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を参照。必須未設定時は ValueError を送出して誤使用を防止。

Notes / Design decisions
- ルックアヘッドバイアス対策: 全てのデータ処理関数は内部で現在時刻を参照せず、呼び出し側から target_date を渡す設計。
- フェイルセーフ設計: 外部 API の失敗は可能な限り局所的に扱い（デフォルトスコアにフォールバック、スキップして継続）、ETL は品質警告を収集して呼び出し元に委ねる。
- テスト容易性: OpenAI 呼び出しや内部ユーティリティをモック差し替え可能にしている（関数分離、private 名称での定義）。
- データベース: DuckDB を前提として最適化された SQL を使用。DuckDB バージョン差異（executemany の空リスト等）に配慮した実装。

今後の予定（検討中）
- Strategy / execution / monitoring の具体的実装（初版ではパッケージプレースホルダとして公開）。
- 追加ファクター（PBR、配当利回り等）やモデル評価パイプラインの拡張。
- OpenAI 呼び出しのメトリクス/監視およびコスト制御機能の追加。