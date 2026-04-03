# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Deprecated / Removed / Security）に分類しています。
- バージョン [0.1.0] はパッケージの初期公開相当の内容を表します。

## Unreleased
（現時点の開発中の変更はここに記載します。現リリースには該当なし）

## [0.1.0] - 2026-04-03

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - パブリックサブパッケージとして data, strategy, execution, monitoring を公開。

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env 行パーサを実装し、クォート、エスケープ、export KEY=val 形式、インラインコメントの扱いなどに対応。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数取得用ヘルパ `_require` と Settings クラスを提供し、J-Quants / kabu / LINE / DB / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティで取得。
  - 設定値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と boolean/Path/float の変換を実装。

- AI モジュール
  - ニュースNLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON Mode でバッチスコアリングし、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する util `calc_news_window` を実装。
    - バッチ処理: 1回の API コールで最大 20 銘柄（_BATCH_SIZE）、1銘柄あたり最大 10 記事・3000 文字までトリム。
    - API 呼び出し時の再試行（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）とレスポンスの厳密な検証（JSON 抽出、results 配列、code と score の型チェック）。
    - スコアは ±1.0 にクリップ。ai_scores テーブルへの置換は部分失敗を避けるため対象コードのみ DELETE→INSERT を実行（DuckDB executemany の空リスト制約に対応）。
    - 公開関数: `score_news(conn, target_date, api_key=None)`。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは `news_nlp.calc_news_window` と raw_news からマクロキーワードで抽出（最大 20 件）。
    - OpenAI（gpt-4o-mini）へ JSON Mode で投げ、レスポンスをパースして macro_sentiment を取得。API 失敗時はフェイルセーフで 0.0 を使用。
    - レジームスコア合成、ラベル化、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。公開関数: `score_regime(conn, target_date, api_key=None)`。

- データ基盤モジュール
  - ETL パイプライン (`kabusys.data.pipeline`)
    - ETL 実行結果を表す dataclass `ETLResult` を追加（取得数・保存数・品質チェック・エラー一覧などを保持）。
    - 差分取得／バックフィル／品質チェックの設計を想定したユーティリティが整備済み（J-Quants クライアント経由での取得を想定）。
  - ETL の公開インターフェース (`kabusys.data.etl`) で `ETLResult` を再エクスポート。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar テーブルの管理、JPX カレンダーの差分取得ジョブ（calendar_update_job）、営業日判定・next/prev/get_trading_days/is_sq_day などを提供。
    - DB にデータが無い場合は曜日ベースのフォールバック（週末非取引）を使用。最大探索日数による安全措置を実装。
    - calendar_update_job はバックフィル機能（直近 N 日を再取得）と健全性チェックを実装。

- Research モジュール (`kabusys.research`)
  - factor_research: ファクター計算関数を追加
    - `calc_momentum(conn, target_date)`：1M/3M/6M リターン、ma200 乖離を算出。
    - `calc_volatility(conn, target_date)`：20日 ATR、ATR 比率、平均売買代金、出来高比などを算出。
    - `calc_value(conn, target_date)`：raw_financials と組み合わせて PER / ROE を算出。
  - feature_exploration: 将来リターン / IC / 統計サマリーなど
    - `calc_forward_returns(conn, target_date, horizons=None)`、`calc_ic(...)`、`rank(...)`、`factor_summary(...)` を提供。
  - `kabusys.research.__init__` で zscore_normalize を含む主要関数をエクスポート。

- その他ユーティリティ
  - DuckDB を用いる想定での各種 SQL 実装と互換性考慮（例: executemany の空リスト回避、ROW_NUMBER の使用など）。
  - OpenAI クライアント呼び出しを個別モジュール内でラップし、テスト時に容易に差し替えられるよう設計（ユニットテストで _call_openai_api を patch 可能）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
- 実装段階での堅牢性改善点:
  - OpenAI API の 5xx / タイムアウト / レート制限等に対するリトライとログ出力を整備。
  - DuckDB の挙動に依存する箇所（executemany の空リスト不可など）に対応するコードを導入。
  - JSON レスポンスの前後余計テキストが混入するケースに対する復元ロジックを追加。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取得は引数優先、引数未指定時は環境変数 OPENAI_API_KEY を参照。キーの取り扱いは利用者の責任（コード中にハードコードなし）。
- 環境変数の自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能（テストや CI 向け）。

### Notes / Requirements / Migration
- 必須環境変数（機能を使用するために必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants API を利用するために必要（Settings.jquants_refresh_token）。
  - KABU_API_PASSWORD: kabu ステーション API 利用時に必要。
  - OPENAI_API_KEY: news_nlp / regime_detector の実行に必須（score_news / score_regime は未指定だと ValueError を送出）。
- 想定される DB スキーマ（本実装は下記テーブルを参照・更新します。実行前にスキーマ整備が必要）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等。
- DuckDB バージョン依存の注意点: executemany に空リストを渡せないバージョンなどに配慮した実装がされています。
- LLM 呼び出しは gpt-4o-mini を想定（モデル名は定数で管理）。JSON Mode を利用して厳密な構造を要請。
- 全ての時刻計算はルックアヘッドバイアスを避けるため datetime.today() / date.today() を内部処理で直接参照しない方針（関数に target_date を明示的に渡す設計）。

### Breaking Changes
- （初回リリースのため該当なし）

---

以上がコード内容から推測した CHANGELOG.md の初期リリース向けの内容です。必要であれば、実際のコミット履歴やリリース日（バージョン管理から取得）に合わせて日付や細部を調整します。