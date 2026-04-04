# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
各リリースには互換性レベル（Added / Changed / Fixed / Removed / Security）を付しています。

現在のバージョン: 0.1.0 — 2026-04-04

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-04

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュール群を __all__ で定義（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を自動読み込みする機能を実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索するため、CWD に依存せずにパッケージ配布後も動作。
  - .env の読み込み順序・優先度:
    - OS 環境変数 > .env.local > .env
    - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサ: export プレフィックス対応、シングル／ダブルクォート内のエスケープ処理、インラインコメント扱いのルールをサポート。
  - 環境変数取得ユーティリティ Settings クラスを追加。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID / KILL フラグ関連パスとクリア挙動
    - CPU / Memory / Disk 閾値（パーセンテージ）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev のヘルパー

- AI：ニュースNLP & レジーム判定（src/kabusys/ai）
  - ニュースセンチメント集約（news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストを作成。
    - タイムウィンドウ: target_date に対して前日 15:00 JST 〜 当日 08:30 JST を対象（UTC に変換して DB クエリに使用）。calc_news_window() を提供。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ評価（最大 20 銘柄 / チャンク）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスの厳密なバリデーション（results 配列、code と score、スコアの数値性、未知コードの無視、スコア±1 でクリップ）。
    - DuckDB への書き込みは部分更新ロジック（DELETE → INSERT）で、部分失敗時に既存の他銘柄スコアを保護。
    - 公開関数: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。
    - テスト容易性のため _call_openai_api を patch できる設計。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull / neutral / bear）。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウからタイトルを抽出して評価。
    - OpenAI 呼び出しは独自のラッパを使用し、失敗時には macro_sentiment=0.0 としてフェイルセーフ継続。
    - レジームスコアはクリップされ、閾値でラベル付け。
    - market_regime テーブルへ冪等的（BEGIN / DELETE / INSERT / COMMIT）に書き込み。
    - 公開関数: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを優先するが、未登録日は曜日ベース（平日のみ）でフォールバック。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得して保存（バックフィル、健全性チェックを実装）。
    - 最大探索日数の上限を設定し無限ループを防止。

  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分取得・保存・品質チェックなどの設計方針をドキュメント化。
    - data.etl で ETLResult を再エクスポート。

- リサーチモジュール（src/kabusys/research）
  - factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足は None）。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER / ROE を計算。
    - すべて DuckDB の SQL を活用して実装。結果は (date, code) をキーとする dict のリストで返す。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算（horizons の入力検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman（ランク）相関を実装（同順位は平均ランク）。
    - rank(values)、factor_summary(records, columns) を提供。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する実装。

### Changed
- （初回リリースのため、他バージョンからの変更履歴はありません）

### Fixed
- （初回リリースのため、修正履歴はありません）

### Removed
- （初回リリースのため、削除点はありません）

### Security
- OpenAI API キーの取り扱いに関する注意: api_key を引数で注入可能にし、環境変数 OPENAI_API_KEY が未設定の場合は ValueError を返すことで意図しない API 呼び出しを防止。

---

## 既知の制約 / 注意点
- DuckDB 0.10 の executemany が空リストを許容しないため、空パラメータを弾いてから executemany を呼んでいる箇所がある（score_news など）。
- OpenAI とのやり取りは外部ネットワークに依存するため API 制限や課金が発生する点に注意。Retry/backoff は実装しているが、完全な耐障害性は保証しない。
- 一部モジュール（例: monitoring, strategy, execution）の実体は今回のスナップショットに含まれていない（__all__ に名前は存在）。利用時はそれらの実装があることを確認してください。
- 設定の自動ロードはプロジェクトルート検出に依存するため、パッケージ化後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に環境を管理することを推奨します。
- 日付処理は説明どおり「ルックアヘッドバイアス防止」を意識し、target_date 引数基準で計算する実装になっている（内部で datetime.today() / date.today() を参照しない設計が多いが、calendar_update_job は内部で date.today() を使用する）。

---

もし CHANGELOG に追加したいポイント（例えば公開されていないモジュールの補足やリリース日付の変更、公開済み API の注記）があればお知らせください。必要に応じて Unreleased セクションも追加します。