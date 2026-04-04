CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージの初回リリース。
- 基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 説明: 日本株自動売買システムの基盤ライブラリ（データ取得・ETL、研究用ファクター、ニュースNLP、レジーム判定、カレンダー管理、設定管理等）。
- 環境設定
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを適切に処理。
  - Settings クラスを提供し、環境変数を型変換・検証して公開（J-Quants、kabu API、LINE、DB パス、監視閾値、実行環境判定など）。
  - 必須設定未定義時は ValueError を発生させる _require を実装。
- データプラットフォーム（data）
  - calendar_management モジュール
    - JPX マーケットカレンダーの夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（週末除外）。
    - DB 登録値優先の一貫した補完ロジックと探索上限 (_MAX_SEARCH_DAYS) を実装。
  - pipeline / ETL
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー一覧等を保持）。
    - 差分更新、バックフィル、品質チェックを想定した設計。
    - DuckDB 互換性を考慮（executemany に空リストを渡さない等の注意）。
  - jquants_client など外部クライアントはデータモジュールから利用する想定（インタフェース呼び出しを使用）。
- ニュースNLP と市場レジーム判定（ai）
  - news_nlp モジュール
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを取得。
    - JST ベースのニュースウィンドウ計算 (前日15:00〜当日08:30 JST) を提供する calc_news_window を実装。
    - バッチサイズ、記事数上限、文字数トリム等のトークン制御を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフによる堅牢化。
    - レスポンス検証ロジック（JSON 抽出、results 配列、code/score のバリデーション、スコアのクリップ）。
    - 書き込みは部分失敗を避けるため対象コードのみ DELETE → INSERT を行う冪等処理。
    - テスト用に _call_openai_api を patch しやすい設計。
  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を融合して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは OpenAI（gpt-4o-mini）を用いて記事タイトルを JSON で評価。API 失敗時はフォールバックで macro_sentiment = 0.0。
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 外部に依存せずルックアヘッドバイアスを避ける設計（内部で date.today() を参照しない、クエリで date < target_date を利用）。
- リサーチ（research）
  - factor_research モジュール
    - Momentum ファクター（1M/3M/6M リターン、200 日 MA 乖離）、Volatility/流動性（20 日 ATR、avg_turnover、volume_ratio）、Value ファクター（per, roe）を計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB を使った SQL ベースの計算で、データ不足時は None を返す等の堅牢な挙動。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の fwd_* を計算。
    - IC（Information Coefficient）算出（calc_ic）: スピアマンランク相関を実装。
    - ランク関数（rank）とファクター統計サマリ（factor_summary）を実装。
    - pandas 等に依存しない標準ライブラリのみでの実装。
- パッケージ公開インタフェース
  - __all__ の整理により主要サブパッケージ（data, research, ai, etc.）を露出。

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- .env 読み込み時、既存の OS 環境変数は保護（protected set を用いた上書き回避）。.env.local を使えば明示的に上書き可能。
- OpenAI API キーの取り扱い: API キーは引数経由で注入可能（テスト性向上）。未設定時は明確な例外を送出。

Notes / Migration / 利用上の注意
- AI 関連（news_nlp.score_news, regime_detector.score_regime）は OpenAI API キー（OPENAI_API_KEY 環境変数、または関数引数）を必須とする。未設定の場合は ValueError が発生する。
- DuckDB を利用する設計上、executemany に空リストを渡すと問題となるバージョンがあるため、空パラメータは明示的に回避している。
- 日付・時間は date / datetime（タイムゾーン非混入）で扱う方針。ニュースウィンドウは UTC naive datetime を返すが、内部ロジックは JST→UTC の固定変換を前提としている。
- テストしやすさを考慮し、OpenAI 呼び出し部分はモック差し替え可能（_call_openai_api を unittest.mock.patch 可能）。
- 自動 .env ロードはパッケージ初期化時に行うため、ユニットテスト等で環境を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用すること。

署名
----
- 作成日: 2026-04-04
- バージョン: 0.1.0

（補足）必要であれば各関数・モジュールごとの詳細な変更点や使用例、移行手順を別途ドキュメントとして作成します。