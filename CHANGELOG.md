# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

なお、本ログは与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-03
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初版を追加。バージョンは 0.1.0。
  - package-level export: data, strategy, execution, monitoring（strategy/execution/monitoring の詳細実装はコードベースの別ファイル想定）。

- 環境設定・読み込み（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（OS環境変数を保護、.env.local は .env より優先して上書き）。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探す実装（CWDに依存しない）。
  - .env パーサ実装（コメント処理、export 接頭辞、シングル/ダブルクォート、エスケープ処理対応）。
  - Settings クラスを提供し、環境変数経由で設定値を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK 閾値（監視用）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）および LOG_LEVEL のバリデーション
  - 必須環境変数未設定時は明示的に ValueError を投げる _require ヘルパを実装。

- AI: ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集計して銘柄ごとにニューステキストをまとめ、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントスコアを算出する score_news を実装。
  - タイムウィンドウの計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換する calc_news_window）。
  - 1銘柄あたりの上限記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装してトークン肥大化対策を行う。
  - バッチ処理（チャンクサイズ _BATCH_SIZE=20）とエクスポネンシャルバックオフ（429・ネットワーク断・タイムアウト・5xx をリトライ）を実装。
  - OpenAI レスポンスの堅牢なバリデーション（JSON 抽出、results フィールド検査、未知コード無視、数値型検査、±1.0 でクリップ）。
  - DuckDB への書き込みは冪等（DELETE→INSERT）で実施。部分失敗時に既存スコアを保護するためコードを限定して置換。
  - テスト容易性のため _call_openai_api を patch して差し替え可能、といった設計注記あり。

- AI: 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLMセンチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - ma200_ratio を DuckDB から取得するロジック（ルックアヘッド防止: date < target_date の排他取得）。
  - マクロ記事はキーワードフィルタ（_MACRO_KEYWORDS）で抽出し、最大記事数制限を設けて LLM に送信。
  - OpenAI 呼び出しは gpt-4o-mini の JSON Mode を使用。リトライ/バックオフ/5xx の取り扱いを定義。
  - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
  - 結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- Research（src/kabusys/research/*.py）
  - ファクター計算（factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足は None を返却。
    - calc_volatility: 20日 ATR（平均 true range）、相対ATR(atr_pct)、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。
    - calc_value: raw_financials（過去の最新財務）と当日の株価を組み合わせて PER/ROE を算出。EPSが0または欠損の場合は PER = None。
    - 各関数は DuckDB SQL を中心に実装し、(date, code) をキーとする dict リストを返却。
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。
    - calc_ic: factor と将来リターンの Spearman ランク相関（Information Coefficient）を実装。有効データが3件未満なら None を返却。
    - rank: 同順位は平均ランクにするランク付け実装（丸めで ties の検出漏れを防ぐ）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - 研究系ユーティリティは外部ライブラリ非依存（標準ライブラリ + DuckDB）で実装。

- Data（src/kabusys/data/*.py）
  - calendar_management.py
    - market_calendar テーブルを用いた営業日判定ユーティリティ群:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar 未登録や NULL 値がある場合は曜日ベース（週末除外）でフォールバックする一貫したロジックを採用。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を更新（バックフィル、健全性チェック、ON CONFLICT 相当の保存ロジック想定）。
    - 最大探索範囲やバックフィル・先読みパラメータを定義して無限ループや異常データの影響を抑制。
  - pipeline.py / etl.py
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質チェック結果、エラーリスト等）を標準化して返却できるようにした。
    - ETL パイプラインは差分更新、保存（jquants_client への委譲）、品質チェック (quality モジュール) を行う設計を想定。
    - jquants_client の fetch/save 系関数と統合する想定のインターフェースを提供。
    - DuckDB の executemany における空リストバインド制約（DuckDB 0.10）を考慮した実装（空リスト時は実行回避）。

- その他
  - テストを考慮した設計メモ（_call_openai_api を patch 可能など）をコード内に明記。
  - ロギング（logger）を各モジュールに導入し、重要な経過・警告・例外を出力する方針を採用。

### Security
- OpenAI API キーや各種トークンは環境変数から取得する設計。必須未設定時は明示的にエラーを出すことで誤った運用を防止。

### Notes / Known limitations
- OpenAI 連携は gpt-4o-mini の JSON Mode を前提としている（環境によりモデル名や JSON 出力仕様の変更が必要になる可能性がある）。
- 一部モジュール（strategy / execution / monitoring）の具体的実装はこのコード断片には含まれていないため、実装済みAPIの想定に基づく表現になっている箇所がある。
- DuckDB バインドや日付型扱いなど、実行環境依存の振る舞い（バージョン差異）についてはコード内に互換性対策コメントを含む。
- 日付計算ロジックはルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照しない設計が尊重されている（ただし calendar_update_job 等は実行時に date.today() を使用）。

---

作成者注: 上記は提供されたソースコードから機能と設計方針を読み取り推測して作成した CHANGELOG です。実際のリリースノートでは、追加の実装ファイルやマイナー/パッチリリース履歴（バグ修正など）を反映してください。