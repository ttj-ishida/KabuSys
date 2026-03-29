# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化: `kabusys`（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ 指定）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - 自動ロード順序: OS環境変数 > .env.local > .env（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを安全に取得。
  - 必須環境変数未設定時は明示的な ValueError を送出。
  - KABUSYS_ENV, LOG_LEVEL の入力検証（許容値チェック）を実装。

- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - バッチサイズ、文字数・記事数の上限、チャンク処理（最大20銘柄/チャンク）などの肥大化対策を実装。
    - レスポンス検証ロジック（JSON 抽出、結果の型・キー検査、スコアの数値変換・有限性チェック）を実装。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。非再試行エラーはスキップして継続（フェイルセーフ）。
    - スコアは ±1.0 にクリップ。書き込みは部分失敗に備え、取得した銘柄のみ DELETE → INSERT の冪等更新を実行。
    - テスト容易性のため _call_openai_api をモック差し替え可能。

  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出はキーワードベースで raw_news から取得（最大 20 件）。
    - OpenAI 呼び出しに対してリトライ・フェイルセーフを実装。API 失敗時は macro_sentiment=0.0 として継続。
    - レジームスコアの閾値に応じたラベル付与と、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - テスト用に _call_openai_api を差し替え可能。外部モジュールとの過度な結合を避ける設計。

- データプラットフォーム (`kabusys.data`)
  - カレンダー管理 (`data.calendar_management`)
    - JPX カレンダーに基づく営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未登録または未取得の場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェック実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止。

  - ETL パイプライン (`data.pipeline`, `data.etl`)
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー等の集約）。
    - 差分取得、バックフィル、品質チェック統合の基礎実装（J-Quants クライアント経由での差分取得想定）。
    - DuckDB に対する互換性配慮（executemany に空リストを渡さない等）。

  - jquants_client / quality 等のクライアント利用を想定した設計（実装はモジュール外）。

- リサーチ（因子・特徴量） (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離（ma200_dev）を計算。
    - Volatility / Liquidity: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率等を計算。
    - Value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損時は None）。
    - データ不足時の扱い（None 戻し）や DuckDB 上でのウィンドウ関数利用を実装。

  - 特徴量探索・統計 (`research.feature_exploration`)
    - 将来リターン calc_forward_returns（任意ホライズン、ホライズン検証、範囲バッファを適用）。
    - IC（Information Coefficient）calc_ic（スピアマンのランク相関を自前実装、少数サンプル・等分散チェックの扱い）。
    - ランク変換 rank（同順位は平均ランク、丸めで ties 検出安定化）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。

### Design / Implementation Notes
- ルックアヘッドバイアス対策
  - date.today()/datetime.today() を直接参照しない設計（score_news / score_regime などで target_date を明示的に受け取る）。
  - DB クエリは target_date 未満（排他）・または過去方向での参照を徹底。

- 耐障害性
  - LLM 呼び出しの失敗は基本的に例外を上位へ投げず、ロギングしてフェイルセーフな既定値で継続（例: macro_sentiment=0.0, スコア未取得はスキップ）。
  - DB 書き込みはトランザクションを使用し、失敗時は ROLLBACK して報告。

- テスト容易性
  - OpenAI API 呼び出し部分は内部関数を通して実装しており、ユニットテストで容易にモック差し替え可能。

### Fixed
- 初回リリースにつき該当なし。

### Changed / Deprecated / Removed / Security
- 初回リリースにつき該当なし。

---

注: 上記はソースコードから読み取れる設計・挙動に基づく CHANGELOG です。実際の公開パッケージや運用環境での API クライアント実装（jquants_client 等）、および追加ドキュメント・テストは別途必要です。