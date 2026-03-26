# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトの初期バージョンは 0.1.0 です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-26
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を提供します。

### Added
- パッケージのメタ情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env のパース機能を強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし値のインラインコメント認識（直前が空白/タブの場合）。
  - .env 上書きロジック: override フラグ、既存 OS 環境変数を保護する protected セット。
  - 必須設定を取得する _require 関数と Settings クラスを提供。
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - KABUSYS_ENV 値検証 (development/paper_trading/live) と LOG_LEVEL 検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)。
    - is_live, is_paper, is_dev の利便性プロパティ。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON モード）へバッチ送信してセンチメントを算出。
    - バッチ処理、1チャンクあたり最大銘柄数（デフォルト 20）、1銘柄あたり記事数上限・文字数トリム（デフォルト: 10 件 / 3000 文字）を実装。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他はスキップして継続。
    - レスポンス検証ロジック（JSON 抽出、results リスト、各要素の code/score 検証、スコアの数値化・有限値判定、±1.0 でクリップ）。
    - DuckDB 互換性を考慮した書き込み（部分書き込み保護のため取得済みコードのみ DELETE→INSERT）。
    - 公開関数: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。
    - タイムウィンドウ計算ユーティリティ: calc_news_window(target_date)。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で日次レジーム（bull/neutral/bear）を判定。
    - _calc_ma200_ratio、_fetch_macro_news（マクロキーワードフィルタ）、OpenAI 呼び出し（gpt-4o-mini、JSON モード）、リトライ・フォールバック処理を実装。
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 で継続。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M）、ma200 乖離、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）などの定量ファクター計算を実装。
    - DuckDB 上の prices_daily / raw_financials のみを参照し外部 API に依存しない設計。
    - データ不足時の None ハンドリング。
    - 公開関数: calc_momentum, calc_volatility, calc_value。

  - feature_exploration.py
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト horizons = [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンランク相関を実装。
    - ランク変換ユーティリティ rank(values) — 同順位は平均ランク。
    - 統計サマリー: factor_summary(records, columns) — count/mean/std/min/max/median を計算。
    - すべて標準ライブラリのみで実装（pandas 等に未依存）。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得・保存・品質チェックのフレームワークを実装。
    - ETLResult データクラスを定義（target_date, fetched/saved カウント、quality_issues, errors 等）。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを提供。
    - 公開: ETLResult を kabusys.data.etl で再エクスポート。

  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新（calendar_update_job）と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫した挙動。
    - calendar_update_job は J-Quants クライアント経由で差分取得し冪等保存、バックフィルや健全性チェックを実装。

- ロギング・設計ポリシー
  - ルックアヘッドバイアス回避のため、各処理で datetime.today()/date.today() を直接参照しない設計。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT / ON CONFLICT）で実施。
  - API 呼び出しは再試行・バックオフを行い、致命的エラーにならないようフォールバックする（失敗時はスキップして続行）。

### Changed
- （初版リリースのため変更履歴はありません）

### Fixed
- （初版リリースのため修正履歴はありません）

### Security
- （現時点で特記すべきセキュリティ通知はありません）

---

注:
- OpenAI クライアントは openai.OpenAI を使用（API キーは引数または環境変数 OPENAI_API_KEY）。API レスポンスのパース・検証・リトライ戦略を実装しているが、実行時には適切な API キーと通信環境が必要です。
- DuckDB を前提とした実装で、バージョン差異（executemany の空リスト禁止など）に配慮したコーディングを行っています。
- .env サンプルや .env.example を参照して必須環境変数を設定してください。