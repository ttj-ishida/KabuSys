# Keep a Changelog — CHANGELOG.md（日本語）

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

フォーマット:
- Unreleased: 次回リリースに向けた未リリース項目（現時点では空または注記）
- 各バージョンは日付付きで記載

注: 以下の変更点はリポジトリ内のソースコードから推測してまとめたものです。

## [Unreleased]

- （無し）

## [0.1.0] - 2026-03-31

Added
- 基本パッケージ初期実装
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - 行末のコメント判定ルール（クォート外かつ直前が空白/タブの場合に # をコメントとして扱う）
  - protected キー（既存 OS 環境変数）を上書きしない仕組みを導入。
  - Settings クラスを通じたプロパティアクセスを提供（J-Quants / kabu API / Slack / DB パス / 監視設定 / システム設定など）。
  - 設定値のバリデーション: KABUSYS_ENV と LOG_LEVEL の許容値チェック。未設定の必須環境変数では ValueError を送出。

- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP（score_news）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON mode を用いて -1.0〜1.0 のセンチメントを取得。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、1銘柄あたり最大記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数制御）。
    - レスポンス検証: JSON 抽出のフォールバック、"results" リストの検証、未知コードの無視、スコアを ±1 にクリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT のトランザクション）を行い、部分失敗時に既存スコアを保護。
    - タイムウィンドウは JST ベースで定義（前日15:00 JST ～ 当日08:30 JST に相当する UTC 範囲を使用）。ルックアヘッドバイアス防止のため date.today() を参照しない設計。
    - APIキーが未設定の場合は ValueError を送出。

  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini、JSON 出力を期待。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - ma200_ratio が計算不能（データ不足）な場合は中立値 1.0 を使用。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実行、失敗時は ROLLBACK を試行して例外を伝播。

  - AI モジュールはテスト容易性を考慮して、OpenAI 呼び出しを _call_openai_api 関数に抽象化（テストで差し替え可能）。news_nlp と regime_detector は意図的に互いの内部関数を共有しない設計。

- データプラットフォーム（src/kabusys/data/*）
  - マーケットカレンダー管理（calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar がない場合は曜日ベース（土日除外）でフォールバックする堅牢な判定ロジック。
    - next/prev_trading_day の探索上限を設定して無限ループを防止（_MAX_SEARCH_DAYS=60）。
    - calendar_update_job: J-Quants API から差分取得し、バックフィル（直近 _BACKFILL_DAYS=7 日）を行う。取得・保存は jq クライアント経由で冪等保存を行う。

  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを提供（取得/保存件数、品質チェック結果、エラーリスト等を集約）。品質チェックの結果は辞書化して監査ログに使えるように to_dict を実装。
    - 差分更新のための最小日付定義、カレンダー先読み、デフォルトのバックフィル日数を定義。
    - jquants_client と quality モジュールを利用する実装方針。

- 研究 / リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組合せて PER / ROE を計算（EPS が 0/欠損なら None）。
    - 設計は DuckDB を用いた SQL ウェイトで実装、外部 API や発注処理に影響しない。

  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）で将来リターンを計算（入力バリデーションあり）。
    - calc_ic: スピアマンランク相関（IC）を計算するユーティリティ（有効レコード数 3 未満は None）。
    - rank: 同順位は平均ランクを与える実装（浮動小数丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- ロギングとフェイルセーフ設計
  - 多くの箇所で詳細な logger メッセージを出力（info/warning/debug）。
  - 外部 API の失敗に対しては例外で即終了させるのではなくフォールバックまたはスキップする設計（耐障害性重視）。

Fixed
- DuckDB executemany の空リストバインドに起因する問題回避
  - score_news 内の DB 書き込みで、DuckDB 0.10 系の executemany が空リストを受け付けない制約を回避するため、空チェックを入れてから executemany を実行する対策を実装。

Changed
- （初期リリースのため該当なし）

Deprecated
- （無し）

Removed
- （無し）

Security
- OpenAI API キーが未設定の場合は明確に ValueError を送出して処理を停止する箇所あり（意図的な安全策）。機密情報の取り扱いについては環境変数利用を想定。

Notes（設計上の重要ポイント）
- ルックアヘッドバイアス防止: 日付計算や DB クエリは target_date 未満／排他条件を守る等、将来情報参照を避ける実装が徹底されています。
- 冪等性: DB 書き込みは DELETE→INSERT といった置換方式や ON CONFLICT 想定の保存手法で冪等性を確保。
- テスト性良好: OpenAI 呼び出し箇所は差し替え可能に設計されており、ユニットテストでモック化しやすい。
- 外部依存は最小限: 研究モジュール等は標準ライブラリと DuckDB のみで実装され、pandas 等に依存しない方針。

--- 

この CHANGELOG はコードの実装内容から推測して作成しています。実際のコミット履歴やリリースノートに基づく修正が必要な場合は、追加情報を提供してください。