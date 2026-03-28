# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記述しています。  
Semantic Versioning を採用しています。  

[Unreleased]

[0.1.0] - 2026-03-28
====================

Added
-----
- 初回リリース。パッケージ kabusys の基本機能を追加。
  - パッケージメタ情報: version 0.1.0 を設定。
  - パブリック API: pakage-level __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出: __file__ を起点に親ディレクトリを上方向に探索し、.git または pyproject.toml を検出してプロジェクトルートを特定する実装を追加（カレントワーキングディレクトリに依存しない）。
  - .env パーサーを実装:
    - コメント行・空行・export プレフィックス対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの無視をサポート。
    - クォート無し値における '#' のコメント判定は直前がスペース/タブの場合のみコメントとして扱う挙動。
  - 自動ロードの優先度: OS 環境変数 > .env.local > .env。既存の OS 環境変数は protected として上書きから保護。
  - 環境変数自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト容易性確保）。
  - 設定ラッパー Settings を実装。J-Quants / kabu API / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを提供。値検証（有効な env 値、ログレベル）やユーティリティ（is_live, is_paper, is_dev）を追加。
  - 必須環境変数未設定時は ValueError を投げる _require を提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を対象に OpenAI（gpt-4o-mini・JSON mode）で銘柄ごとのセンチメントを算出し、ai_scores テーブルへ書き込む score_news を実装。
  - ニュース集計ウィンドウ: JST 前日 15:00 〜 当日 08:30 を UTC に変換して扱う calc_news_window を実装。
  - 銘柄ごとに最新 N 件・文字数上限でトリムしてプロンプト生成（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - バッチ処理: 1 API 呼び出しで最大 20 銘柄を処理（並べて提示）して効率化。
  - レート制限（429）、ネットワーク断、タイムアウト、サーバー 5xx に対する指数バックオフ・リトライ実装。
  - レスポンス検証: JSON パース（余分な前後テキストの補正含む）、"results" リスト構造、code と score の妥当性チェック、スコアの ±1.0 クリップ。
  - 部分成功対策: 成功した銘柄のみを DELETE → INSERT の形で置換して、部分失敗時に既存スコアを保護。
  - フェイルセーフ: API エラーやパースエラーは例外を上げずログ出力してスキップ（システム全体の安定性重視）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - MA 計算は DuckDB の prices_daily を参照し、target_date 未満のデータのみを使用してルックアヘッドを防止。
  - マクロニュースは news_nlp の calc_news_window で算出されたウィンドウからキーワードフィルタでタイトルを抽出 (_MACRO_KEYWORDS)。
  - OpenAI 呼び出しは専用実装を行い、JSON パース失敗・API エラー時は macro_sentiment を 0.0 としてフェイルセーフ処理。
  - 結果の合成スコアは clip(-1.0, 1.0) で正規化し閾値によりラベル付け。
  - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。ROLLBACK 失敗時は警告ログを出力して上位へ例外を伝播。

- 研究用ファクター計算（kabusys.research）
  - factor_research:
    - モメンタム: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を calc_momentum に実装。データ不足時は None を返す。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を calc_volatility に実装。true_range 計算における NULL 伝播に配慮。
    - バリュー: 最新の raw_financials（report_date <= target_date）と当日の株価を組み合わせて PER, ROE を calc_value に実装。
    - すべて DuckDB クエリ主体で実装し、外部 API へのアクセスは行わない設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意の horizons、入力検証あり）。
    - IC（Spearman）計算 calc_ic：欠損・同値・少数レコード等の扱いに配慮。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を算出）。
  - research パッケージの __init__ で主要関数を再エクスポート。

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - market_calendar を起点に営業日判定・翌前営業日検索・期間内営業日の取得・SQ 判定などのヘルパーを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の calendar データがない場合は曜日ベースのフォールバック（平日を営業日とする）を適用。
    - カレンダー更新ジョブ calendar_update_job を実装。J-Quants から差分取得して保存、バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（将来日付過大時のスキップ）をサポート。
    - market_calendar の NULL 値検出時は警告ログを出すなど堅牢化。
  - ETL / pipeline:
    - ETLResult dataclass を実装し、ETL 実行結果（取得件数・保存件数・品質問題・エラー）を集約可能に。
    - テーブル存在チェックや最大日付取得ユーティリティ（DuckDB 対応）を提供。
    - pipeline モジュールの ETLResult を data.etl で再エクスポート。

Internal / Design
-----------------
- ルックアヘッドバイアス防止を一貫した設計方針として採用。datetime.today() / date.today() をアルゴリズム内部で直接参照しない実装により、外部から target_date を注入して再現性のある処理を行えるように設計。
- OpenAI 呼び出しはモジュール単位で個別実装し、テスト時に unittest.mock.patch で差し替え可能にしてモジュール間結合を低減。
- DuckDB の executemany に関する既知の挙動（空リスト不可）を考慮して、パラメータが空のときは executemany を呼ばないガードを導入。
- ロギング: 各主要処理で debug/info/warning/exception ログを出力し運用時のトラブルシュートを容易に。

Fixed
-----
- （初回リリースのため該当なし）

Changed
-------
- （初回リリースのため該当なし）

Deprecated
----------
- （初回リリースのため該当なし）

Security
--------
- OpenAI API キーや各種機密は Settings 経由で環境変数から取得する設計。自動ロードを無効化するフラグを用意し、テスト中や CI 環境での誤動作を防止できる。

Notes
-----
- 本リリースはコアデータ処理・研究用分析・AIベースのニュース評価・カレンダー管理を中心とした初期実装です。実運用では J-Quants クライアント、kabu API 実行部分（execution）や monitoring 部分の追加実装、テストカバレッジ強化、詳細なエラーハンドリング方針の拡充が想定されます。