# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース方針: 初期リリース v0.1.0 を記載しています。日付はコードベース解析時点の日付を使用しています。

## [0.1.0] - 2026-03-27

### Added
- パッケージ初期化
  - kabusys パッケージの公開 API を定義（data, strategy, execution, monitoring）。パッケージバージョンは v0.1.0 に設定。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env / .env.local ファイルからの自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - .env の行パーサーを実装:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの扱いを賢く処理（クォート無しでは '#' の直前が空白/タブの場合にコメントと扱う）
  - 環境変数上書きロジック（override）と OS 環境変数保護用の protected セットをサポート。
  - Settings クラスを提供し、各種必須設定（J-Quants, kabuステーション, Slack など）と既定値（DB パス、API ベース URL、ログレベル、環境種別）を公開。無効な値は検証して例外を送出。

- データ処理 / ETL (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却可能に。
  - 差分取得・バックフィル・品質チェックを想定した ETL 設計（J-Quants クライアント連携、idempotent な保存方針、品質チェックの収集方針）。

- マーケットカレンダー管理 (`kabusys.data.calendar_management`)
  - JPX カレンダーの夜間差分取得ジョブ（calendar_update_job）を実装。バックフィル・健全性チェック・J-Quants クライアント経由での差分取得をサポート。
  - 営業日判定ユーティリティを実装:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar の DB 登録値を優先、未登録日は曜日ベースのフォールバック（週末判定）を行う設計。
    - 探索上限 (_MAX_SEARCH_DAYS) による無限ループ防止。

- AI（自然言語処理）機能 (`kabusys.ai.news_nlp`, `kabusys.ai.regime_detector`)
  - ニュースセンチメントスコアリング（score_news）:
    - 前日 15:00 JST ～ 当日 08:30 JST の記事ウィンドウ算出（UTC 変換）と記事集約処理を実装。
    - 銘柄ごとに記事を結合・トリムし、バッチ（最大 20 銘柄）で OpenAI（gpt-4o-mini）に JSON モードで送信してセンチメントを取得。
    - API エラー（429 / ネットワーク断 / タイムアウト / 5xx）は指数バックオフでリトライ、その他はスキップ。レスポンス検証とスコア ±1.0 クリップを実施。
    - スコア書き込みは部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT の冪等更新を行う。
    - テスト容易化のため、OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（score_regime）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組合せてレジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio が計算不能（データ不足）な場合は中立値 1.0 を採用、マクロ記事が無い場合は macro_sentiment=0.0 とするフェイルセーフ。
    - OpenAI 呼び出し失敗時のリトライ、JSON パース失敗時のフォールバック等の堅牢化。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で処理。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金・出来高比率。
    - calc_value: PER（EPS が 0/欠損時は None）・ROE（raw_financials から取得）。
  - 特徴量探索ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得、ホライズン検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（有効データが 3 件未満で None を返す）。
    - rank: 同順位は平均ランクとする安定したランク付け。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - research パッケージから zscore_normalize を再エクスポート。

- 内部設計・実装上の注意点（ドキュメントとしてコード内に明記）
  - 多くのモジュールで datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計を採用（ルックアヘッドバイアス防止）。
  - DuckDB をメインの分析 DB として使用し、SQL と標準ライブラリのみで実装（pandas などの外部依存を避ける方針）。
  - API 呼び出し部分はテストの差し替えを想定して分離（ユニットテスト容易性の確保）。
  - ロギングと警告出力を充実させ、異常系での情報追跡を容易に。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数ロード時に OS 環境変数を保護する仕組み（protected set）を実装。自動ロードを無効化するフラグも提供し、テストや CI での秘密情報漏洩を低減。

---

注: 本 CHANGELOG は提供されたコード内容からの推測に基づいて作成しています。実際のリリースノートには、変更者・テスト結果・互換性情報・既知の制限などを併せて記載することを推奨します。