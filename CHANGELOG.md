Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

フォーマット方針:
- 期間差分ではなく機能/変更点を読みやすく列挙しています。
- 日付はリポジトリ内のバージョン情報と現在のリリース日（本CHANGELOG作成日）を用いています。

Unreleased
---------
（なし）

[0.1.0] - 2026-04-09
--------------------
初回公開リリース。以下の主要機能・実装を含みます。

Added
- パッケージ基礎
  - kabusys パッケージ初期公開。__version__ = "0.1.0"。
  - モジュール群を public API としてエクスポート（portfolio, research, ai, ...）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - 環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - OS 環境変数を保護する protected キーセットを利用し、不用意な上書きを防止。
  - .env パーサは次をサポート:
    - コメント行、export KEY=val 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの処理。
  - Settings クラス（プロパティ経由で環境値を取得）を提供:
    - 必須変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - デフォルト値（例: KABU_API_BASE_URL, DB パス）と Path 変換のサポート。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証（不正値で ValueError を送出）。
    - is_live / is_paper / is_dev の便利プロパティ。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でのタイブレークで上位 N を返す。
  - 重み計算
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率による重み。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - リスク調整
    - apply_sector_cap: 既存ポジションのセクター別時価総額が閾値（max_sector_pct）を超える場合、新規候補の同セクターを除外。unknown セクターは除外しない。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告ログ）。
  - 株数決定
    - calc_position_sizes: allocation_method に基づく発注株数計算を実装（"risk_based" / "equal" / "score"）。
      - lot_size 単位で丸め、銘柄毎の上限（max_position_pct）を考慮。
      - risk_based: risk_pct, stop_loss_pct を用いた単純リスクベース算出。
      - aggregate cap: 全銘柄投下コストが available_cash を超える場合にスケールダウンし、残余キャッシュで端数を lot 単位で再配分するアルゴリズムを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
      - 価格欠損時はスキップ、ログ出力。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。必要行数不足時は None を返す。
    - calc_volatility: 20日 ATR（true_range の取り扱いに注意）/ atr_pct / avg_turnover / volume_ratio を計算。ウィンドウ内データ不足時は None を返す。
    - calc_value: raw_financials から最新の財務データを取り出し、PER（EPS が有効な場合）と ROE を計算。
    - 全関数は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照。
  - 特徴量解析（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。horizons の妥当性チェックあり。
    - calc_ic: スピアマンランク相関（IC）を実装（同順位は平均ランク）。有効レコードが 3 未満の場合は None。
    - rank: 同順位の平均ランク処理（丸め誤差対策で round(v,12) を使用）。
    - factor_summary: count/mean/std/min/max/median を算出。None 値は除外。
    - 外部ライブラリに依存しない純粋 Python 実装（DuckDB は使用）。

- AI / LLM 統合（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - score_news: raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込む。
      - ニュースウィンドウの計算（calc_news_window）を提供（JST ベース → UTC 変換）。
      - チャンク処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数の上限を設定（トークン肥大化対策）。
      - OpenAI 呼び出しは retry（429/接続/タイムアウト/5xx）に対して指数バックオフ。その他の例外はリトライしない。
      - レスポンスのバリデーション: JSON 抽出・results リスト・code/score 検査・スコア数値化・±1.0 クリップ。パース失敗時は可能なら最外の {} を切り出して復元。
      - DuckDB への書込みは部分的に冪等 (DELETE → INSERT) を行い、部分失敗で他コードのスコアを消さないよう配慮。DuckDB executemany の空リスト制約に対する安全措置あり。
      - API キー未指定時は ValueError を送出。
      - テスト容易性のため _call_openai_api を差替え可能に設計。
  - レジーム判定（regime_detector.py）
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込む。
      - ma200_ratio の算出は target_date 未満のデータのみを使用（ルックアヘッド防止）。
      - マクロニュースはキーワード検索で抽出（最大 N 件）し、LLM で macro_sentiment を評価。記事なし・API失敗時は macro_sentiment=0.0 でフォールバック。
      - 合成スコアを -1..1 にクリップし閾値に基づき regime_label を決定（冪等な DB 書き込み）。
      - OpenAI 呼び出しに対して retry / 例外処理を実装。テストのため _call_openai_api を差替え可能。
      - 失敗時もフェイルセーフなデフォルトを使う設計。

- 監視データ永続化（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite 接続に対して監視用のテーブル群とインデックス（system_status, trade_logs, positions, risk_logs 等）を冪等に作成するスクリプトを提供（部分的にファイルは省略）。

Security / Safety / Design notes
- ルックアヘッドバイアス防止のため、どのモジュールも datetime.today()/date.today() を参照していない（target_date を外部から注入する設計）。
- OpenAI API 呼び出しは冪長性・フェイルセーフ設計（バックオフ、フォールバック値、部分書き込みでの保護）。
- DuckDB / SQLite 周りは互換性と実運用での注意点（executemany の空リスト制約、NULL の扱いによる true_range カウントの制御等）に配慮。
- テストしやすさのため API 呼び出し点（_call_openai_api 等）はモック差替えを想定して実装。

Known limitations / TODOs (明示的な既知事項)
- position_sizing の lot_size は現状グローバル共通（将来的に銘柄別 lot_map に拡張予定）。
- apply_sector_cap は price が欠損（0.0）だとエクスポージャー過少見積りとなる可能性があり、将来はフォールバック価格を検討予定。
- news_nlp / regime_detector の OpenAI 呼び出しは現在 gpt-4o-mini を想定。将来的にモデル差替え対応やリクエスト最適化を検討。
- monitoring_db のスキーマはこのリリースで途中まで定義（ファイル末尾に断片あり）。完全スキーマは次リリースで整備予定。

その他
- 本リリースは機能的に多数の「純粋関数群」「DB 読込専用処理」「外部 API 呼出し（OpenAI）」を含むため、ユニットテスト・統合テストを通して安全にデプロイしてください。API キー等の機密は .env または環境変数で管理することを推奨します。