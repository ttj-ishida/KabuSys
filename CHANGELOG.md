# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

現行バージョンは 0.1.0 です（初回公開リリース）。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。主要サブパッケージ/モジュールをエクスポート:
    - data, research, ai, execution, strategy, monitoring（__all__ にて宣言）。
  - バージョン情報: __version__ = "0.1.0"。

- 設定管理（kabusys.config）
  - .env/.env.local を自動ロード（優先度: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない）。
  - 環境変数パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、行末コメント処理（条件付き）。
    - 不正行は安全に無視。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数の保護機能（.env の上書き制御）。
  - Settings クラスを提供（settings インスタンス）:
    - J-Quants / kabuステーション / Slack / データベースパス / ログレベル / 実行環境（development, paper_trading, live）などのプロパティ。
    - 必須キー取得時の _require で未設定は ValueError を送出。
    - env/log_level の検証ロジック、is_live/is_paper/is_dev のヘルパー。

- データ関連（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未登録のときは曜日ベースのフォールバック（週末=非営業日）。
    - night batch job: calendar_update_job により J-Quants から差分取得し冪等保存。
    - 安全対策: 最大探索日数や健全性チェック、バックフィル日数を設計。
  - etl / pipeline:
    - ETLResult データクラスの導入（ETL 実行結果の集約・変換メソッド to_dict を含む）。
    - 差分更新・最終日取得・バックフィルや品質チェックを想定したユーティリティを実装（_get_max_date 等）。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

- AI（kabusys.ai）
  - news_nlp:
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに書き込む。
    - タイムウィンドウ: JST 前日15:00 ～ 当日08:30（内部は UTC naive で計算）。
    - バッチ処理（最大 20 銘柄 / リクエスト）、記事数制限・文字数トリム（トークン肥大対策）。
    - リトライポリシー: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション（JSON抽出、results 配列、code/score の検証、数値チェック、±1.0 にクリップ）。
    - DB 書き込みは部分的失敗を避けるため対象コードのみ DELETE → INSERT（冪等性の確保）。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（_call_openai_api のモック化想定）。
  - regime_detector:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - マクロニュースは news_nlp.calc_news_window を利用して収集、OpenAI で JSON レスポンス（{"macro_sentiment":...}）を期待。
    - ルックアヘッドバイアス防止: queries は target_date 未満のみを参照、datetime.today() を直接参照しない設計。
    - API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ。
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック保護。
    - リトライ / エラー分類（RateLimitError、APIConnectionError、APITimeoutError、APIError の 5xx 判定）を考慮。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を考慮した実装。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を取得して PER/ROE を計算（最新レポートを銘柄ごとに取得）。
    - DuckDB を用いた SQL 実装で、prices_daily / raw_financials のみ参照。発注 API 等にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 複数ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を実装。有効レコードが 3 未満だと None を返す。
    - rank(values): 同順位は平均ランクとするランク付けユーティリティ（丸めで ties 検出漏れを防止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー関数。
  - zscore_normalize は kabusys.data.stats から再利用できるようにインポート/公開。

### Changed
- （初回リリースのため履歴上の変更はありません。初期機能セットを公開）

### Fixed
- （初回リリースのため修正履歴はありませんが、下記の堅牢化措置を含む実装が行われています）
  - .env パーサでクォート内のエスケープと行末コメント処理に対応し、誤パースを低減。
  - OpenAI API 呼び出しでのエラー耐性強化（リトライ・バックオフ・フェイルセーフ）。

### Deprecated
- なし

### Security
- 明示的なセキュリティ修正はなし。環境変数の扱いにおいて OS 環境変数の保護や自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止:
  - AI 関連および研究系の関数は datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を渡す設計。
  - DB クエリは target_date 未満（排他）や適切なウィンドウ指定で将来データを参照しないようにしている。
- 冪等性と部分失敗保護:
  - DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 相当）で実装し、部分失敗で既存データを不必要に消さない。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数（_call_openai_api）をモック差し替え可能に実装。API キーは引数注入も可能。
- ロギング:
  - 重要な分岐やエラー時に詳細なログを出力するように設計（warning/info/debug レベルを適宜使用）。

---

今後の予定（例）
- ai モジュールの追加評価指標・モデル拡張。
- ETL の品質チェックルール群の充実とモニタリング連携。
- 研究用ユーティリティの高速化・大規模データ対応。

（必要であれば、機能追加・修正の想定スケジュールや詳細アーキテクチャ注記を追記できます。）