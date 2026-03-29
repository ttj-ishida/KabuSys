# Changelog

すべての重要な変更履歴をここに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

- リリース日付は ISO 形式（YYYY-MM-DD）を使用します。
- このファイルはコードベースから推測して作成した初期の変更ログです。

## [Unreleased]

## [0.1.0] - 2026-03-29

Added
- パッケージ初回公開。パッケージ名: kabusys、バージョン: 0.1.0
  - src/kabusys/__init__.py により public サブパッケージ（data, research, ai, 等）をエクスポート。

- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルや OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml で判定）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export KEY=val 形式、シングル/ダブルクォート対応、エスケープ対応、インラインコメント処理）。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
    - 必須環境変数検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - オプション/デフォルト値: KABUSYS_ENV（development/paper_trading/live の検証あり、デフォルト development）、LOG_LEVEL 検証、KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH
    - is_live / is_paper / is_dev ヘルパーを提供

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄別に記事を結合し、OpenAI（gpt-4o-mini、JSON Mode）へ送信してセンチメント（-1.0〜1.0）を取得。
  - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄当たりの最大記事数と文字数制限でトークン肥大化を抑制。
  - API 呼び出しに対するエクスポネンシャルバックオフとリトライ（429・ネットワーク断・タイムアウト・5xx 対象）。その他エラーはスキップして継続（フェイルセーフ）。
  - レスポンスの厳密なバリデーション（JSON 抽出、results 配列・code・score 検証、スコアは ±1.0 にクリップ）。
  - 書き込みは ai_scores テーブルへ冪等的に（対象コードのみ DELETE → INSERT）実行し、部分失敗時に既存データを保護。
  - テスト容易性のため _call_openai_api を patch 可能（unittest.mock.patch を想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルに書き込み。
  - マクロニュースは raw_news からマクロ関連キーワードでフィルタ（最大 20 件）して LLM に渡す。
  - OpenAI API 呼び出しは JSON mode で結果をパース、失敗時は macro_sentiment=0.0 にフォールバック。
  - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。DB エラー時は ROLLBACK を試行して上位へ例外を伝播。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを導入（target_date, fetched/saved カウント、quality_issues, errors 等を保持）。
    - 差分取得・バックフィル設計（デフォルト backfill_days 等）や品質チェックを想定した設計。
    - DuckDB を用いた最大日付取得やテーブル存在チェック等のユーティリティを実装。
  - etl モジュールで ETLResult を再エクスポート（kabusys.data.etl）。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの取得・保存用の夜間バッチ calendar_update_job（J-Quants クライアント経由）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を実装。
    - market_calendar が未取得の場合は曜日ベース（土日休場）でフォールバックする一貫した挙動。
    - 最大探索日数制限、バックフィル、健全性チェック（未来日付の過大値検出）などの安全設計。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。部分窓処理・NULL 伝搬を考慮。
    - calc_value: raw_financials と当日の株価を結合して PER / ROE を算出（EPS が 0/欠損時は None）。
    - すべて DuckDB 接続を受け取り SQL で計算。外部 API にアクセスせず安全。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）に対する将来リターンを計算。ホライズン検証あり。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク）相関（IC）を計算。有効レコード 3 件未満は None。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ（丸めで ties 検出漏れを防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 実装は標準ライブラリと DuckDB のみで外部依存を抑制。

Security
- 外部 API（OpenAI / J-Quants）用キーは環境変数（OPENAI_API_KEY 等）から取得。未設定時は明示的な例外を返すことで誤使用を防止。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / 実装上の重要ポイント（ドキュメント的補足）
- ルックアヘッドバイアス回避: 日付計算や DB クエリは target_date 未満/以前などの排他条件や外部の現在時刻参照を避ける設計。
- トランザクション設計: ai_scores / market_regime への書き込みは DELETE→INSERT をトランザクションで行い、部分失敗時に既存データを保護する実装。
- テスト性: OpenAI 呼び出し箇所は内部ラッパー関数を用意し patch できるようにしている（テストで API 呼び出しをモック可能）。
- DuckDB 互換性: executemany に空リストを渡せない点やリストバインドの不安定さを考慮した実装（個別 DELETE を多用）。

Breaking Changes
- なし（初期リリース）

References
- 必要な環境変数（主なもの）
  - OPENAI_API_KEY: OpenAI 用（news_nlp / regime_detector）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用
  - KABU_API_PASSWORD, KABU_API_BASE_URL: kabu ステーション API 用
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
  - DUCKDB_PATH, SQLITE_PATH: データベースファイルパス（デフォルト値あり）

--- 

今後のリリースでは、テストカバレッジ、エラーハンドリングの細分化、メトリクス/監視用のエンドポイント追加、より詳細な ETL の状態管理などを予定すると良いでしょう。