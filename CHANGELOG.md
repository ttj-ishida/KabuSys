KEEP A CHANGELOG
すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

Unreleased
- 今後の変更をここに記載します。

[0.1.0] - 2026-03-27
Added
- パッケージ初期リリース kabusys v0.1.0
  - パッケージ公開用の __version__ と __all__ を設定 (src/kabusys/__init__.py)。

- 環境設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース直前の # をコメントと扱う）に対応。
  - 必須環境変数取得用の _require 関数と Settings クラスを提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* / DB パス等のプロパティを定義）。
  - env 値検証（development / paper_trading / live）と LOG_LEVEL 値検証（DEBUG〜CRITICAL）を実装。
  - デフォルトの DB パス（DuckDB/SQLite）や kabu API のデフォルト URL を提供。

- ニュース NLP モジュールを追加 (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装（score_news）。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC で変換して DB と比較）。calc_news_window を公開。
  - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大 10 記事かつ最大 3000 文字でトリム。
  - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数的バックオフでリトライ。
  - レスポンス検証: JSON パース（前後の余計なテキストを含むケースへの復元）、"results" フォーマット検証、未知コードの無視、スコアの数値化と ±1.0 クリップ。
  - DB 書き込みは冪等処理（DELETE → INSERT）を行い、部分失敗時に既存データを保護する実装。DuckDB executemany の空リスト制約に配慮。
  - 設計方針として、処理で datetime.today()/date.today() を直接参照せずルックアヘッドバイアスを防止。API 失敗時は個別にスキップして処理継続するフェイルセーフ。

- 市場レジーム判定モジュールを追加 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - 価格データは prices_daily、ニュースは raw_news、結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - マクロセンチメントはニュースタイトル（マクロキーワードでフィルタ）を LLM に渡し JSON で受け取り -1.0～1.0 に正規化。API エラー時は macro_sentiment=0.0 にフェイルセーフ。
  - OpenAI 呼び出しは専用の内部関数化（news_nlp とは独立実装）し、テスト時にモック可能な設計。
  - 設計上、内部で datetime.today()/date.today() を参照せず、prices_daily クエリに date < target_date の排他条件を付けてルックアヘッドを防止。

- データ関連モジュールを追加
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にデータがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - 夜間バッチ更新 job (calendar_update_job)：J-Quants API から差分取得し market_calendar へ冪等保存、バックフィル・健全性チェックを実装。
    - 最大探索日数やバックフィル日数などの安全装置を備える（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。
    - jquants_client との連携フックを想定。

  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL 実行結果の集約: 取得件数 / 保存件数 / 品質問題 / エラー一覧など）。
    - 差分更新・バックフィル・品質チェックのためのユーティリティ関数を実装（内部で DuckDB の最大日付取得等を提供）。
    - 設計方針: 差分更新は営業日単位、backfill による後出し修正吸収、品質チェックは呼び出し元で判断する方式（Fail-Fast ではない）。

- リサーチ/ファクター分析モジュールを追加 (src/kabusys/research/*)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB ベースの SQL で計算する関数群を実装（calc_momentum / calc_volatility / calc_value）。
    - 入出力は (date, code) をキーとする dict のリスト形式。
    - データ不足時の None 扱い、ウィンドウサイズやスキャンバッファの設定により週末・祝日を吸収。

  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman のランク相関を実装。最小有効レコード数のチェックを実施。
    - ランク関数（rank）: 同順位は平均ランク、丸め誤差対処のため round(v,12) を使用。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - pandas など外部ライブラリに依存せず標準ライブラリ + DuckDB SQL で実装。

- モジュール公開整理
  - ai、research、data パッケージの __init__ で主要関数を再エクスポート（例: kabusys.ai.score_news, kabusys.research.calc_momentum 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 設計上の重要点（リリース注記）
- ルックアヘッドバイアス防止: AI モジュール・スコアリング系は内部で現在日時を直接参照せず、全て target_date を引数で指定する設計。
- フェイルセーフ: OpenAI API の失敗は個別処理をスキップまたはデフォルト値（0.0）にフォールバックし、ETL/解析パイプライン全体が停止しないよう配慮。
- テスト容易性: OpenAI への呼び出しを内部関数化しており、unittest.mock.patch 等で差し替え可能。
- データベース: DuckDB を主要な分析 DB として使用。executemany の空リストに対する互換性（DuckDB 0.10 系）への注意点を考慮した実装。

今後の課題（参考）
- PBR・配当利回りなどバリューファクターの追加
- モデルの校正・モデルサービング周り（戦略 → 実行）との接続
- API キー・認証まわりの運用強化（シークレット管理の改善）
- 単体テストや統合テストの拡充（特に外部 API モックや DB フェイクデータ）

------ 
この CHANGELOG はコード内容からの推測に基づいて作成しています。実際のリリースノートやプロジェクト方針に合わせて編集してください。