# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトは Semantic Versioning に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買支援およびリサーチ/データ基盤のコア機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装。バージョンは 0.1.0 に設定。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能。
  - .env パーサを実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理のルールを実装）。
  - Settings クラスを追加し、以下の設定をプロパティ経由で安全に取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev
  - 必須環境変数未設定時は ValueError を投げる挙動を定義。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事のセンチメント解析と ai_scores テーブルへの書き込み機能を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime を使用）。
    - raw_news と news_symbols を統合して銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
    - OpenAI（gpt-4o-mini）へバッチ送信（JSON Mode を利用）。1回に最大 20 銘柄のチャンク処理。
    - API エラー（429 / ネットワーク / タイムアウト / 5xx）に対して指数バックオフでリトライ。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。部分成功時は該当銘柄のみ置換するトランザクション（DELETE → INSERT）。
    - DuckDB 互換性考慮: executemany に空リストを渡さないチェックを実装。
    - テスト容易性: _call_openai_api をモック差し替え可能に設計。
  - regime_detector: 市場レジーム判定（bull/neutral/bear）機能を実装。
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次判定。
    - マクロキーワードで raw_news をフィルタして LLM に渡す。記事がない場合や API 失敗時は macro_sentiment=0.0 をフェイルセーフとして使用。
    - OpenAI 呼び出しも JSON Mode を利用し、リトライ・エラー処理を実装。
    - 結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性: news_nlp の内部関数とは独立した _call_openai_api 実装（モジュール結合を避ける設計）。

- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日ロジックを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバックする一貫した設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェック実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開（etl モジュールから再エクスポート）。
    - ETL パイプライン基盤（差分更新、idempotent 保存、品質チェックのフレームワーク）を実装。
    - backfill_days、_MIN_DATA_DATE、カレンダープレビュー等の定数を定義。
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティ等を実装。
    - 品質チェック結果を収集して ETLResult に保持する仕組みを設計。

- Research モジュール（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB ベースで計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - 全て prices_daily / raw_financials を参照し、外部 API へアクセスしない安全な設計。
    - 欠損データやデータ不足時の扱い（None）を明確化。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（calc_ic：Spearman ランク相関）、factor_summary（統計サマリー）、rank（同順位は平均ランク）を実装。
    - 外部依存ライブラリに頼らず標準ライブラリのみで実装。
    - rank は浮動小数丸め (round(v,12)) を行い ties 判定の安定性を向上。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で注入可能（api_key 引数）か、環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げて誤った実行を防止。
- .env 自動読み込みは OS 環境変数を保護する設計（読み込み時に既存環境変数集合を protected として扱う）。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、各種スコア/判定処理は datetime.today() / date.today() を内部参照しない（外部から target_date を注入する設計）。
- OpenAI 呼び出しは JSON Mode を利用して厳密な構造を期待し、レスポンスパース失敗時はフェイルセーフとしてスコア 0.0 または該当銘柄スキップの挙動とする。
- DuckDB のバージョン互換性（executemany に空リストを渡せない等）を考慮した実装。
- research モジュールは本番取引 API へは接続しない（安全・再現性担保）。

---

今後の改善候補（未実装・検討項目）
- ai_scores / market_regime 書き込み時のバージョン管理（監査ログ）の導入。
- news_nlp のマルチモデル対応やスコアのキャリブレーション/正規化機構。
- ETL の並列化や性能監視、詳細な品質チェックルールの追加。
- strategy / execution 周り（公開 API の実装・テスト）の充実。