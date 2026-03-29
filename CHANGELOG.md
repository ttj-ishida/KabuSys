# Changelog

すべての変更は Keep a Changelog の形式に従い、慣用的にセマンティックバージョニングを使用します。

※このファイルはリポジトリ内の現在のコードベースから推測して作成した初期リリース向けの CHANGELOG です。実際のコミット履歴に基づくものではありません。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### Added
- パッケージ全体
  - kabusys パッケージを追加。エントリポイントのバージョンは `0.1.0`。
  - モジュール構成: data, research, ai, monitoring, strategy, execution（__all__ で公開済みのサブパッケージを含む）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local からの自動読み込み機能を実装。プロジェクトルートを `.git` または `pyproject.toml` から探索するため、CWD に依存しない動作。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサー実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内部のバックスラッシュエスケープ対応。
    - インラインコメント（未クォート時は直前に空白がある `#` をコメントとして扱う）を考慮。
  - 上書き制御:
    - `.env` は OS 環境変数を上書きせず（override=False）、`.env.local` は上書き（override=True）する。ただし OS の既存キーは保護（protected）。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティ（必須キーは未設定時に ValueError を送出）。
    - KABUSYS_ENV の検証（development / paper_trading / live のいずれか）と LOG_LEVEL 検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
    - デフォルト値: KABUSYS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など。

- AI モジュール (kabusys.ai)
  - news_nlp
    - ニュースの NLP スコアリング機能を追加。
    - target_date に対するニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供する `calc_news_window`。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ（最大 20 銘柄/チャンク）で投げて JSON レスポンスを取得、検証後 ai_scores テーブルへ差し替え書き込み（DELETE→INSERT）。
    - 1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出し部はテストのため差し替え可能（_call_openai_api を patch 可能）。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライし、リトライ上限到達時は部分スキップ（フェイルセーフ）。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、code/score の型チェック、score の ±1.0 クリップ）。
    - DuckDB の executemany 空リスト制約への対応（空時は skip）。

  - regime_detector
    - 市場レジーム判定機能を追加。
    - ETF 1321（日経225連動型）の直近 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
    - MA200 計算は target_date 未満のみを使用してルックアヘッドを防止。
    - マクロニュースは news_nlp のウィンドウ関数を利用して取得。マクロキーワードでフィルタ（最大 20 件）。
    - OpenAI 呼び出しは JSON モードで行い、レスポンスパース失敗や API エラー時は macro_sentiment=0.0 にフォールバックして処理継続（フェイルセーフ）。
    - レジーム値を market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。

- 研究用モジュール (kabusys.research)
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を正しく扱う実装。
    - calc_value: raw_financials から最新財務（target_date 以前）を取得して PER / ROE を計算。EPS=0/欠損は None。
    - DuckDB のウィンドウ関数を積極利用して効率的に集計。
  - feature_exploration
    - calc_forward_returns: マルチホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の妥当性チェックあり（1..252）。
    - calc_ic: Spearman（ランク相関）による IC を計算。データ不足（<3 ペア）の場合は None。
    - rank: 同順位は平均ランクを返す実装（丸め誤差対策で round(v, 12) を使用）。
    - factor_summary: 指定カラムごとの count/mean/std/min/max/median を返す。

- データ基盤モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）用ロジックを追加。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB に登録がない日や NULL 値は曜日ベース（平日を営業日とする）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル、健全性チェックあり）。
    - 最大探索日数やバックフィル日数、サニティチェックなどの安全策を実装。

  - pipeline / etl
    - ETLResult データクラスを実装（ETL 実行結果、品質検査結果・エラーの集約、to_dict メソッド）。
    - 差分更新・バックフィル・品質チェックの方針を実装（jquants_client 経由で保存し idempotent に扱う）。
    - 内部ユーティリティ: テーブル存在確認、テーブルの最大日付取得などを提供。
    - kabusys.data.etl モジュールで ETLResult を再エクスポート。

### Changed
- 設計/実装方針の明文化（コード内 docstring に多数記載）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接使用しない方針が一貫して適用。
  - OpenAI 呼び出しは JSON Mode を用い、レスポンスの堅牢な検証と部分失敗時のフェイルセーフ戦略を採用。
  - DuckDB 互換性のため executemany に関する注意点（空リスト扱い）を反映。

### Fixed
- （該当無し／初回リリースのためバグ修正履歴なし。ただし実装内で予防的なログ・例外処理（API 失敗時のフォールバック、ROLLBACK の試行等）を追加して堅牢性を向上。）

### Security
- OpenAI API キーや各種トークンは Settings を通じて環境変数から取得。必須未設定時は明確な ValueError を送出して誤設定を防止。
- .env ロード時に OS 環境変数を保護する仕組みを実装（.env が既存 OS 環境変数を不用意に上書きしない）。

### Notes / Implementation details
- OpenAI 連携は gpt-4o-mini を指定。API 呼び出しのタイムアウト・リトライ・レスポンス検証を実装してあるが、実際の運用ではレート・コスト最適化やモデル変更に対する運用ルールの整備を推奨。
- DuckDB を主要なストレージとして使用する想定。SQL は DuckDB のウィンドウ関数を使う実装で最適化を図っている。
- テスト容易性のため、OpenAI 呼び出し部分は patch してモックできるように設計されている（ユニットテストでの注入ポイントあり）。
- 一部ファイル（pipeline の末尾など）で実装が続く想定の箇所があるため、将来的に追加の ETL 調整・機能拡張が想定される。

---

参考: 各モジュールの詳細な仕様・設計方針は該当ソースファイル内の docstring に記載されています。リリース後のバグ修正・機能追加はこの CHANGELOG に追記してください。