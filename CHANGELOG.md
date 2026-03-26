CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

0.1.0 - 2026-03-26
------------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py: パッケージ名・バージョン・公開サブパッケージ定義（data, strategy, execution, monitoring）。

- 設定（環境変数）管理
  - src/kabusys/config.py
    - .env 自動読み込み実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装:
      - export KEY=val 形式対応、シングル/ダブルクォート処理とバックスラッシュエスケープ処理、行末のコメント判定の細かい挙動を実装。
      - 不正行はスキップ、ファイル読み込み失敗時は警告を出力。
      - OS 環境変数を保護する protected セットを用いた上書き制御（.env.local の上書き等）。
    - Settings クラス:
      - 必須変数チェック（_require 関数）で未設定時は ValueError。
      - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを提供（デフォルト値と型変換を含む）。
      - KABUSYS_ENV, LOG_LEVEL の値検証（有効値集合を厳密にチェック）。
      - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（ニュースNLP & 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事の銘柄別センチメントスコアリング機能（score_news）。
    - タイムウィンドウ計算 calc_news_window（JST 基準 → UTC 変換。ルックアヘッド回避のため内部で date.today() を参照しない設計）。
    - raw_news と news_symbols を用いた銘柄ごとの記事集約（最大 _MAX_ARTICLES_PER_STOCK 件、テキストトリム _MAX_CHARS_PER_STOCK）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（1リクエスト最大銘柄数 = _BATCH_SIZE = 20）、JSON Mode を利用。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフ（最大リトライ回数設定）。
    - レスポンス検証ロジック（JSON の復元・results 配列検査・コード照合・数値検証）とスコア ±1 でクリップ。
    - DB 書き込みは部分失敗を想定した安全な置換処理（対象コードのみ DELETE → INSERT、DuckDB の executemany 空リスト制約に配慮）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして継続。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - MA200 は DuckDB 内の prices_daily（target_date 未満のみ参照）から計算（データ不足時は中立 ma200_ratio=1.0 を採用し警告ログ）。
    - マクロニュース抽出は news_nlp.calc_news_window と raw_news テーブルからマクロキーワードでフィルタ（最大 _MAX_MACRO_ARTICLES）。
    - LLM 呼び出しは独自実装（news_nlp とプライベート関数を共有しない）で再試行と冗長性を持たせ、API失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコアは重み合成（MA70% / マクロ30%）して -1..1 にクリップ、閾値によりラベル付け。
    - DB への書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で、失敗時は ROLLBACK を試行して例外を伝播。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン・ma200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を DuckDB SQL ウィンドウ関数で計算する calc_momentum / calc_volatility / calc_value を提供。
    - 欠損データや計算条件（必要行数不足等）に対する None 返却やログ出力を明示。
    - 結果は (date, code) を含む dict リストで返却。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン、ホライズン妥当性チェック、単一クエリで効率取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、同順位は平均ランク処理）。
    - rank ユーティリティ（round(..., 12) による丸めを用いた同順位処理）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）算出。外部ライブラリ非依存で実装。

  - src/kabusys/research/__init__.py
    - 主要関数の再エクスポート（zscore_normalize, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）。

- Data（カレンダー・ETL・パイプライン）
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルに基づく営業日判定ロジックを提供。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB にカレンダー情報がない場合は曜日ベース（土日休）でフォールバック。
    - next/prev_trading_day 等は DB の登録値を優先し、未登録日は曜日フォールバックで一貫した判定を返す。
    - calendar_update_job: J-Quants クライアント（jquants_client）を用いた差分取得・バックフィル（直近 _BACKFILL_DAYS 日を再フェッチ）・健全性チェック（未来日付過多はスキップ）・冪等保存を実装。
    - 最大探索日数やルックアヘッド・バックフィル日数等の定数化。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult dataclass による ETL 実行結果表現（取得数、保存数、品質問題、エラー一覧、has_errors/has_quality_errors、to_dict によるシリアライズ）。
    - 差分更新・バックフィル・保存（jquants_client の save_* を想定）・品質チェック統合を想定したパイプライン基盤。
    - DuckDB 向けユーティリティ（テーブル存在確認、最大日付取得など）を実装し、初回ロード向け _MIN_DATA_DATE 等を定義。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

  - 互換性/運用面の配慮
    - DuckDB の executemany に関する既知の挙動（空リスト不可）への対応ロジックを含む。
    - DB 書き込み時は部分失敗に備えたコード単位の削除→挿入アプローチを採用し、既存データの保護を考慮。

Misc / Implementation notes
- 全体設計に関する共通ポリシーを明記:
  - AI モジュール（news_nlp, regime_detector）やその他日次処理はルックアヘッドバイアス防止のため datetime.today()/date.today() を内部で参照しない設計。
  - LLM 呼び出しは再試行・バックオフ・フェイルセーフ（失敗時はスコア 0.0 又はチャンクスキップ）で堅牢化。
  - ロギング（logger）を各モジュールに導入し、警告・情報を詳細に出力する実装。
  - OpenAI SDK 呼び出しは専用の内部ラッパー関数を定義し、テスト時に差し替え可能（unittest.mock.patch による差替え想定）。
  - DuckDB の日付/型差異や JSON パースの頑健化（レスポンスに余計な文字列が混ざるケースの復元処理）を考慮。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Security
- なし（初回リリース）。必要に応じて環境変数や API キーの取り扱い方針を追記予定。

Notes / 今後の予定
- strategy / execution / monitoring モジュールはパッケージ公開に含まれているが、今回のコードベースでは主に data / research / ai / config 周りの基盤機能を実装。
- jquants_client の実装・外部 API のモックや実運用時の認証まわり、Slack 通知などの統合は今後追加・拡張予定。