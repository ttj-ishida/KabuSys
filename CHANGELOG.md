CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
このファイルはリポジトリの第一次リリース（0.1.0）に基づく機能一覧と設計上の要点を、コードベースから推測してまとめたものです。

フォーマット:
- 重要な新機能は "Added"
- 設計方針や実装上の注意点は "Changed" に記載
- バグ修正・フェイルセーフなどは "Fixed"
- 破壊的変更・非推奨・セキュリティ情報は該当する場合に記載

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージトップ: src/kabusys/__init__.py に __version__ と公開モジュールを定義。

- 環境設定管理 (kabusys.config)
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を起点）。
  - .env / .env.local の読み込み順序と上書きルール（OS 環境変数保護機構を実装）。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行内コメント処理を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - Settings クラスにアプリ設定を集約:
    - J-Quants, kabuステーション, Slack, DB パス等の必須/既定値プロパティ。
    - KABUSYS_ENV と LOG_LEVEL の妥当性検証（有効な値集合を限定）。
    - is_live / is_paper / is_dev の補助プロパティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news / news_symbols から銘柄別にニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄）・1 銘柄あたりの最大記事数/文字数制限、JSON モード応答のバリデーションとフォールバック実装。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ。
    - DuckDB への冪等的書き込み（DELETE → INSERT）と部分失敗時の既存データ保護。
    - テスト容易性のため OpenAI 呼び出し箇所をモック可能に設計。
  - 市場レジーム判定 (regime_detector.py)
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - OpenAI（gpt-4o-mini）を使ったマクロセンチメント評価、API 再試行・フォールバック（API 失敗時は macro_sentiment=0.0）。
    - DuckDB の prices_daily, raw_news, market_regime テーブルを参照・冪等書き込み。
    - LLM 呼び出し関数は news_nlp と独立した実装。テスト用に差し替え可能。

- データ関連 (kabusys.data)
  - ETL 用インターフェースの再エクスポート (etl.py → ETLResult)
  - ETL パイプライン支援モジュール (pipeline.py)
    - ETLResult dataclass による実行結果の集約（品質問題やエラー一覧を含む）。
    - テーブル存在チェック、最大日付取得ユーティリティ等を提供。
    - 差分更新・バックフィル・品質チェックの設計思想を実装。
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得 → 冪等保存（バックフィル期間や健全性チェック付き）。
    - 最大探索範囲制限で無限ループ回避。

- 研究用モジュール (kabusys.research)
  - factor_research.py
    - モメンタム (1M/3M/6M)、200 日 MA 乖離、ATR（20 日）、出来高/売買代金関連などのファクターを DuckDB 上で計算。
    - raw_financials を用いた PER / ROE の算出（value）。
    - 結果を (date, code) キーの dict リストで返す仕様。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない、純粋 Python + DuckDB 実装。

Changed (設計方針・注意点)
- ルックアヘッドバイアス対策
  - AI / リサーチの各モジュールは datetime.today() や date.today() を参照せず、呼び出し元から target_date を受け取る設計。
  - DB クエリは target_date 未満/未満等の排他条件でデータを選ぶ工夫あり。

- DuckDB 互換性注意
  - executemany に空リストを渡せない DuckDB バージョン対応のため、空チェックを行ってから executemany を呼ぶ実装。
  - 日付の型変換ヘルパを用いて DuckDB の返り値を安全に date に変換。

- OpenAI 呼び出しとフォールバック
  - JSON モードでも前後に余計なテキストが混ざるケースに備えて最外側の {} 抽出による復元処理を実装。
  - API の失敗（レート制限・ネットワーク・5xx 等）はリトライし、最終的に失敗しても例外を投げずにフェイルセーフなデフォルト（スコア 0.0 やスキップ）を使用する箇所がある。

Fixed
- 初期リリースとして、以下のロバスト化を行いエラー時の安全性を確保:
  - .env ファイル読み込み失敗時の警告出力（例外を投げずに継続）。
  - DB 書き込みでの例外発生時に ROLLBACK を試み、さらに ROLLBACK に失敗した場合はログ出力。

Security
- OpenAI API キーおよび各種機密情報は Settings 経由で環境変数から取得。OpenAI キー未設定時は明示的な ValueError を送出して誤使用を防止。

Known Issues / Notes
- 実行環境依存:
  - .env 自動読み込みはプロジェクトルート検出に依存する。パッケージ配布後に期待通り動作させたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を適切に設定するか明示的に環境変数を設定してください。
- テスト容易性:
  - OpenAI 呼び出し箇所はモックしやすいように設計している（ユニットテスト時の差し替えを推奨）。
- J-Quants / kabu API クライアント（kabusys.data.jquants_client など）はインポート箇所で参照されており、外部 API 呼び出し部分は実際の API 実装/認証情報に依存します。

Unreleased
- （現時点なし）

補足
- 本 CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース差分を参照して更新してください。