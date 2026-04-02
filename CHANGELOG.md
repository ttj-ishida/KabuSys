# Changelog

すべての変更は「Keep a Changelog」フォーマットに従い、セマンティックバージョニングを使用します。  
このファイルはコードベースから推測して作成しています（実装に基づく要約・設計上の注記を含みます）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-02

概要: 日本株自動売買プラットフォーム「KabuSys」の初期実装。環境設定管理、データETL／カレンダー管理、研究用ファクター算出、AIを用いたニュースセンチメント・市場レジーム判定など、コアなデータ取得・前処理・リサーチ機能を提供します。DuckDB を主要なローカルデータ格納先として想定した設計になっています。

### Added

- パッケージ初期化
  - src/kabusys/__init__.py にて version = 0.1.0、公開サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルや OS 環境変数から設定値を読み込む自動ローダーを実装。
    - 自動ロード順: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護（.env の上書きを防ぐ）。.env.local は上書き可。
    - 環境自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出は __file__ から親階層を探索し .git または pyproject.toml を基準に判定（配布後の動作に配慮）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの場合、'#' の直前が空白／タブのときのみコメントとして扱うなど細かい動作を定義。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants / kabuステーション / Slack / データベース / 監視 / システム設定のプロパティを定義。
    - 必須 env は _require() にて ValueError を発生させる（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
    - KABUSYS_ENV 値検証（development / paper_trading / live のみ許容）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - パス系は Path 型で返却（expanduser）。
    - 監視閾値（CPU/MEM/DISK）は float として取得。

- AI モジュール（kabusys.ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを算出して ai_scores テーブルへ書き込む処理を提供。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチ処理: 1回の API 呼び出しで最大 _BATCH_SIZE=20 銘柄。
    - 1銘柄あたりのトークン肥大化対策: 最大 _MAX_ARTICLES_PER_STOCK=10 記事、_MAX_CHARS_PER_STOCK=3000 文字にトリム。
    - リトライ戦略: 429（RateLimit）・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ（最大回数制御）。
    - レスポンス検証: JSON の抽出・パース、"results" リストの検証、未知コードの無視、スコア数値化と ±1.0 クリップ。
    - DB 書き込みは部分失敗に備え、スコア取得済みコードのみ DELETE → INSERT することで既存データ保護。
    - テスト容易性: OpenAI 呼び出し箇所（_call_openai_api）をモックで差し替え可能。
    - フェイルセーフ: API 未取得時は該当銘柄をスキップして処理継続。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを排除。
    - マクロニュースは news_nlp.calc_news_window 範囲で取得。記事が無ければ LLM を呼ばず macro_sentiment=0.0。
    - OpenAI 呼び出しについては独自実装（news_nlp とプライベート関数を共有しない）。
    - API の失敗やレスポンスパース失敗は macro_sentiment=0.0 にフォールバックし、警告ログを出す実装（例外は上げない）。
    - レジーム計算後は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE WHERE date=? / INSERT / COMMIT）。失敗時は ROLLBACK を試み、上位へ例外を伝播。

- データモジュール（kabusys.data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（祝日・半日取引・SQ日）管理ロジックを提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった日次判定ユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（平日を営業日）で一貫して動作。
    - next/prev/get_trading_days は DB 登録値を優先し未登録日は曜日フォールバックで補完する（DB がまばらでも一貫した結果）。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得し save_market_calendar で保存、バックフィルと健全性チェックあり）。
    - 最大探索範囲（_MAX_SEARCH_DAYS）により無限ループを防止。

  - pipeline / ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（ETL の取得件数、保存件数、品質問題、エラー概要などを保持）。
    - ETL の設計方針（差分更新、backfill、品質チェック非 Fail-Fast、id_token 注入可能）を明記。
    - _table_exists / _get_max_date 等のユーティリティを実装（DuckDB 前提）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究（research）モジュール（kabusys.research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m、200日 MA 乖離（ma200_dev）を計算（prices_daily を参照）。
    - Volatility / Liquidity: 20日 ATR（atr_20）, 相対 ATR (atr_pct), 20日平均売買代金（avg_turnover）, 出来高比（volume_ratio）を計算。
    - Value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 または欠損の場合は None）。prices_daily / raw_financials のみ参照。
    - 各関数は (date, code) をキーとする dict のリストを返す。データ不足は None を返す設計。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: target_date から各ホライズン（デフォルト [1,5,21]）先の終値を用いて将来リターンを算出。horizons の妥当性チェックあり（正の整数かつ <=252）。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman の ρ）を計算。有効レコードが 3 未満の場合は None を返す。
    - rank: 同順位の平均ランクを返す実装（丸め処理により ties の誤検出を低減）。
    - factor_summary: 各カラムについて count/mean/std/min/max/median を算出（None 値を除外）。

### Design / Safety / Testing Notes

- ルックアヘッドバイアス対策
  - AI・リサーチ・レジーム判定等の関数は内部で datetime.today()/date.today() を参照しない（呼び出し側から target_date を与える設計）。prices_daily クエリは target_date 未満／等の条件を適切に付与。

- DB 書き込みの冪等性と部分失敗耐性
  - market_regime, ai_scores などのテーブル更新は既存レコードの削除後挿入、または個別 DELETE → INSERT の形で既存データの保護を考慮。

- OpenAI 呼び出しの堅牢化
  - JSON Mode を利用し、レスポンスのパース失敗や API エラーに対してリトライやフォールバック（ゼロ値）を行う実装。
  - テスト容易性のため _call_openai_api をパッチ可能にしている。

- DuckDB の互換性配慮
  - executemany に空リストを渡さないチェック（DuckDB のバージョン差異への配慮）。
  - 日付型変換ユーティリティやテーブル存在チェックを用意。

### Known limitations / Not implemented yet

- strategy, execution, monitoring パッケージは __all__ に含まれるが、当該差分には詳細実装ファイルが含まれていない（将来追加想定）。
- 一部指標（PBR・配当利回りなど）は未実装（calc_value の注記）。
- OpenAI との統合は gpt-4o-mini を想定した実装だが、API/SDK 変更に対する互換性は一部コードで注意が必要（例: APIError.status_code の存在チェック等）。

---

（注）この CHANGELOG は現在のコード内容から自動的に要約したものであり、実際のコミット履歴やリリースノートとは差分がある可能性があります。必要であればリリース日や細かい変更点（コミット単位）を手動で調整してください。