Keep a Changelog
=================

すべての重要な変更履歴をここに記録します。形式は Keep a Changelog に準拠します。

[Unreleased]

[0.1.0] - 2026-03-31
-------------------

Added
- 基本
  - パッケージ初期リリースを追加（kabusys v0.1.0）。
  - パッケージ公開 API: kabusys.__all__ に data, strategy, execution, monitoring を定義。
  - バージョン情報: kabusys.__version__ = "0.1.0"。

- config: 環境変数・設定管理
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの自動検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを決定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱いの制御など。
    - 無効行（空行・コメント・キーなしなど）は無視。
  - 読み込み時の保護機構:
    - override フラグ、protected キーセット（既存 OS 環境変数保護）をサポート。
    - ファイル読み込み失敗時は警告ログを出力して安全に継続。
  - Settings クラスを実装し環境変数をラップ:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定（env, log_level）などのプロパティを提供。
    - 必須環境変数未設定時は ValueError を発生させる `_require` を利用。
    - env / log_level は値検証（許容値のチェック）を行う。
    - Path は expanduser() を用いて解決。

- AI: ニュース NLP と レジーム判定
  - ai.news_nlp: ニュース記事の銘柄ごとのセンチメントスコアリング機能（score_news）を実装。
    - 対象時間ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - raw_news と news_symbols を結合して銘柄毎に記事を集約（最大記事数・最大文字数でトリム）。
    - バッチ処理（最大 20 銘柄／コール）で OpenAI（gpt-4o-mini, JSON Mode）へ送信。
    - リトライ戦略: 429、接続断、タイムアウト、5xx に対して指数バックオフで再試行。
    - レスポンスのバリデーション処理を実装（JSON パース、results リスト・コード一致・スコア数値性・クリッピング）。
    - 書き込みは ai_scores テーブルへ冪等的に（DELETE → INSERT）行い、部分失敗時に他銘柄の既存データを保護。
    - DuckDB 互換性のため executemany に空リストを渡さない等の注意点を実装。
    - テスト用に内部の OpenAI 呼び出し関数をパッチ差し替え可能に設計。
  - ai.regime_detector: 市場レジーム判定（score_regime）を実装。
    - ETF 1321 の 200 日移動平均乖離（比率）とマクロニュースの LLM センチメントを合成してレジーム（bull/neutral/bear）を日次判定。
    - LLM（gpt-4o-mini）呼び出しは独立実装、最大リトライ、5xx 判定の扱いなど踏襲。
    - マクロキーワード一覧を定義して raw_news からタイトル抽出。
    - API 失敗時は macro_sentiment=0.0 としてフォールバックするフェイルセーフ挙動。
    - 計算後に market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - ルックアヘッドバイアス防止のため date.today()/datetime.today() を参照しない設計（target_date を明示的引数）。

- research: ファクター計算・特徴量探索
  - research パッケージ公開 API を追加（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足は None。
    - calc_volatility: 20 日 ATR（true range の扱いを明示して NULL 伝播を制御）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出。最新財務レコードの選択は ROW_NUMBER による。
    - 設計上、DuckDB 上の SQL と Python を組み合わせ外部 API に依存しない実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを LEAD を用いて一括取得。
    - calc_ic: スピアマンランク相関（ランク処理は同順位平均ランク）を計算。有効レコード数が 3 未満なら None を返す。
    - rank: 値からランクへ変換（丸めによる ties 対策）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。

- data: データ基盤ユーティリティ
  - data.calendar_management:
    - JPX カレンダー管理用ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar テーブルが無い場合は曜日ベースのフォールバック（平日を営業日）を採用して堅牢化。
    - next/prev_trading_day では DB 登録値優先、未登録日は曜日フォールバックで一貫した挙動。
    - カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants API から差分取得→jq.save_market_calendar による保存、バックフィル・健全性チェックを含む）。
  - data.pipeline / data.etl:
    - ETLResult データクラスを追加し ETL 実行結果（取得数、保存数、品質問題、エラー一覧等）を構造化。
    - pipeline モジュールの ETLResult を data.etl で再エクスポート。
    - DuckDB 上のテーブル存在チェックや最大日付取得等のユーティリティを追加（ETL の差分取得ロジック基盤）。
    - ETL の設計方針として差分更新・バックフィル・品質チェック（致命的問題があっても収集を継続）を採用。

- その他設計上の注意点（横断）
  - ルックアヘッドバイアス防止: スコア計算関数群は内部で date.today()/datetime.today() を参照せず、必ず target_date を引数として受け取る。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 相当）し、トランザクションの失敗時には ROLLBACK とログ記録を行う。
  - OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用し、レスポンス耐性を高める工夫（前後の余分なテキスト抽出など）を実装。
  - テスト容易性のため OpenAI 呼び出し関数や一部内部関数をパッチ/モック差し替え可能に設計。
  - DuckDB バージョン依存性への配慮（executemany に空リストを渡さない等の互換性対策）を実装。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- なし（初回リリース）

脚注 / 備考
- 実装は各モジュール内の docstring に設計意図・処理フロー・フォールバックルールが記載されています。運用時は .env.example を参照して必須環境変数を設定してください。
- OpenAI の API キーは関数引数で注入可能（api_key）であり、未指定時は環境変数 OPENAI_API_KEY を参照します。