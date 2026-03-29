Keep a Changelog に準拠した CHANGELOG.md（日本語）です。

全体のバージョンはパッケージ内の __version__ = "0.1.0" を基にしています。

なお、日付はリリース日として本ファイル作成時の日付を設定しています（必要に応じて調整してください）。

KEEP A CHANGELOG
================

すべての変更は分類 (Added, Changed, Fixed, Deprecated, Removed, Security) に従って記載します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初版を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本モジュール構成
  - kabusys.__init__: パッケージ公開 API を定義（data, strategy, execution, monitoring）。
  - kabusys.config: 環境変数 / .env 読み込みと Settings クラスを提供。
    - .env 自動ロード機能（プロジェクトルート判定: .git または pyproject.toml を基準）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサ: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを考慮した堅牢な実装。
    - protected set: OS 環境変数を上書きしない保護機構。
    - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得。env と log_level の値検証（不正値は ValueError）。
    - 必須値未設定時は _require が ValueError を投げる。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp:
    - ニュースのタイムウィンドウ計算 calc_news_window。
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）で一括スコアリングし、ai_scores テーブルへ書き込む score_news。
    - バッチ処理（1 API 呼び出しあたり最大 _BATCH_SIZE = 20 銘柄）、1 銘柄あたりの記事トリム（最大 _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI への呼び出しは JSON Mode を利用し、厳密な JSON を期待。レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - リトライ/バックオフ: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフで再試行。その他エラーはスキップして継続（フェイルセーフ）。
    - テスト用に _call_openai_api をモック可能（unittest.mock.patch で差し替え推奨）。
    - API 未設定時は ValueError を送出。

  - kabusys.ai.regime_detector:
    - ETF 1321（日経225連動ETF）200日移動平均乖離（MA 要素）とマクロ経済ニュースの LLM センチメント（マクロ要素）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime。
    - MA 要素は prices_daily から target_date 未満のデータのみを利用（ルックアヘッド防止）。
    - マクロニュースは news_nlp.calc_news_window と raw_news のフィルタで取得、最大 _MAX_MACRO_ARTICLES 件を LLM に渡す。
    - レジームスコア合成に重み付け（MA 70%、MACRO 30%）・スケーリング・クリッピングを適用。しきい値でラベルを割当。
    - OpenAI 呼び出しのリトライ/例外ハンドリングを実装。API 失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラー時のロールバック処理。

- Research（調査）モジュール
  - kabusys.research.factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）の計算を SQL で実行。データ不足時の None 処理。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true range の NULL 伝播を考慮。
    - calc_value: raw_financials から直近の財務データを取得し PER / ROE を計算（EPS が 0 または欠損の場合は None）。price と財務の組合せ。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。ホライズン検証（正の整数かつ <=252）。
    - calc_ic: スピアマンランク相関（IC）を計算。3 銘柄未満は None。
    - rank: 平均ランクを返す（同順位は平均ランク）。浮動小数丸めで ties を検出する安全な実装。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - zscore_normalize は data.stats から再エクスポート（研究用途に利用可能）。

- Data（データ基盤）モジュール
  - kabusys.data.calendar_management:
    - 市場カレンダー管理：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB（market_calendar）にデータがある場合は DB 値を優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - カレンダー更新ジョブ calendar_update_job: J-Quants API から差分取得し、バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（将来日付の異常検知）を行い、jquants_client.save_market_calendar を使って冪等保存。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ防止。
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETLResult データクラス（ETL 実行結果の集約、品質問題の収納、エラー一覧、シリアライズ用 to_dict）。
    - 差分更新・バックフィル方針、品質チェック（quality モジュール）との統合方針を実装するための基盤。

- tests / 開発支援
  - 各所にテスト容易化のための差し替えポイントを用意（例: _call_openai_api を patch）。

Changed
- 新規リリースのため「Changed」はなし。

Fixed
- 新規リリースのため「Fixed」はなし。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー（OPENAI_API_KEY）や各種外部 API トークン / パスワードは環境変数で管理する設計。Settings._require は未設定時に ValueError を投げるため、運用時に機密情報の設定を忘れると起動時に明示的に失敗します。
- .env 読み込み時に OS 環境変数が保護される（.env による上書きを防止）仕組みを導入。

Notes / 既知の設計上のポイント
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・ファクター計算等、すべて target_date の前日/過去データのみを参照するように設計されています。
  - datetime.today()/date.today() を直接参照しない関数設計が優先されています（再現性確保）。
- フェイルセーフ設計:
  - OpenAI 呼び出しや外部 API 失敗時には「失敗を許容して継続」する設計（スコア = 0.0 / スキップ等）を多くの箇所で採用しており、部分的な障害が全体を停止させないようになっています。
- DuckDB の互換性注意点:
  - executemany に空リストを渡せない等の制約に対応するため、空チェックを行ってから DB 操作を行っています。
- テスト・モック:
  - OpenAI 呼び出し部やファイル読み込みで副作用を切り離せる hook が用意されているため unit-test が容易です。

今後のリリース候補（提案）
- エラー監視とリトライポリシーの統一的な抽象化（各 AI 呼び出しで同様のコードが存在するため）。
- ai/regime_detector と ai/news_nlp の API 呼び出し部分の共通化（現在は意図的に別実装だが、共通ライブラリ化の検討）。
- docs に使用方法、環境変数一覧（.env.example）および ETL 実行手順を追加。

お問い合わせ
- この CHANGELOG の内容に誤りや追加して欲しい点があれば教えてください。日付の変更やリリースノートの粒度（より技術的 or より利用者向け）も調整可能です。