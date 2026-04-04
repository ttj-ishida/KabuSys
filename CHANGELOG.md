CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い記載しています。  
このプロジェクトは安定化以前の初期リリースです（0.1.0）。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-04
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索するため、CWD に依存せず動作。
    - 自動ロードの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - OS 環境変数は protected として .env 読み込み時に上書きされない。
  - .env 行パーサ: export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント等に対応。
  - Settings クラス: アプリケーション設定値をプロパティとして提供（J-Quants / kabu / LINE / DB / 監視 / システム設定等）。
    - デフォルト値やパスの展開（expanduser）、型変換（float, Path, bool）を実装。
    - 必須 env の取得用 _require()（未設定時は ValueError）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）。
    - is_live / is_paper / is_dev の簡易判定プロパティを提供。
  
- AI 関連 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う calc_news_window 実装）。
    - バッチ/チャンク処理: 1 API call あたり最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたりの記事数上限・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化対策。
    - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（_MAX_RETRIES）。
    - レスポンス検証: JSON 抽出、"results" 配列存在確認、コード整合性、数値パース、スコアの有限性チェック、±1 でクリップ。
    - DuckDB 互換対策: executemany に空リストを渡さない等の実装（DuckDB 0.10 対応）。
    - DB 書き込みは冪等性を考慮（DELETE → INSERT をトランザクション内で実行、ROLLBACK 保護）。
    - テスト支援: OpenAI 呼び出しを差し替え可能（内部の _call_openai_api を patch 可能）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロキーワードで raw_news をフィルタリングし、最大 20 記事を LLM に投げる。
    - LLM 呼び出しに対する堅牢なリトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - スコア合成後クリップ・閾値判定し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI API キー解決（引数優先、未指定なら環境変数 OPENAI_API_KEY。未設定時は ValueError）。
    - Look-ahead バイアス対策: target_date 未満データのみを利用し、datetime.today()/date.today() を参照しない実装。

- 研究（Research）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER・ROE）等を DuckDB 上で計算する関数を提供。
    - データ不足時の None 扱い、結果は (date, code) をキーとする dict リストで返却。
    - DuckDB のウィンドウ関数等を活用した SQL 実装。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns: デフォルト horizons=[1,5,21]、ホライズンの検証あり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関、十分なサンプルが無い場合は None を返す）。
    - rank、factor_summary（count/mean/std/min/max/median）等のユーティリティを実装。
  - research パッケージの __all__ に主要関数をエクスポート。

- データプラットフォーム（Data）モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーを扱うユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末を休場と扱う）を実装。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）や先読み・バックフィルポリシー、健全性チェックを実装。
    - 夜間バッチ（calendar_update_job）: J-Quants から差分取得し market_calendar を冪等的に保存。API エラーや異常時は安全にスキップして 0 を返す。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質問題とエラー集計、to_dict）。
    - ETL 設計方針、差分更新・backfill、品質チェック（quality モジュールとの連携）を考慮したインターフェースを用意。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
  - データアクセスに関する注記: jquants_client を介して外部 API を呼び出す前提（実体は別モジュール）。

- その他
  - モジュール分割とテスト容易性: OpenAI 呼び出しや DB 操作の差し替えを想定した設計（モジュール結合を低減）。
  - ロギングと詳細な警告メッセージを充実させ、異常時に情報を残す実装。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- 新規リリースのため該当なし。

Removed
- 新規リリースのため該当なし。

Security
- OpenAI API キーは引数優先で、引数が無い場合は環境変数 OPENAI_API_KEY を参照。未設定時は明示的に例外を投げる仕組みで誤動作を防止。
- .env 読み込みは OS 環境変数を保護する設計（上書き保護）。

Notes / 実装上の注意
- 多くの関数はルックアヘッドバイアス回避のため datetime.today()/date.today() を直接利用しない実装方針になっています（テストやバッチ実行で明確に target_date を与えることを想定）。
- DuckDB のバージョン互換性に配慮した実装（executemany の空リスト禁止等）。
- OpenAI 呼び出しは JSON Mode を期待したパースを行うが、稀に前後に余計なテキストが付く場合があるため補正ロジックを含みます。
- 一部外部クライアント実装（jquants_client 等）は本リリース内で参照されるが、実体は別モジュールとして分離されています。

--- 

今後のリリースで想定される改善点
- strategy / execution / monitoring パッケージの具現化（現時点では公開名のみ）。
- ai モデル切替やローカル推論器への対応、より細かい品質チェックルールの拡張。
- テストカバレッジ拡大（DB モック、OpenAI レスポンスの多様ケース）。