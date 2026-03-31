# CHANGELOG

すべての注目すべき変更をここに記録します。これは Keep a Changelog の形式に準拠しており、意味のあるリリース変更のみを載せています。

最新の変更は常に上に記載します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-31

初回リリース（ベース機能の実装）。主に日本株自動売買プラットフォームのデータ・リサーチ・AI・カレンダー・設定周りの基盤機能を提供します。

### Added
- パッケージ初期公開
  - kabusys パッケージの公開インターフェースを追加（data, strategy, execution, monitoring を __all__ で公開）。
  - バージョン定義: __version__ = "0.1.0"。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動ロードする機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準に探索）。
  - .env/.env.local の読み込み順序および override/protected（OS 環境変数保護）をサポート。
  - export KEY=val 形式、クォート文字列、インラインコメントの取り扱いに対応した .env パーサ実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - 必須環境変数取得時の検査関数（ValueError を送出）。
  - 各種設定プロパティを持つ Settings クラスを提供（J-Quants/OPENAI/Slack/Kabu/API パス、DB パス、監視閾値、環境チェック等）。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。
  - デフォルト値・Path 型変換の提供（duckdb/sqlite/pid ファイルパス等）。

- AI モジュール（kabusys.ai）
  - ニュースベースの銘柄センチメント算出: score_news（gpt-4o-mini を利用、JSON Mode, バッチ処理、最大20銘柄/チャンク）。
    - ニュースウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 に対応）: calc_news_window。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約する _fetch_articles 実装（最大記事数・文字数トリム対応）。
    - API 呼び出しのリトライ戦略（429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出・構造検査・スコア数値化・±1.0 でクリップ）。
    - 部分成功を許容する DB 置換ロジック（取得したコードのみ DELETE → INSERT）により既存スコア保護。
    - テスト容易性のため、OpenAI 呼び出し部を差し替え可能な設計（ユニットテスト用の patch を想定）。

  - 市場レジーム判定: score_regime（ETF 1321 の 200 日移動平均乖離 + マクロセンチメントの合成）
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ使用）。
    - マクロニュースはニュース NLP のウィンドウから抽出して OpenAI でセンチメント評価（gpt-4o-mini）。
    - MA と マクロセンチメントの重み合成（70% / 30%）、スコアを -1..1 にクリップ、閾値で bull/neutral/bear を判定。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT + ロールバックハンドリング）。
    - API 失敗時はフェイルセーフで macro_sentiment=0.0 として継続。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算関数群を実装（prices_daily/raw_financials に依存、外部 API にアクセスしない）
    - calc_momentum: 1M/3M/6M リターンおよび ma200_dev（200 日 MA 乖離）。
    - calc_volatility: ATR(20)/ATR%/20日平均売買代金/出来高比率。
    - calc_value: PER（EPS が 0/欠損なら None）および ROE（最新財務データを結合）。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来リターン取得（複数ホライズンを一度のクエリで取得、horizons バリデーション）。
    - calc_ic: スピアマンランク相関（IC）計算（None と non-finite を除外し有効件数チェック）。
    - rank: 平均ランク（ties を平均ランクで処理、丸めによる ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。

- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX マーケットカレンダー取得・保存用ロジック（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末は非営業日）。
    - DB 優先で未登録日は曜日フォールバックする一貫した動作、探索上限の導入（_MAX_SEARCH_DAYS）。
    - J-Quants クライアント経由で差分取得・バックフィル対応（直近 _BACKFILL_DAYS を再フェッチ）。

  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラーの収集、辞書変換ユーティリティ）。
    - 差分更新・バックフィル・品質チェックを念頭に置いたパイプライン設計（jquants_client 呼び出しを想定）。
    - etl モジュールから ETLResult を再エクスポート。

- テスト容易性・堅牢性
  - OpenAI 呼び出しをユニットテストで差し替え可能な設計（モジュール内の呼び出し関数を patch 可能）。
  - DuckDB を用いた SQL 実装（SQL 内でのウィンドウ関数や LEAD/LAG を活用）。
  - ログと例外ハンドリングを広範に実装（WARN/INFO/DEBUG レベルのメッセージによる観測性）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数取り扱いでの保護（既存 OS 環境変数を保護する protected セットを導入）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

---

注記:
- 全体設計で「ルックアヘッドバイアス」を避ける方針が徹底されており、target_date ベースで過去データのみを参照する実装になっています。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（厳密な JSON 出力）を前提としたバリデーションを行います。API の失敗時はフォールバック（スコア 0.0）して処理を継続するフェイルセーフが入っています。
- DB 書き込みは可能な限り冪等性（既存行の置換）を保つ実装です（DELETE → INSERT や executemany による個別削除など）。
- 今後のリリースでは strategy / execution / monitoring 周りの実装拡充や、より詳細な品質チェック・モニタリング機能の追加を想定しています。