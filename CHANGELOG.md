CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
さらに詳細な設計意図や使用方法はソースコードのドキュメンテーション（モジュール docstring）を参照してください。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各リリースはバージョン／リリース日／変更カテゴリで記載

Unreleased
----------
（なし）

0.1.0 - 2026-04-01
------------------

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを公開します。
主な追加点・設計上の要点は以下の通りです。

Added
-----
- パッケージ基盤
  - パッケージ定義とバージョン: kabusys v0.1.0 を追加。
  - __all__ に data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーが export プレフィックス、クォート・エスケープ、インラインコメントなどに対応。
  - OS 環境変数を保護する protected 上書きロジックを実装（.env.local は既存 OS 環境変数を上書きしない）。
  - 必須値取得用 _require と Settings クラスを提供。Settings は多くのプロパティを公開:
    - J-Quants / kabu ステーション / Slack / DB（duckdb/sqlite）パス
    - 監視用 PID ファイルパス、CPU/Memory/Disk 閾値（デフォルト値あり）
    - 環境 (development/paper_trading/live) とログレベルの検証
    - is_live / is_paper / is_dev のユーティリティ

- AI ニュース解析 (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - バッチ処理: 最大 20 銘柄ずつ送信、1銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - JSON Mode を使用した厳密な出力期待。レスポンスのバリデーション実装（results キーの検証、未知コード除外、スコアの数値検証、±1.0 にクリップ）。
  - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
  - API キー未設定時は ValueError を送出。API 呼び出しはテスト用に差し替え可能（_call_openai_api を patch 可能）。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部参照しない設計。対象ウィンドウは calc_news_window で明確に計算。

- AI マーケットレジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を統合して日次で市場レジーム（bull / neutral / bear）を判定。
  - マクロニュース抽出用キーワードセット実装（日本・米国・グローバル系）。
  - OpenAI 呼び出しは retry/backoff を実装、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - 結果は冪等に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。
  - テスト容易性のため _call_openai_api を差し替え可能。

- 研究用モジュール (kabusys.research)
  - factor_research: モメンタム（1/3/6M、MA200乖離）、ボラティリティ（20日ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数、統計サマリー（factor_summary）を追加。
  - 設計方針: DuckDB 接続を受け取り SQL + Python で完結、外部 API へアクセスしない。結果は (date, code) をキーとする辞書リストで返す。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management: market_calendar の扱い（営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）と JPX カレンダー夜間更新ジョブ（calendar_update_job）を実装。DB データが無い場合は曜日ベースでフォールバックする堅牢な挙動。
  - pipeline / etl: ETLResult データクラスを提供し、ETL の基本的な差分取得・保存・品質チェックの設計を反映。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- テスト・運用を意識した設計
  - OpenAI への API 呼び出しを patch しやすい点を明示（ユニットテストでモック可能）。
  - DuckDB の executemany の制約に対する回避（空リスト送信を避けるチェック）。
  - ロギングにより異常時の解析を容易にする詳細ログを多用。

Changed
-------
- （初版のため特になし）

Fixed
-----
- （初版のため特になし）

Security
--------
- OpenAI / Slack / kabu API 等のシークレットは環境変数で取得（Settings._require により未設定時は明示的なエラー）。
- .env 自動読み込みは既存 OS 環境変数を保護する実装（protected set）。自動読み込み自体は環境変数で無効化可能。

Notes / Known issues / TODO
---------------------------
- pipeline._get_max_date 関数の実装スニペットが途中で切れているように見える行（ソース末尾に "return date.fro" のような未完の痕跡）が存在します。初回リリースではここが不完全であり、関数の最終実装／単体テストが必要です。
- パッケージ内で参照している外部モジュール（例: kabusys.data.jquants_client や kabusys.data.quality）は本スナップショットには含まれていません。ETL やカレンダー更新系の完全な動作にはそれらの実装が必要です。
- data/__init__.py が空のまま（エクスポートが未記載）になっています。利用側の import パスは現状の実装に合わせて確認してください。
- OpenAI との連携は外部 API に依存するため、API 仕様変更やモデル名変更に対する互換性確認が必要です（コード中に MODEL 名 gpt-4o-mini をハードコード）。
- News/Regime の LLM 出力は厳密な JSON を期待する設計だが、実運用ではLLMの出力の揺らぎをさらに堅牢に扱うための改善余地があります（現在も余分な前後テキストの復元ロジック等を実装）。

Authors
-------
- 初期実装: ソース内 docstring に記載された設計方針に基づいて実装

License
-------
- ソースにライセンス表記がない場合はリポジトリの LICENSE を参照してください。