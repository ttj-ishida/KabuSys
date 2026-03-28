# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。バージョン番号は package の __version__（src/kabusys/__init__.py）に合わせています。

現在の日付: 2026-03-28

なお、表記方針:
- 日付はリリース日（YYYY-MM-DD）を使用します。
- 各エントリには「Added / Changed / Fixed / Deprecated / Removed / Security」を可能な限り明確に分けて記載します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。以下の主要機能とモジュールを実装しています。

### Added
- パッケージ基礎
  - 初期バージョン 0.1.0 を追加。パッケージ名: kabusys（src/kabusys/__init__.py）。
  - 公開モジュール群: data, research, ai, monitoring, strategy, execution（__all__ にて定義）。

- 設定管理
  - 環境変数/設定読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルート判定は .git または pyproject.toml を基準にし、__file__ を起点に親ディレクトリを探索するため CWD に依存しない。
    - .env, .env.local の自動ロードを実装。OS 環境変数を保護する protected 機構を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env のパースルールを細かく実装（export プレフィックス、クォート内エスケープ、インラインコメント取り扱いなど）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルを取得するプロパティを公開。
    - 不正な値や必須環境変数未設定時は ValueError を送出。

- データプラットフォーム（Data）
  - ETL パイプラインと結果オブジェクト（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを実装（取得数・保存数・品質チェック・エラー集約等）。
    - 差分更新、バックフィル、品質チェックを想定した設計。
  - ETL 公開インターフェース（src/kabusys/data/etl.py）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等を提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバックする堅牢な実装。
    - calendar_update_job により J-Quants からの差分取得・冪等保存（バックフィルと健全性チェックを含む）を実行可能。
  - DuckDB を利用する前提のユーティリティ関数を実装（テーブル存在チェック、日付変換等）。

- リサーチ（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算する calc_momentum を追加。データ不足時は None を返す設計。
    - Volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算する calc_volatility を追加。true_range の NULL 伝播を考慮した実装。
    - Value: PER, ROE を raw_financials と prices_daily から計算する calc_value を追加（最新財務レコードの取得ロジック含む）。
    - DuckDB のウィンドウ関数を活用し、結果を (date, code) 単位の dict リストで返す設計。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns（任意ホライズンの fwd_Xd を一度のクエリで取得）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ に相当するランク相関を実装、欠損・同値対応）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - ランキング関数: rank（同順位は平均ランク扱い、丸めによる ties 対策あり）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI（自然言語処理 / LLM）
  - ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC 変換ロジック含む）。
    - バッチサイズ、記事・文字数上限、JSON mode を利用した出力検証、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンス検証ロジック（JSON パース、results 配列、code/score 検証、数値の有限性検査）、スコアの ±1 クリップ、部分成功時の DB 保護（対象コードのみ DELETE → INSERT）を実装。
    - テスト容易性のため _call_openai_api を patch 可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - LLM 呼び出しは gpt-4o-mini、JSON mode、冪等の DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ、リトライ・バックオフの実装。
    - lookahead ライアビリティ回避のため date を引数で受け取り、DB クエリは target_date 未満のデータのみを参照する設計。
    - news_nlp と内部的に結合しないよう関数分離（モジュール結合の抑制）。

- その他
  - ai/__init__.py と research/__init__.py で主要関数を公開エクスポート。
  - データ層で jquants_client を利用する設計（jquants_client 自体は参照されるが今回の差分に含まれていない）。

### Changed
- 設計ルール（全体）
  - すべての日時ロジックは内部で datetime.today()/date.today() への直接参照を避け、呼び出し側が target_date を明示的に渡すことでルックアヘッドバイアスを防止する設計としました（AI モジュールとリサーチモジュールに適用）。

### Fixed
- ロバストネス改善
  - OpenAI API 呼び出し失敗時のフォールバックとログ出力を強化（429・ネットワーク・タイムアウト・5xx の再試行、非再試行ケースの警告ログ）。
  - DuckDB executemany の空パラメータに対する互換性対策（空リストをチェックしてから executemany を実行）。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

リリースノート補足（運用上の注意）
- OpenAI API
  - 環境変数 OPENAI_API_KEY または api_key 引数が必須です。未設定の場合、score_news / score_regime は ValueError を送出します。
  - LLM 出力は厳密な JSON を想定していますが、余計な前後テキストが混ざるケースに備えた復元処理を行います。とはいえモデル挙動に依存するため運用時はモニタリングを推奨します。
- 環境変数自動ロード
  - 自動で .env / .env.local を読み込む挙動はデフォルトで有効です。CI / テスト環境等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB（DuckDB）
  - デフォルトの duckdb ファイルパスは settings.duckdb_path = data/kabusys.duckdb（ホーム展開対応）です。運用環境では環境変数 DUCKDB_PATH を設定してください。
- テスト / モック
  - OpenAI への実際の呼び出し部分はモック可能な実装（_call_openai_api）として分離しています。ユニットテストでは patch して振る舞いを制御してください。

問い合わせやバグ報告はリポジトリの issue にてお願いします。