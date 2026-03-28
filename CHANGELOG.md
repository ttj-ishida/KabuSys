CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」準拠です。
リリースはセマンティックバージョニングに従います。

Unreleased
----------

（なし）

0.1.0 - 2026-03-28
------------------

Added
- 初回公開リリースを追加。
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring）。
- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索するため、CWD に依存しない動作。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理などをサポート。
  - Settings クラスを提供（環境変数から値を取得するプロパティ群）。
    - J-Quants / Kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの検証とデフォルト値を実装。
    - 必須値未設定時は ValueError を送出するユーティリティを提供。
- AI（kabusys.ai）
  - news_nlp モジュール（score_news）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価を実装。
    - チャンク（最大20銘柄）での API 呼び出し、トークン肥大対策（記事数上限、文字数トリム）、JSON Mode を想定したレスポンスバリデーションを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライを実装。部分成功時に既存スコアを保護するため、書き込みは対象コードの DELETE → INSERT に限定。
    - calc_news_window ユーティリティを提供（JST の前日 15:00 ～ 当日 08:30 を UTC ベースで扱う）。
  - regime_detector モジュール（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロ記事は raw_news からマクロキーワードでフィルタして取得し、LLM（gpt-4o-mini）でセンチメント評価。
    - API 失敗時は macro_sentiment = 0.0 のフェイルセーフを採用。API 呼び出しのリトライ・エラーハンドリングを実装。
- Data（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー（market_calendar）を扱う営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先、未登録日は曜日ベースでフォールバックする一貫性のあるロジック。
    - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理を実装（バックフィル/健全性チェック含む）。
  - pipeline / etl モジュール
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプライン設計：差分更新、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）などの仕組みのためのユーティリティを実装。
    - テーブル存在チェックや最大日付取得等の DB ヘルパーを実装。
- Research（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER/ROE）などのファクター計算を実装。
    - DuckDB 上の SQL とウィンドウ関数を用いる実装で、データ不足時の挙動（None を返す）を明確化。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（スピアマン）計算（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL で実装。
- 内部ユーティリティ・堅牢化
  - DuckDB 操作における冪等書き込みパターン（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）を各所で採用。
  - JSON レスポンスパースに対して余計な前後テキストが混ざるケースの復元ロジックを実装（最外側の {} を抽出してパース）。
  - DuckDB の executemany に対する空リスト問題（DuckDB 0.10）を考慮して空チェックを導入。

Changed
- 設計方針周りの明文化
  - 全モジュールで「datetime.today()/date.today() によるルックアヘッドを行わない」方針を明記。target_date 引数依存に統一。
  - API 呼び出しの失敗時はフェイルセーフで継続（一部モジュールでは 0.0 / スキップ を返して上位へ例外を伝播しない実装）とした。
- OpenAI 呼び出し実装はモジュール間でプライベート関数を共有せず、それぞれ独立実装に変更。
- news_nlp と regime_detector のレスポンス検証・リトライロジックを強化。

Fixed
- OpenAI レスポンスのパース失敗や API エラー時に、例外投げっぱなしではなく警告ログ出力とフォールバック（0.0 またはスキップ）を行うように改善。
- DuckDB に対する executemany の空リストバインドで失敗する問題に対処（空チェックを追加）。
- market_calendar の NULL 値が混入した場合のフォールバックと警告ログ出力を追加して不整合時の挙動を明確化。
- calc_news_window の UTC 計算を明確化（JST -> UTC の変換をドキュメント化）。

Security
- OpenAI API キーや各種シークレットは環境変数経由でのみ取得し、Settings にて必須チェックを行うことで未設定時に明示的なエラーを出すようにした（キーをコード中に埋め込まない運用を前提）。

Known issues / Notes
- DuckDB バインドの互換性（特にリスト型バインド）はバージョン差で挙動が異なるため、executemany による個別 DELETE を採用。将来の DuckDB バージョンで改善の余地あり。
- OpenAI のモデル/API の挙動（JSON Mode の完全性や rate-limit のポリシー）に依存する部分があり、実運用では API キー管理・レート管理・コスト管理の運用ルール整備が必要。
- 一部の外部クライアント（jquants_client など）はインターフェース想定のみで実装は別モジュール側に委ねられます。実際の API クライアント実装との接続時に追加のエラーハンドリングが必要になる場合があります。

Acknowledgements
- 初期実装リリース。今後の改善・バグ修正・機能拡張は Unreleased セクションに追加していきます。