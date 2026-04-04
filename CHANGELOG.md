# Changelog

すべての重要な変更はこのファイルに記載します。本ファイルは「Keep a Changelog」仕様に準拠します。  
タグ付けは semver に従います。

## [Unreleased]

---

## [0.1.0] - 2026-04-04

初回公開リリース。本リリースでは日本株自動売買プラットフォームの基礎機能群（データ取得/前処理、研究用ファクター計算、AI を用いたニュース解析・市場レジーム判定、環境設定ユーティリティなど）を提供します。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（バージョン 0.1.0、公開 API: data, strategy, execution, monitoring を想定）。
- 環境設定 / 設定管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env の柔軟なパーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応）。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等の設定をプロパティ経由で取得。未設定の必須値は ValueError を送出。
  - ログレベル・環境値のバリデーション実装（LOG_LEVEL, KABUSYS_ENV の検証）。
- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理機能を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar がない場合は曜日ベースのフォールバック（週末除外）を使用。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / ETLResult（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを公開。ETL 実行結果・品質チェック結果・エラー一覧を保持。to_dict により品質問題を辞書化可能。
    - ETL パイプラインの設計方針とユーティリティの骨組みを実装。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを gpt-4o-mini（OpenAI Chat JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ保存。
    - チャンク処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたりの記事上限 / 文字上限によるトリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフを実装。API 例外はフェイルセーフでスキップし、処理継続。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - タイムウィンドウ計算（JST ベース：前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で提供。
  - regime_detector.score_regime
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタリングして LLM 評価を行う処理を実装。API 失敗時は macro_sentiment=0.0（中立）で継続するフェイルセーフを実装。
    - Look-ahead バイアス回避のため date 条件は target_date 未満のデータのみ使用。datetime.today()/date.today() を直接参照しない設計。
    - OpenAI SDK の APIError で status_code の有無に柔軟に対応する実装やリトライロジックを備える。
- リサーチ / ファクター（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
    - Value: raw_financials からの EPS/ROE を用いた PER, ROE 計算（EPS が 0/欠損の場合は None）。
    - DuckDB 上で SQL とウィンドウ関数を利用して効率的に集計。
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装。
    - まとめてホライズンの将来リターンを取得する高速 SQL 実装。
    - Spearman ランク相関（IC）実装（tie の平均ランク処理含む）。有効レコードが 3 未満の場合は None。
    - 統計サマリー（count/mean/std/min/max/median）。
  - research パッケージで data.stats.zscore_normalize を再エクスポート。
- DuckDB 互換性 & 安全性
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実装。失敗時は ROLLBACK を試み、失敗時に警告ログを出力。
  - DuckDB 0.10 の制約（executemany に空リストを渡せない）に対する防御ロジックを実装。
  - DB から返る日付値の安全な変換ユーティリティを実装（_to_date）。
- テスト性・運用性
  - OpenAI 呼び出し部分はテスト時に差し替え可能（unittest.mock.patch 想定）。
  - api_key の注入可能（関数引数）でテストしやすい設計。
  - ログと警告を多用し、異常系の可観測性を高める実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Known limitations
- strategy / execution / monitoring パッケージは top-level __all__ に含まれていますが、このリリースに完全な実装が含まれていない可能性があります（将来的な拡張予定）。
- OpenAI の使用には環境変数 OPENAI_API_KEY（または各関数の api_key 引数）が必要です。未設定時は ValueError を送出します。
- 一部の設計は DuckDB のバージョンや OpenAI SDK の将来の変更（status_code の所在やレスポンス形式）に依存するため、将来の互換性チェックが必要です。
- JSON モードでも LLM が余計な前後テキストを返す可能性に備え、最外の {} を抽出してパースする復元ロジックを組み込んでいますが、想定外の出力はスキップされ得ます。

--- 

（今後のリリースでは bugfix / performance / security 等のセクションを分けて記載します。）