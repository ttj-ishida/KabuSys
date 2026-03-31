# CHANGELOG

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
次バージョンのリリース履歴はセマンティックバージョニングに従います。

- リンク: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点のコードスナップショットは初期公開相当の状態のため、未リリースの変更はありません）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。設計方針として
「ルックアヘッドバイアス回避」「DuckDBベースの分析/ETL」「OpenAI を用いたニュースNLP 」「冪等な DB 書き込み」「フェイルセーフな外部 API 呼び出し」を重視しています。

### Added
- パッケージ基盤
  - kabusys パッケージを提供。バージョンは 0.1.0。
  - モジュール公開: data, research, ai, execution, strategy, monitoring（__all__ によるエクスポート）を想定。

- 設定管理 (kabusys.config)
  - Settings クラスを実装し、環境変数ベースで設定を提供。
  - 必須設定の取得ヘルパー（_require）を追加し、未設定時は明示的な ValueError を送出。
  - .env 自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーは export 文やクォート、インラインコメント、エスケープに対応。
  - 設定項目:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
    - SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV 値検証 (development / paper_trading / live)
    - LOG_LEVEL 値検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - 環境フラグ用のユーティリティプロパティ: is_live, is_paper, is_dev

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini, JSON モード）に投げ、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する処理を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB と比較）。
  - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大 10 記事・3000 文字にトリム。
  - 再試行戦略: 429（レート制限）、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ（最大回数定義）。
  - レスポンス検証: JSON パース、"results" 配列、code/score の存在、既知コードフィルタ、数値変換・有限性チェックを実施。スコアは ±1.0 にクリップ。
  - DuckDB 互換性: executemany に空リストを渡さない対策を実装。
  - テスト容易性: _call_openai_api をパッチ差替え可能（unittest.mock.patch で置き換えを想定）。
  - OpenAI API キーは引数 (api_key) または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出し、market_regime テーブルへ冪等書き込み。
  - マクロニュースは news_nlp の calc_news_window を利用して抽出し、独自の OpenAI 呼び出し実装でセンチメントを取得。
  - LLM 呼び出し失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
  - 計算におけるルックアヘッドバイアス防止: date 比較や window の排他条件を遵守。
  - OpenAI 呼び出しに対しリトライ/バックオフ、5xx ハンドリング、レスポンスパース失敗時のフォールバックを実装。
  - 重要な内部関数: _calc_ma200_ratio, _fetch_macro_news, _score_macro, 等。

- 研究／ファクター群（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と当日の株価から PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - DuckDB SQL を活用した実装で高速に集約。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得。horizons のバリデーションあり。
    - calc_ic: Spearman（ランク相関）で IC を計算。必要レコード数が少ない場合は None を返す。
    - rank: 同順位の平均ランク処理、丸め処理で tie の誤検出を防止。
    - factor_summary: count/mean/std/min/max/median といった基本統計量を算出。
  - zscore_normalize は data.stats から再エクスポート。

- データ管理（kabusys.data）
  - calendar_management:
    - JPX カレンダー取得・管理のユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB に calendar データがない場合の曜日ベースのフォールバックを提供。
    - calendar_update_job: J-Quants API から差分取得 → 市場カレンダーを冪等に保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）。バックフィルと健全性チェック（将来日付の異常検出）を実装。
    - 最大探索日数 (_MAX_SEARCH_DAYS)、先読み日数、バックフィル日数等の安全パラメータを備える。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。ETL の実行結果、品質検査結果、エラー概要を格納。
    - ETL パイプライン基盤（差分取得、バックフィル、保存・品質チェックの設計方針）を記述。
    - DuckDB の日付最大値取得、テーブル存在判定等のユーティリティを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーおよび各種トークンは環境変数で外部に保存し、コード中に直書きしない運用を想定。
- .env 自動読み込み機能は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注意事項 / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の設定を確認してください。
  - OpenAI 呼び出しを行う機能（score_news, score_regime）は OPENAI_API_KEY が必要です（api_key 引数でも注入可）。
- DuckDB に対する互換性考慮として executemany に空リストを渡さない実装になっています（DuckDB 0.10 等を想定）。
- 外部 API（OpenAI / J-Quants）呼び出し部分は堅牢化（リトライ/バックオフ/フォールバック）されていますが、API レート制限／料金に注意してください。
- ルックアヘッドバイアス防止の方針により、日付取得は datetime.today()/date.today() を直接参照しない実装が各所で採られています（テスト時には明示的な target_date を渡してください）。

今後の予定（参考）
- 監視・実行モジュール（execution / monitoring / strategy）との統合、運用用 CLI /ジョブスケジューラ実装、テストカバレッジの拡充。