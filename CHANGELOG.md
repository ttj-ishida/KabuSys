# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。セマンティックバージョニングを採用しています。

## [Unreleased]

（現在の状態は初回リリース v0.1.0 としてまとめられています。将来の変更はここに記載します。）

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な機能、設計方針、注意点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0）。主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 行解析は export KEY=val、クォート内エスケープ、インラインコメント処理などに対応する堅牢な実装。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得のヘルパー _require。
  - 各種設定プロパティを持つ Settings クラスを提供（J-Quants / kabuステーション / Slack / DBパス / 環境判定 / ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を制限し不正な値では ValueError を送出）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
    - タイムウィンドウ定義（JST 前日 15:00 〜 当日 08:30 相当の UTC 半開区間）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数と文字数でトリム。
    - レスポンスの検証とスコアの ±1.0 クリップ。
    - 取得スコアは ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗で他銘柄の既存データを保護）。
    - 再試行・指数バックオフ（429・ネットワーク断・タイムアウト・5xx を対象）。非再試行エラーはスキップして継続するフェイルセーフ設計。
    - テスト容易性のため OpenAI 呼び出し関数をパッチ差替え可能（_call_openai_api を patch 可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照し、計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しに対する再試行・バックオフ、API 失敗時は macro_sentiment = 0.0 で継続するフェイルセーフ。
    - レジーム合成時のスコアは -1.0〜1.0 でクリップ。

- データ・ETL（kabusys.data）
  - ETL 結果を表す ETLResult クラスを pipeline モジュール定義から再エクスポート（kabusys.data.etl）。
  - pipeline モジュール（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェックのためのユーティリティ群と ETLResult を提供。
    - DuckDB を用いた最大日付取得やテーブル存在チェックなどの内部ユーティリティを実装。
    - API からの再フェッチ（backfill）を考慮した設計。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 登録がない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - JPX カレンダーの夜間差分取得ジョブ（calendar_update_job）を実装。バックフィルや健全性チェック（将来日付の異常判定）を備える。
    - jquants_client（jq）経由での取得・保存処理を呼び出し、例外時には安全に 0 を返す。

- 研究・ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - momentum（1M/3M/6M リターン, ma200_dev）、volatility（ATR20, atr_pct, avg_turnover, volume_ratio）、value（per, roe）計算関数を提供。
    - DuckDB SQL ウィンドウ関数を活用し、(date, code) 単位の結果リストを返す。
    - データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）は任意ホライズン（デフォルト [1,5,21] 営業日）をサポート。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。
    - ランク関数（rank）および統計サマリー（factor_summary）を提供。
  - zscore_normalize を含むデータユーティリティを再エクスポート。

### Changed / Design Decisions
- ルックアヘッドバイアス対策
  - ほとんどの処理（news scoring, regime scoring, factor/forward 計算など）は内部で datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計とした。
  - DB クエリは target_date 未満 / 排他区間を明示してルックアヘッドを防止。

- エラー・フォールバック方針
  - LLM や外部 API の失敗は例外で即停止させず、適切なデフォルト（例: macro_sentiment = 0.0）で継続するフェイルセーフ設計。DB 書き込み失敗時のみ例外を伝播して上位で対処可能とする。

- DuckDB 互換性対応
  - executemany に空リストを渡さない（DuckDB 0.10 の制約）など、実行時エラー回避のためのガードを追加。
  - 日付の取り扱いは明示的に date オブジェクトを使用し、DuckDB の戻り値を date に変換するユーティリティを用意。

- OpenAI 呼び出し
  - JSON Mode（response_format={"type": "json_object"}）を利用し、厳密な JSON 出力を期待するプロンプト設計。
  - テスト用に _call_openai_api をモジュール内で分離しており、unittest.mock.patch による差し替えが可能。

### Fixed / Robustness
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内のエスケープ、インラインコメント処理などを実装して .env のパースミスを低減。
  - .env の読み込み失敗時は警告を出力して処理継続。

- DB 書き込みの冪等性
  - score_regime / score_news 等で冪等的な書き込みパターン（DELETE→INSERT をトランザクション内で実行）を採用し、再実行に耐える仕様。

### Security
- 環境変数に依存する API キー類は Settings / 関数引数で注入可能にし、明示的に未設定時は ValueError を送出して誤使用を防止。

### Notes / Known limitations
- OpenAI モデルとして gpt-4o-mini を指定しているが、API 契約やモデルの変更に依存するため環境変数や引数でキーを渡して利用してください。
- ETL やカレンダー更新は jquants_client 実装に依存しており、外部 API の応答や仕様変更が影響します。
- いくつかの高度な指標（PBR、配当利回りなど）は現バージョンで未実装。
- strategy / execution / monitoring パッケージ名は公開されているが、ここに含まれない具体的な実装は別途追加予定。

---

今後のリリースでは API 互換性のある追加機能、性能最適化、監視/アラート機能の充実、さらに戦略実行周りの実装を予定しています。