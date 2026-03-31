KEEP A CHANGELOG
=================

このファイルは Keep a Changelog の形式に従っており、変更履歴を時系列で記録します。
例: https://keepachangelog.com/ja/1.0.0/

全般
----
- このリポジトリは日本株自動売買システム「KabuSys」の初期実装を含みます（バージョン 0.1.0）。
- 主な技術スタック: Python、DuckDB、OpenAI API（gpt-4o-mini 想定）、J-Quants API（データ取得用）。
- 設計上の方針や多くの個別処理で「ルックアヘッドバイアス防止（datetime.today()/date.today() を直接参照しない）」や「DB への冪等書き込み」「API 再試行／フェイルセーフ」を重視しています。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージの初期公開。
  - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を追加。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 強化された .env パーサを実装:
    - コメント行・空行の無視、export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを導入し、アプリケーション設定（J-Quants / kabu / Slack / DB パス / 環境切替 / ログレベル判定等）をプロパティ経由で提供。
  - 必須変数未設定時は _require() が ValueError を投げて明確に通知。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news):
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を使って一括でセンチメントを取得。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数でトリム）、レスポンスバリデーションを実装。
    - 429/ネットワークエラー/タイムアウト/5xx に対する指数バックオフ再試行。失敗時はログを残してスキップ（フェイルセーフ）。
    - 結果は ai_scores テーブルへ冪等的に置換（該当 code の DELETE → INSERT）し、部分失敗時に既存データを保護。
    - calc_news_window: JST基準のニュース収集ウィンドウ算出ユーティリティを追加（前日15:00～当日08:30 JST を UTC に変換）。
    - テスト容易性のため _call_openai_api をラップして patch 可能に。
  - 市場レジーム判定 (regime_detector.score_regime):
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出のためのキーワードリスト、最大件数制限、OpenAI 呼び出しの再試行ロジックを実装。
    - API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とエラー時のロールバック処理。
    - news_nlp と同様に OpenAI 呼び出しを独立実装してモジュール結合を避ける設計。

- Data モジュール (kabusys.data)
  - カレンダー管理 (calendar_management):
    - JPX カレンダーを扱うユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - カレンダー更新ジョブ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - DB に不整合（NULL 等）がある場合のログ出力とフォールバックを実装。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー一覧等を保持）。
    - 差分取得、バックフィル動作、品質チェック呼び出し、idempotent 保存の方針を実装方針として明記。
    - 内部ユーティリティとしてテーブル存在チェックや最大日付取得処理を実装。
  - jquants_client の抽象（実体は別モジュール想定）との連携点を用意。

- Research モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1/3/6ヶ月リターン、ma200乖離）、ボラティリティ（20日 ATR、相対ATR、出来高関連）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算で、欠損時の扱い（None）やログ出力を明記。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク化ユーティリティ（rank）、ファクターサマリー（factor_summary）を実装。
    - pandas 等に依存せず純標準ライブラリで実装、境界条件（horizons 上限等）検証を実装。

- パッケージの内部公開 API 整備
  - 複数モジュールで __all__ を適切にエクスポート（ai, research, data.etl など）。

Changed
- 設計ドキュメント→実装への反映:
  - 各モジュール内ドキュメントに DataPlatform.md / StrategyModel.md 等の設計参照を追加し、実装と設計方針を明示。

Fixed
- DB 書き込み安全性強化:
  - DuckDB の executemany が空リストに弱い点を回避するため、空チェックを追加（score_news 等）。
  - トランザクション（BEGIN / COMMIT / ROLLBACK）を明示的に使用、ロールバック失敗時のログ出力を追加。

- レスポンスパース耐性向上:
  - OpenAI JSON mode でも前後に余計なテキストが混入するケースへ対応（外側の { } を抽出して再パース）。
  - レスポンスで想定外の型・欠損があった場合はスキップしつつ警告ログを出す実装。

Security
- センシティブなキーの扱い:
  - OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から取得。未設定時は明示的に ValueError を投げる。
  - .env 読み込み時に OS 環境変数を保護する（protected set）挙動を実装。

Notes / Implementation details
- ルックアヘッドバイアス防止:
  - AI 評価やリサーチ系の処理では datetime.today() / date.today() を直接参照せず、必ず target_date を呼び出し元から渡す設計。
- フェイルセーフ設計:
  - 外部 API エラーは基本的に「ログを残してスキップ」または「デフォルト値（例: 0.0）を使用」し、上位の処理が継続できるようにしている。
- 冪等性:
  - DB 保存処理は既存レコードの上書き（DELETE → INSERT, または ON CONFLICT）を推奨し、部分失敗時のデータ消失を最小化する手順を取っている。

今後の TODO（想定）
- jquants_client 実装の統合（API 実体の提供）。
- kabu ステーション API 実行・発注ロジック（execution モジュール）とモニタリング周りの実装拡充。
- テストカバレッジ強化（特に OpenAI 呼び出しのモックと DuckDB を使った統合テスト）。
- ドキュメント: API 使用方法・ETL 運用手順の詳細化。

署名
----
KabuSys チーム（実装から推測して記載）