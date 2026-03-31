CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠し、セクションは安定版リリースごとに記載します。

[unreleased]: https://example.com/kabusys/compare/v0.1.0...HEAD

0.1.0 - 2026-03-31
-----------------

Added
- 初回リリース: KabuSys 0.1.0 を公開。
- パッケージ構成:
  - kabusys: パッケージ本体（__version__ = "0.1.0"）。公開サブモジュールとして data / research / ai 等を含む想定。
- 環境設定 (kabusys.config):
  - .env/.env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索して決定するため、CWD に依存しない。
  - .env のパースは export KEY=val、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントなどに対応。
  - 上書きポリシー: OS環境変数を保護するため protected set を用意。.env は .env.local と読み込み順を分けて処理。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）などのプロパティとバリデーションを実装。
  - 必須環境変数取得時には未設定で ValueError を送出するユーティリティを用意。
- AI (kabusys.ai):
  - ニュースセンチメント: score_news（kabusys.ai.news_nlp）を実装。
    - 対象ウィンドウは前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う）。
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode でバッチ評価（最大 20 銘柄/チャンク）。
    - 429・接続断・タイムアウト・5xx に対する指数バックオフによるリトライ、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップを実装。
    - 成功分のみ ai_scores テーブルに冪等（DELETE → INSERT）で書き込む実装。部分失敗時に既存データを保護する。
  - 市場レジーム判定: score_regime（kabusys.ai.regime_detector）を実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して regime_score / regime_label を算出。
    - OpenAI 呼び出しは専用実装を持ち、API失敗時は macro_sentiment=0.0 にフォールバック（例外を上げず処理継続）。
    - DB への書き込みはトランザクションで冪等に実行（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - OpenAI 呼び出し部分はテスト容易性のため差し替え可能に設計（private 関数を patch してモック可能）。
- リサーチ（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev)。データ不足時は None。
    - Value: EPS を用いた PER と ROE（raw_financials からの最新財務データを使用）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等。
  - 特徴量探索: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関＝IC）、rank、factor_summary（count/mean/std/min/max/median）を実装。
  - 実装方針として DuckDB 接続のみを参照し、外部ライブラリ（pandas 等）に依存しない純 Python + SQL 実装。
  - zscore_normalize を data.stats から再エクスポート。
- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management):
    - market_calendar テーブルを利用した営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック。最大探索日数制限や整合性チェックを実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新（バックフィル・健全性チェックあり）。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを公開（target_date、取得/保存件数、品質問題、エラー集約など）。
    - 差分取得・保存（jquants_client 経由）、品質チェック（quality モジュール連携）を想定した設計。
    - デフォルトのバックフィル日数・カレンダー先読み日数等の定義。
  - etl モジュールは ETLResult を再エクスポート。
- 設計・品質関連の共通方針（コード全体）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を一次データソースと想定し、DB による時系列ウィンドウ処理（ROW_NUMBER / WINDOW 関数等）を多用。
  - DB 書き込みは可能な限り冪等に実装（DELETE→INSERT、ON CONFLICT 想定）。
  - API 呼び出し失敗時のフェイルセーフ（LLM API 失敗はスコア 0.0 またはスキップで継続）。
  - ログ出力と警告を多用して運用時の原因調査を容易にする。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- 初版のため該当なし。

注意事項（移行 / 利用時のポイント）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（各機能を使用する場合）。
  - OpenAI を利用する機能（score_news, score_regime）は OPENAI_API_KEY を引数または環境変数で指定する必要がある。
- 環境設定の自動ロードはプロジェクトルートが見つからない（配布インストールや特殊環境）場合はスキップされる。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- DuckDB のバージョン差異により executemany の挙動（空リスト不可など）に対応するコードが含まれている。運用 DB バージョンに合わせて確認を行ってください。
- OpenAI API のレスポンス形式・SDK の振る舞いが変化した場合に備え、API エラー処理や status_code の扱いは堅牢化しているが、運用環境でのテストを推奨します。

開発上のメモ
- テスト容易性のため、OpenAI 呼び出し部分は内部関数を patch してモック可能に実装されています（unittest.mock.patch を利用）。
- いくつかのモジュールは運用に必要な外部クライアント（jquants_client 等）への依存を想定しています。実行前にそれらのクライアント実装と DB スキーマを揃えてください。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして公開する前に、リリース日・実装詳細・未公開の変更点をプロジェクト関係者と確認してください。）