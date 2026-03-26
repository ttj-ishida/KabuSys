# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-26
最初の公開リリース。日本株自動売買システムの基盤機能を実装しました。

### Added
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開（将来的なモジュール拡張を想定）。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 強化された .env パーサー:
    - export プレフィックス対応（export KEY=val）。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無しの行でのインラインコメント処理（'#' の前が空白/タブの場合のみコメントと判定）。
  - 設定ラッパー Settings を提供:
    - 必須環境変数取得メソッド（_require）で未設定時は ValueError を送出。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY などを想定）。
    - KABUSYS_ENV 値検証（development / paper_trading / live のみ許容）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - duckdb_path / sqlite_path のデフォルトと expanduser 対応。
    - is_live / is_paper / is_dev ユーティリティプロパティ。

- データプラットフォーム（kabusys.data モジュール群）
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar を利用した営業日判定ユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先、未登録日は曜日（土日）によるフォールバックを採用。
    - next/prev_trading_day の最大探索範囲を設定して無限ループ防止。
    - calendar_update_job: J-Quants（想定クライアント）から差分取得して market_calendar を冪等更新。
      - lookahead/backfill/健全性チェック（未来日が異常に遠い場合はスキップ）を実装。
  - ETL パイプライン (pipeline, etl, etl.ETLResult)
    - ETLResult データクラスで ETL 実行結果を集約（品質問題やエラーを集める）。
    - 差分フェッチ、バックフィル、品質チェックの設計方針を反映。
    - DuckDB との互換性を意識した実装（テーブル存在チェック、MAX 日付取得ユーティリティなど）。
    - etl モジュールで ETLResult を公開。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング (news_nlp)
    - raw_news + news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（デフォルト最大 20 銘柄/チャンク）、1 銘柄あたりの記事数と文字数上限を実装（記事数/文字数トリム）。
    - 再試行ポリシー（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。失敗時はそのチャンクをスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーションとスコア ±1.0 クリップ。
    - データベースへの書込みは部分置換（DELETE → INSERT）で冪等処理、DuckDB executemany の空リスト注意点に対応。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - ニュース収集ウィンドウ（JST 基準）を calc_news_window で計算（UTC naive datetime に変換して DB と比較）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を算出。
    - MA200 計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロ記事は raw_news からキーワードでフィルタ（最大 20 件）し、OpenAI を呼び出して JSON レスポンスから macro_sentiment を抽出。
    - API 呼び出し失敗やパース失敗は macro_sentiment = 0.0 でフォールバックし処理を継続（警告ログ）。
    - レジームスコアの閾値に基づき label を決定し market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行）。

- リサーチ / ファクター解析（kabusys.research）
  - factor_research:
    - モメンタム、ボラティリティ、バリュー等の定量ファクター計算関数を提供:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（データ不足時は None）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（データ不足時は None）
      - calc_value: per（EPS が 0/欠損のときは None）、roe（raw_financials から最近報告を参照）
    - DuckDB SQL を活用して高性能に集計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）までの将来リターンを一括取得。
    - calc_ic: ランク相関（Spearman ρ）をランク化して計算（有効レコード数 < 3 の場合は None）。
    - rank: 同順位は平均ランクを返す実装（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出（None 値除外）。
    - 外部依存（pandas 等）無しで標準ライブラリと DuckDB のみで実装。

- その他
  - DuckDB を前提とした SQL 実装と、各関数のルックアヘッドバイアス防止方針（datetime.today()/date.today() を内部ロジックで参照しない）を徹底。
  - 適切なログ出力と警告（data ソース欠損・API 失敗・ROLLBACK 失敗等）を実装し運用時の可観測性を確保。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Deprecated
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーや機密情報は Settings を通じて環境変数で管理する想定。自動 .env ロードはテスト等のためにオフに設定可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Known limitations
- news_nlp の出力で PBR や配当利回りは現時点で未実装（calc_value の Note に記載）。
- DuckDB の executemany は空リストを受け付けない実装上の注意点があり、空時は処理をスキップするガードを追加しています。
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を想定。API 仕様変更や別モデル使用の際は _call_openai_api の差し替えや設定変更が必要です。
- J-Quants / kabu ステーション等の外部クライアント実装（jquants_client, kabu API クライアント等）は本リリース内で参照／想定されているが、クライアント実装の詳細は別モジュールに委ねられます。

---

今後の予定:
- strategy / execution / monitoring の具現化（実際の発注・モニタリングロジックの実装）。
- 更なる品質チェックルール追加および ETL の堅牢化。
- テストカバレッジの拡充と CI での静的解析導入。

（この CHANGELOG はコードから推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴・リリースプロセスに基づいて整備してください。）