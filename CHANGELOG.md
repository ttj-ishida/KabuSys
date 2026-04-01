CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン
----------------
- 0.1.0 - 2026-04-01

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-04-01
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージ公開: kabusys、サブモジュールとして data, research, ai, execution, monitoring, strategy 等を想定してエクスポート設定。
- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - .env パーサを実装: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - OS 環境変数の上書きを防ぐための protected キーセット処理。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / データベースパス / 監視閾値 / 環境 (development/paper_trading/live) / ログレベル等のプロパティを提供。未設定の必須キーは _require() にて ValueError を発生させる。
  - duckdb/sqlite 等のパスは Path オブジェクトで返却、閾値は float で返却。
- AI 関連
  - ニュースNLPスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini の JSON mode）で -1.0〜1.0 のセンチメントを算出。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄当たりの記事数・文字数トリム、レスポンス検証（results キー・型・既知コードの照合・スコア数値化）を実装。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフによるリトライ、非再試行のエラーはスキップしてフェイルセーフに継続。
    - JSON レスポンスのパースに頑健化（前後に余計なテキストが混入した場合は最外の {} を抽出して復元）。
    - DuckDB 互換性考慮: executemany に空リストを渡さないガードを追加し、部分失敗時に既存スコアを保護するために書き込みはコードを絞って DELETE→INSERT を実行。
    - テスト容易性のため _call_openai_api をモジュールローカルに実装しパッチ可能に。
  - レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull/neutral/bear）を日次算出。
    - prices_daily からのデータ取得は target_date 未満のみを使用してルックアヘッドを防止。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出しは独立実装（モジュール結合を避ける）。
    - API 失敗やパース失敗時は macro_sentiment を 0.0 にフォールバックし続行（フェイルセーフ）。
    - market_regime テーブルへ冪等的に書き込むトランザクション処理（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- データプラットフォーム関連 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを参照した営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ判定（is_sq_day）を実装。
    - market_calendar が未取得または一部欠損の場合は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants クライアント経由で差分取得・バックフィル・健全性チェックを行い、冪等的に保存。
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー概要等を保持）。to_dict によるシリアライズを提供。
    - 差分更新・バックフィル・品質チェックを想定した設計（J-Quants クライアント呼び出しと quality モジュール連携を前提）。
    - DuckDB テーブル存在チェック等のユーティリティを実装。
- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER / ROE）を計算する関数を実装。prices_daily/raw_financials のみ参照。
    - データ不足時の None 返却、結果は (date, code) キーの dict リストとして返す。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank/統計サマリー（factor_summary）を実装。外部ライブラリに依存しない純粋 Python 実装。
- 互換性・テスト支援
  - OpenAI 呼び出し部分はモジュール内で差し替え可能にしてユニットテスト容易化（unittest.mock.patch を想定）。

Changed
- 初期設計で以下の設計原則を徹底:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() をスコープ内で直接参照しない（target_date を明示的に受け取る）。
  - API 呼び出しは失敗してもプロセス全体を停止させず安全なデフォルトにフォールバックする設計。
  - DuckDB のバージョン差異（executemany の空リスト等）を考慮した実装。

Fixed
- 初期リリースにおける堅牢化:
  - OpenAI API のレスポンスパース失敗時に例外を上位へ伝播させずログに出してフェイルセーフで継続するように実装。
  - market_regime / ai_scores の DB 書き込みにおいてトランザクションとロールバック保護を実装。

Security
- 環境変数管理:
  - 必須トークン・パスワードは Settings で必須化（未設定時は ValueError）。
  - .env 自動ロード時に OS 環境変数を保護する機構を実装。

Notes / Implementation details
- OpenAI への問い合わせは gpt-4o-mini を使用する想定で JSON Mode を利用（レスポンスを厳密な JSON として期待）。
- 各所でログ（logger）を多用し、情報・警告・例外を記録するよう設計。
- DuckDB を主要なローカル分析 DB として利用。Path 型でのファイルパス指定と互換性確保を行う。
- 一部ファイル内で実装途中 / スニペット切れの個所が確認できるため（pipeline モジュールの末尾など）、今後の修正・補完が想定される。

参考
- パッケージバージョンは kabusys.__version__ = "0.1.0" に合わせています。

---

注: 本 CHANGELOG は提示されたコードベースの実装内容から推測して作成したものです。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、より細かな関数単位・コミット単位の差分に基づく CHANGELOG を作成します。