# Changelog

すべての重要な変更はこのファイルに記録します。これは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。主要サブパッケージとして data, research, ai, monitoring, execution, strategy 等を公開（__all__ 定義）。
  - バージョン情報: __version__ = "0.1.0"。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（読み込み優先順位: OS環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い（クォート有無での差分処理）などの堅牢なパーシング実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化。
  - Settings クラス: アプリケーション設定をプロパティとして公開（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定等）。必須変数は _require() で検証し未設定時は ValueError を送出。
  - env/log_level の検証: 有効な値集合を定義し、不正な値は明示的にエラー化。

- ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）でセンチメント評価を行うスコアリング機能を実装。
  - タイムウィンドウ計算: JST ベースの前日15:00〜当日08:30 を UTC に変換して対象記事を選定する calc_news_window を提供。
  - バッチ処理: 最大 20 銘柄単位でバッチ送信（_BATCH_SIZE）、1 銘柄あたり記事数/文字数上限によるトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（リトライ回数・待機時間設定）。
  - レスポンス検証: JSON パース、results キー/型/コード整合性/数値判定を行い、不正応答はスキップ。スコアは ±1.0 にクリップ。
  - DB 書き込み: スコア取得済みコードのみを DELETE → INSERT により置換するトランザクション（部分失敗時に他コードの既存データを保護）。
  - フェイルセーフ: API エラーやパース失敗は例外を投げずログ出力してスキップ（全体処理継続）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動）200日移動平均乖離とマクロニュースセンチメントを合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - MA200 乖離はターゲット日未満データのみを使用しルックアヘッドを防止。データ不足時は中立値(1.0)を採用して継続。
  - マクロニュースは news_nlp.calc_news_window を用いて抽出。マクロキーワード一覧および最大件数制限を実装。
  - OpenAI 呼び出しは gpt-4o-mini（JSON モード）を利用。API の一時エラーへのリトライや 5xx 判定を考慮した堅牢な実装。
  - レジームスコア合成は重み付け（MA70% / マクロ30%）で行い、結果は市場レジームテーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - API 未設定時には明示的な ValueError を送出。

- データ基盤ユーティリティ (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を基に営業日判定/前後営業日取得/期間内営業日列挙/is_sq_day 判定等のAPIを実装。
    - DB にカレンダーが存在しない場合は曜日ベース（土日非営業）でフォールバックする設計。
    - next_trading_day / prev_trading_day は DB 上の登録値を優先し、未登録日は曜日フォールバックで一貫した挙動を提供。最大探索範囲で無限ループ防止。
    - 夜間バッチ更新 calendar_update_job: J-Quants API から差分取得し market_calendar を冗長防止（バックフィル / 健全性チェック含む）で保存。jq.fetch_market_calendar / jq.save_market_calendar を利用。
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを導入し、ETL の取得数/保存数/品質問題/エラー一覧を構造化して返却・監査可能に。
    - 差分更新・バックフィル・品質チェック（quality モジュールを利用）等の方針を実装（詳細は pipeline 内で実装）。
  - etl モジュールで ETLResult を再エクスポート。

- 研究用ユーティリティ (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS 欠損や 0 時は None）。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装。外部 API への依存なし。
  - feature_exploration: 将来リターン/IC/統計サマリ等を提供
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。ホライズンは 1..252 の整数で検証。
    - calc_ic: factor と将来リターンのスピアマンランク相関を計算。有効レコードが 3 未満の場合は None を返す。
    - rank: 同値の平均ランク処理（丸めによる ties 検出対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

### Changed
- 新規初版のため該当なし。

### Fixed
- 新規初版のため該当なし。

### Security
- OpenAI API キーや各種機密情報は Settings 経由で環境変数から取得する設計。キー未設定時は例外を投げることで安全に失敗する挙動を採用。
- .env 自動ロードは明示的に無効化できる（KABUSYS_DISABLE_AUTO_ENV_LOAD）ため、テストや CI 環境で誤読されるリスクを軽減。

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策: いずれのモジュール（news_nlp, regime_detector, research）も datetime.today()/date.today() を直接参照せず、外部から渡された target_date に基づく評価を行うよう設計されています。
- フェイルセーフ志向: 外部 API の失敗は基本的にスキップまたはデフォルト値（例: macro_sentiment=0.0, スコア未取得はスキップ）で処理を継続する方針です。
- テスト容易性: OpenAI 呼び出しラッパー（_call_openai_api）を内部で分離しており、ユニットテスト時にモック差し替えが可能です。
- DuckDB に依存した実装: 多くの処理は DuckDB に対する SQL クエリと Python 側の整形で実現されています。

---

今後の予定（例）
- 0.2.0: 実運用向けの execution / monitoring モジュール強化、より詳細な品質チェック、ETL のスケジューリング連携等。
- ドキュメント追加: API 使用例・SETUP (環境変数・.env.example) の整備。

（注: 本 CHANGELOG は提示されたコードベースからの機能・設計情報を基に作成しています。）