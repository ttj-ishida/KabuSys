# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。

### Added
- パッケージ基盤
  - パッケージバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 公開 API のエクスポートを定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装。読み込み優先順位は OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、.env の読み込み失敗時の警告出力に対応。
  - .env のパースは export プレフィックス、クォート／エスケープ、インラインコメント等に対応。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等の取得とバリデーションを提供。必須環境変数未設定時は ValueError を送出する `_require` を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを取得して ai_scores テーブルへ書き込む機能を実装（score_news）。
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ計算（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数制限）、JSON Mode のレスポンス検証、スコア ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時は個別チャンクをスキップして継続するフェイルセーフ設計。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api をモック可）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する機能を実装（score_regime）。
    - MA200 比率の算出、マクロキーワードに基づく raw_news 抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ、リトライロジックやログを実装。
    - テスト用に OpenAI 呼び出しの差し替えを想定。

- データ処理（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline / etl）
    - ETL 実行結果を表すデータクラス ETLResult を実装（取得数・保存数・品質問題・エラー一覧などを保持、has_errors/has_quality_errors/proto変換 to_dict を提供）。
    - 差分取得/バックフィル/品質チェックの設計方針に基づくユーティリティ（テーブル存在確認や最大日付取得など）。
    - etl モジュールで ETLResult を再エクスポート。

  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間ジョブ calendar_update_job を実装。バックフィル・先読み・健全性チェック（将来日付の跳躍検出）に対応。
    - DB にデータがない場合は曜日ベースでフォールバック（週末を非営業日扱い）する一貫した動作。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）等の計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB を用いた SQL ベースの実装で、prices_daily / raw_financials のみ参照。結果は (date, code) をキーとする dict のリストで返す。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の fwd リターンを一括で取得する効率的なクエリを実装。
    - IC 計算（calc_ic）: factor と将来リターンのスピアマンランク相関を実装（少数データ時のガード、None 返却）。
    - ランク変換ユーティリティ（rank）と統計サマリー（factor_summary）を実装。pandas 等外部依存なしで標準ライブラリのみで実装。

### Changed
- 設計上の重要な方針を明確化
  - AI モジュール・NLP はルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定）し、部分失敗時に既存データを保護する手法を採用。
  - DuckDB executemany に対する互換性考慮（空リストでの executemany 回避）を実装。

### Fixed
- フェイルセーフ・堅牢性強化
  - OpenAI/API 呼び出しの失敗（429/ネットワーク断/タイムアウト/5xx）に対してリトライ・フォールバックを実装。最終的に API が使えない場合でも処理を継続し、推定値を中立（0.0 / 1.0）にする動作を確立。
  - .env ファイルの読み込み時の I/O エラーを警告化してプロセスを継続するように改善。
  - トランザクション中の例外発生時に ROLLBACK を試行し、ROLLBACK 自体の失敗は警告ログに留め上位へ例外を伝播する実装とした。

### Security
- 現時点でのセキュリティ関連の変更はありません。API キー等の機密情報は環境変数経由で取得し、.env の取り扱いに注意する設計です。

---

※ 本 CHANGELOG は、提供されたソースコードの内容から機能・挙動を推測して作成しています。実際のリリースノートとして使用する際は、リリース時のコミット履歴や運用上の判断に基づき適宜修正してください。