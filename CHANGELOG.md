KEEP A CHANGELOG
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。

Unreleased
----------
- 小さな改善・リファクタリングやテストの追加などが予定されています。
- 予定の例:
  - ETL パイプラインの追加メトリクスと詳細な監査ログ
  - OpenAI 呼び出しのモニタリング・メトリクス出力
  - strategy / execution / monitoring サブパッケージの追加ドキュメント強化

0.1.0 - 2026-03-31
-----------------

初回リリース。日本株自動売買システムのコアユーティリティ群を実装しました。主な追加点は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージの公開開始。__version__ = 0.1.0、主要サブパッケージ（data, strategy, execution, monitoring）をエクスポート。

- 設定 / 環境変数読み込み（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ:
    - コメント行・空行を無視。
    - export KEY=val 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - Settings クラスにより型変換や既定値・バリデーションを提供（J-Quants / kabu API / Slack / DB パス /監視閾値など）。
  - 環境変数未設定時の明確なエラーメッセージ（_require）。

- ニュース NLP / マクロレジーム判定（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini, JSON Mode）へ最大 20 銘柄ずつバッチ送信してセンチメントスコアを取得。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で厳密に計算。
    - 1銘柄あたりの記事・文字数上限の実装（記事数トリム / _MAX_CHARS_PER_STOCK）。
    - レスポンス検証（JSON パース、results リスト・各要素 code/score チェック、未知コードは無視、数値の有限性確認）。
    - スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは「取得済みコードのみを DELETE → INSERT」して部分失敗時に既存データを保護。
    - API エラー（429、接続断、タイムアウト、5xx）に対する指数バックオフによるリトライ制御。
    - テストのため _call_openai_api をモック可能に設計。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - MA200 は target_date 未満のデータのみ利用しルックアヘッドバイアスを防止。データ不足時は中立扱い（ma200_ratio=1.0）。
    - マクロ記事がない場合や API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - OpenAI のエラー処理（リトライ・5xx 判定）とレスポンス JSON パースの堅牢化。
    - 結果は idempotent に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を元にした営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベース（週末を休日）でフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・保存を行う処理を実装。健全性チェック（極端な未来日付検出）を導入。
  - pipeline / ETL:
    - ETLResult データクラスを導入し、ETL の取得数・保存数・品質問題・エラー情報を集約できるようにした。
    - 差分更新、backfill、品質チェックのための設計方針に基づく基礎的な実装（jquants_client との連携を想定）。
    - kabusys.data.etl は ETLResult を再エクスポート。
  - DuckDB 互換性考慮:
    - executemany に空リストを渡せない制約を回避するため、空チェックを事前に行うなどの安全策を導入。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。NULL の伝播とカウント制御に注意。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0・NULL の場合は None）。
    - 設計上、prices_daily / raw_financials のみ参照し本番口座や外部発注 API への副作用は無し。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターン（LEAD）を一括取得。horizons 引数のバリデーションを実施。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。必要件（有効レコード >=3）を満たさない場合は None。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、各ファクターの基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージは主要関数を __all__ でエクスポート。

Changed
- （初回リリースのため過去バージョンとの差分はなし）

Fixed / Robustness improvements
- OpenAI レスポンスの JSON パースが不正な場合でも、文字列から最外層の {} を抽出して復元を試みるフォールバックを追加（news_nlp）。
- API エラー処理を詳細化:
  - RateLimitError / 接続断 / タイムアウト は指数バックオフでリトライ。
  - APIError の status_code を安全に取得し 5xx の場合は再試行、それ以外は即時フォールバック。
  - 全リトライ消費時は警告ログを出力して安全側値（例: macro_sentiment=0.0）で継続。
- DuckDB 関連の互換性対策（executemany に空リストを渡さない、日付変換ヘルパーなど）。
- ルックアヘッドバイアス対策: 全ての AI / リサーチ処理で内部的に date.today() を直接参照せず、呼び出し元から target_date を受け取る設計。

Documentation / Design notes
- 各モジュールに豊富な docstring を記載し、処理フロー・設計方針・フェイルセーフの挙動を明示。
- テスト容易性を考慮して、OpenAI 呼び出しのプライベート関数をモック可能に設計（ユニットテストでの差し替えを想定）。

Security
- API キー（OpenAI）未設定時は明確な ValueError を返す。API キーは引数で注入可能なのでテスト時に環境変数を汚染しない設計。

Notes / Migration
- 本バージョンは「コア機能の初期実装」であり、外部サービス（J-Quants / OpenAI / kabuAPI）への接続点は抽象化されています。運用前に .env の設定や DuckDB スキーマの準備、関連 API クレデンシャルの配置が必要です。

Acknowledgements
- このリリースは DuckDB を組み込みデータストア、OpenAI（gpt-4o-mini）の JSON Mode を用いた NLP、J-Quants クライアントとの連携を前提とした構成になっています。