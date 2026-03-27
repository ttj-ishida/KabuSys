Changelog
=========

すべての変更は Keep a Changelog に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

(なし)

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
- パッケージルート & バージョン
  - パッケージのエントリポイントを追加。__version__ = "0.1.0"、公開モジュール一覧を __all__ で定義。
- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動ロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト等で利用可能）。
  - .env 解析器を実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（条件付き）。
    - 無効行（空行・コメント・不正な行）は無視。
  - .env ロード時の上書き制御:
    - override フラグと protected キーセット（OS 環境変数保護）をサポート。
    - ファイル読み込み失敗時は警告を出力して継続。
  - Settings クラスを公開:
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを環境変数から取得。
    - env / log_level のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None)：raw_news / news_symbols から記事を集約し、OpenAI (gpt-4o-mini, JSON Mode) で銘柄ごとのセンチメントを算出して ai_scores に書き込む。
    - タイムウィンドウ計算 (calc_news_window)：JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたりの記事数・文字数上限を設定（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション: JSON 抽出 (前後ノイズ対応)、results 配列/各要素の型チェック、未知コードの無視、数値チェック、±1.0 でクリップ。
    - DuckDB の制約（executemany に空リスト不可）を考慮した DB 書き込みロジック（DELETE 個別実行 → INSERT、トランザクション制御）。
    - API キー注入可能（引数 or OPENAI_API_KEY 環境変数）。未設定時は ValueError。
    - フェイルセーフ: API 呼び出し失敗時は該当チャンクをスキップして処理継続。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None)：ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム ('bull'/'neutral'/'bear') を算出し market_regime に冪等書き込み。
    - ma200 比率計算 (_calc_ma200_ratio)：target_date 未満のデータのみ使用し、データ不足時は中立値 1.0 を返す（警告ログ）。
    - マクロニュース抽出 (マクロキーワード群による title フィルタ) と LLM スコア (_score_macro)。
    - LLM 呼び出しは gpt-4o-mini の JSON mode を使用、再試行・エラーハンドリング（429/接続/タイムアウト/5xx）、JSON parse 失敗時は 0.0 にフォールバック。
    - スコア合成後、BEGIN/DELETE/INSERT/COMMIT により冪等的に DB 書き込み。失敗時は ROLLBACK を試行して例外を再送出。
    - フェイルセーフ設計（API 失敗時は macro_sentiment=0.0）。
- データ関連モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバック。
    - DB 登録値優先、未登録日は曜日フォールバックという一貫した振る舞いを保持。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得し market_calendar を冪等更新（fetch → save）。
    - バックフィル期間・健全性チェック（将来日付の異常検出）をサポート。
    - jquants_client を利用した実装。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題リスト・エラーリストなどを保持）。
    - 差分更新・バックフィル・品質チェックを行う設計方針を実装。DB 最終日確認や backfill_days による再取得を想定。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - DuckDB 互換性（executemany 空リスト回避など）を考慮した実装。
  - kabusys.data.etl は ETLResult を再エクスポート。
- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum：1M/3M/6M リターン、200 日 MA 乖離などを prices_daily から計算。データ不足は None を返す。
    - calc_volatility：20 日 ATR、ATR 比率、20 日平均売買代金、出来高比などを計算。
    - calc_value：raw_financials の最新報告と当日の株価から PER / ROE を計算。EPS 不在や 0 の場合は None。
    - SQL とウィンドウ関数を利用した効率的な実装（DuckDB 前提）。
  - feature_exploration
    - calc_forward_returns：指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーション有り。
    - calc_ic：ファクター値と将来リターンの Spearman ランク相関（IC）を算出。有効レコード < 3 なら None。
    - rank：同順位は平均ランクで扱うランク変換（丸めによる ties 対応）。
    - factor_summary：count / mean / std / min / max / median を計算する統計サマリー。
    - いずれも標準ライブラリ + DuckDB SQL のみで実装（pandas 等に非依存）。
- 実装上の設計指針・安全策（全体）
  - ルックアヘッドバイアス防止: 各処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - OpenAI 呼び出しについてはテスト時に差し替え可能（内部 _call_openai_api を patch することでモック可能）。
  - DB 書き込みはトランザクション制御かつ冪等性を意識した実装（DELETE → INSERT、ON CONFLICT 方針等）。
  - 詳細なログ出力と警告による異常検出を重視（警告ログで挙動を追跡可能）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- DuckDB のバインドや executemany の挙動に依存する箇所があり、環境によっては調整が必要な場合があります（空リスト処理を回避する対策を実装済み）。
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を想定しており、将来の API 仕様変更やモデル変更に備えた例外処理を入れていますが、運用時は API キー管理とレート制御に注意してください。
- calendar_update_job / ETL ジョブは外部 J-Quants クライアントに依存します。API の利用制限や変更に備えてエラーハンドリングを行っていますが、運用時の監視が推奨されます。